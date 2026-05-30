#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "aiohttp",
#     "mcp",
#     "python-dotenv",
# ]
# ///
"""
OpenGameEval Local Harness
Runs OpenGameEval evals locally against Roblox Studio via MCP.
Supports skills injection for benchmarking LLMs with/without context.
"""

import asyncio
import json
import time
import os
import re
import subprocess
import sys
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession
import aiohttp
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────

@dataclass
class ModelConfig:
    name: str
    api_base: str
    api_key: str
    system_prompt: Optional[str] = None


@dataclass
class StudioConfig:
    exe_path: str
    mcp_path: str
    startup_wait: int = 20


@dataclass
class RunConfig:
    evals_dir: str
    places_dir: str
    max_tool_rounds: int = 25
    pass_n: int = 1
    output_dir: str = "results"
    screenshots: bool = False
    verbose: bool = False


# ──────────────────────────────────────────────
# Eval Parser
# ──────────────────────────────────────────────

@dataclass
class EvalFile:
    path: str
    scenario_name: str
    prompt_text: str
    place: str
    script: str


def parse_eval(path: str) -> EvalFile:
    content = Path(path).read_text(encoding="utf-8")

    name_m = re.search(r'scenario_name\s*=\s*"([^"]+)"', content)
    place_m = re.search(r'place\s*=\s*"([^"]+)"', content)

    # prompt can be [[multi-line]] or "single-line"
    prompt_m = re.search(r'content\s*=\s*\[\[(.+?)\]\]', content, re.DOTALL)
    if not prompt_m:
        prompt_m = re.search(r'content\s*=\s*"([^"]+)"', content)

    return EvalFile(
        path=path,
        scenario_name=name_m.group(1) if name_m else Path(path).stem,
        prompt_text=prompt_m.group(1).strip() if prompt_m else "",
        place=place_m.group(1) if place_m else "",
        script=content,
    )


# ──────────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────────

@dataclass
class EvalMetrics:
    scenario: str = ""
    place: str = ""
    passed: bool = False
    passed_cons: bool = False   # Cons@5: >=3/5 passes
    passed_all: bool = False    # All@5: 5/5 passes
    scene_passed: Optional[bool] = None
    game_passed: Optional[bool] = None
    error: Optional[str] = None
    llm_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    llm_latency_ms: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    total_time_ms: int = 0
    rounds_used: int = 0
    screenshot_path: Optional[str] = None


# ──────────────────────────────────────────────
# LLM Bridge
# ──────────────────────────────────────────────

def mcp_tools_to_openai(tools) -> list:
    """Convert MCP tool definitions to OpenAI function calling format."""
    openai_tools = []
    for tool in tools:
        schema = tool.inputSchema if hasattr(tool, "inputSchema") and tool.inputSchema else {"type": "object", "properties": {}}
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            },
        })
    return openai_tools


async def llm_chat(
    config: ModelConfig,
    messages: list,
    tools: list,
    timeout: int = 120,
) -> dict:
    """Call an OpenAI-compatible chat completions endpoint."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
    }
    payload = {
        "model": config.name,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{config.api_base}/chat/completions",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=timeout),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"LLM API error {resp.status}: {body[:500]}")
            return await resp.json()


# ──────────────────────────────────────────────
# Studio Lifecycle
# ──────────────────────────────────────────────

async def launch_studio(studio: StudioConfig, place_path: str) -> subprocess.Popen:
    abs_place = str(Path(place_path).resolve())
    logger.info(f"Launching Studio with {abs_place}")
    proc = subprocess.Popen(
        [studio.exe_path, "-localPlaceFile", abs_place],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.info(f"Waiting {studio.startup_wait}s for Studio to load...")
    await asyncio.sleep(studio.startup_wait)
    return proc


def kill_studio(proc: subprocess.Popen):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except Exception:
        proc.kill()


# ──────────────────────────────────────────────
# Eval Runner
# ──────────────────────────────────────────────

# EvalUtils module implementations (reverse-engineered from eval script usage)
# These are injected as ModuleScripts inside LoadedCode.EvalUtils

EVALUTILS_TYPES = """
-- Type stubs for eval scripts (BaseEval type annotation)
return {
    BaseEval = {},  -- placeholder; type annotations are ignored at runtime
}
"""

EVALUTILS_UTILS_HE = """
local utils_he = {}

-- Returns all non-service instances in the game as an array (snapshot)
function utils_he.getAllReasonableItems()
    local items = {}
    for _, obj in ipairs(game:GetDescendants()) do
        local ok, isService = pcall(function()
            return game:GetService(obj.ClassName) ~= nil
        end)
        if not (ok and isService) then
            table.insert(items, obj)
        end
    end
    return items
end

-- Returns items in 'new' that are not in 'old' (set difference by instance identity)
function utils_he.table_difference(old, new)
    local oldSet = {}
    for _, obj in ipairs(old) do
        oldSet[obj] = true
    end
    local diff = {}
    for _, obj in ipairs(new) do
        if not oldSet[obj] then
            table.insert(diff, obj)
        end
    end
    return diff
end

-- Returns selected instances from a selection context table
function utils_he.GetSelected(selectionContext)
    local selected = {}
    for _, selection in ipairs(selectionContext) do
        for _, instance in ipairs(game:GetDescendants()) do
            if instance.Name == selection.instanceName and instance:IsA(selection.className) then
                table.insert(selected, instance)
                break
            end
        end
    end
    return selected
end

-- Returns bounding box size info for a model
function utils_he.getSizeInfoOfModel(model)
    local cf, size = model:GetBoundingBox()
    local sx, sy, sz = size.X, size.Y, size.Z
    local shortest = math.min(sx, sy, sz)
    local longest = math.max(sx, sy, sz)
    return {
        shortestSide = shortest,
        longestSide = longest,
        size = size,
        cframe = cf,
    }
end

return utils_he
"""

EVALUTILS_UTILS_RUNS = """
local utils_runs = {}

-- Simulates a key press/release in play mode
function utils_runs.sendKeyEvent(pressed, keyCode)
    local VirtualInputManager = game:GetService("VirtualInputManager")
    if pressed then
        VirtualInputManager:SendKeyEvent(true, keyCode, false, game)
    else
        VirtualInputManager:SendKeyEvent(false, keyCode, false, game)
    end
end

-- Creates PlayerScripts in StarterPlayer if missing
function utils_runs.createPlayerScripts()
    local StarterPlayer = game:GetService("StarterPlayer")
    if not StarterPlayer:FindFirstChild("StarterPlayerScripts") then
        local sps = Instance.new("Folder")
        sps.Name = "StarterPlayerScripts"
        sps.Parent = StarterPlayer
    end
end

-- Loads/reloads player scripts (no-op in edit mode)
function utils_runs.loadPlayerScripts()
    -- This is a no-op in edit mode; only relevant during playtest
end

return utils_runs
"""

EVALUTILS_LIB = """
-- General library stub (not used by any eval at runtime)
return {}
"""

# Lua code to inject EvalUtils modules into LoadedCode
INJECT_EVALUTILS = """
local LoadedCode = game:FindFirstChild("LoadedCode")
if not LoadedCode then
    LoadedCode = Instance.new("ModuleScript")
    LoadedCode.Name = "LoadedCode"
    LoadedCode.Source = "return {}"
    LoadedCode.Parent = game
end

local eu = LoadedCode:FindFirstChild("EvalUtils")
if not eu then
    eu = Instance.new("Folder")
    eu.Name = "EvalUtils"
    eu.Parent = LoadedCode
end

local modules = {TYPES_PLACEHOLDER}

for name, source in pairs(modules) do
    local existing = eu:FindFirstChild(name)
    if existing then
        existing.Source = source
    else
        local mod = Instance.new("ModuleScript")
        mod.Name = name
        mod.Source = source
        mod.Parent = eu
    end
end
return "ok"
"""

# Build the injection Lua with actual module sources
def _build_inject_lua():
    import json
    modules = {
        "types": EVALUTILS_TYPES,
        "utils_he": EVALUTILS_UTILS_HE,
        "utils_runs": EVALUTILS_UTILS_RUNS,
        "lib": EVALUTILS_LIB,
    }
    # Serialize as Lua table
    parts = []
    for name, source in modules.items():
        # Escape source for Lua string
        escaped = source.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
        parts.append(f'["{name}"] = "{escaped}"')
    lua_table = "{" + ", ".join(parts) + "}"
    return INJECT_EVALUTILS.replace("TYPES_PLACEHOLDER", lua_table)

ENSURE_LOADED_CODE = _build_inject_lua()

def get_tool_text(result) -> str:
    """Extract text from MCP tool result, handling different content types."""
    if not result or not result.content:
        return ""
    for c in result.content:
        if hasattr(c, "text"):
            return c.text
    return str(result.content[0])


async def run_single_eval(
    ev: EvalFile,
    model: ModelConfig,
    studio: StudioConfig,
    run: RunConfig,
) -> EvalMetrics:
    m = EvalMetrics(scenario=ev.scenario_name, place=ev.place)
    t0 = time.time()

    place_path = Path(run.places_dir) / ev.place
    if not place_path.exists():
        m.error = f"Place file not found: {place_path}"
        m.total_time_ms = int((time.time() - t0) * 1000)
        return m

    studio_proc = None
    try:
        # 1. Launch Studio
        studio_proc = await launch_studio(studio, str(place_path))

        # 2. Connect MCP
        server_params = StdioServerParameters(
            command="cmd.exe",
            args=["/c", studio.mcp_path],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                logger.info(f"[{ev.scenario_name}] MCP connected")

                # 3. Get tool definitions
                tools_result = await session.list_tools()
                openai_tools = mcp_tools_to_openai(tools_result.tools)
                logger.info(f"[{ev.scenario_name}] {len(openai_tools)} tools available")

                # 4. Ensure LoadedCode exists
                await session.call_tool("execute_luau", {"code": ENSURE_LOADED_CODE})

                # 5. Run eval setup
                setup_lua = f"""
local ok, eval = pcall(function()
    return loadstring([==[{ev.script}]==])()
end)
if not ok then return "SETUP_ERROR: " .. tostring(eval) end
if eval.setup then
    local sok, serr = pcall(eval.setup)
    if not sok then return "SETUP_ERROR: " .. tostring(serr) end
end
return "ok"
"""
                setup_result = await session.call_tool("execute_luau", {"code": setup_lua})
                setup_text = get_tool_text(setup_result)
                if "SETUP_ERROR" in setup_text:
                    m.error = f"Setup failed: {setup_text}"
                    m.total_time_ms = int((time.time() - t0) * 1000)
                    return m

                # 6. Build messages for LLM
                messages = []
                if model.system_prompt:
                    messages.append({"role": "system", "content": model.system_prompt})
                messages.append({"role": "user", "content": ev.prompt_text})

                # 7. LLM tool-use loop
                llm_start = time.time()
                round_idx = 0
                for round_idx in range(run.max_tool_rounds):
                    logger.info(f"[{ev.scenario_name}] LLM round {round_idx + 1}")
                    response = await llm_chat(model, messages, openai_tools)
                    m.llm_calls += 1

                    usage = response.get("usage", {})
                    m.total_tokens_in += usage.get("prompt_tokens", 0)
                    m.total_tokens_out += usage.get("completion_tokens", 0)

                    choice = response["choices"][0]
                    message = choice["message"]
                    messages.append(message)
                    finish = choice.get("finish_reason", "")

                    if finish == "tool_calls" and message.get("tool_calls"):
                        for tc in message["tool_calls"]:
                            m.tool_calls += 1
                            func = tc["function"]
                            try:
                                args = json.loads(func["arguments"])
                            except json.JSONDecodeError:
                                args = {}

                            try:
                                result = await session.call_tool(func["name"], args)
                                tool_out = get_tool_text(result)
                            except Exception as e:
                                tool_out = f"Tool error: {e}"
                                m.tool_errors += 1

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": tool_out,
                            })
                    else:
                        # LLM finished (stop, length, or content)
                        break

                m.llm_latency_ms = int((time.time() - llm_start) * 1000)
                m.rounds_used = round_idx + 1

                # 8. Take screenshot if requested
                if run.screenshots:
                    try:
                        ss = await session.call_tool("screen_capture", {})
                        if ss.content:
                            ss_path = Path(run.output_dir) / f"{ev.scenario_name}.png"
                            # screen_capture returns base64 or image data
                            # save it if possible
                            m.screenshot_path = str(ss_path)
                    except Exception:
                        pass

                # 9. Run check_scene (edit mode)
                check_scene_lua = f"""
local ok, eval = pcall(function()
    return loadstring([==[{ev.script}]==])()
end)
if not ok then return "false|PARSE_ERROR: " .. tostring(eval) end
if not eval.check_scene then return "true|NO_CHECK" end
local cok, cerr = pcall(eval.check_scene)
if cok then return "true|pass" else return "false|" .. tostring(cerr) end
"""
                scene_result = await session.call_tool("execute_luau", {"code": check_scene_lua})
                scene_text = get_tool_text(scene_result) or "false|no_response"
                m.scene_passed = scene_text.startswith("true")
                if not m.scene_passed:
                    m.error = f"check_scene failed: {scene_text}"

                # 10. Enter play mode and run check_game
                if not m.error or m.scene_passed:
                    try:
                        await session.call_tool("start_stop_play", {"action": "start_play"})
                        await asyncio.sleep(8)  # wait for play mode to initialize

                        check_game_lua = f"""
local ok, eval = pcall(function()
    return loadstring([==[{ev.script}]==])()
end)
if not ok then return "false|PARSE_ERROR: " .. tostring(eval) end
if not eval.check_game then return "true|NO_CHECK" end
local cok, cerr = pcall(eval.check_game)
if cok then return "true|pass" else return "false|" .. tostring(cerr) end
"""
                        game_result = await session.call_tool("execute_luau", {"code": check_game_lua})
                        game_text = get_tool_text(game_result) or "false|no_response"
                        m.game_passed = game_text.startswith("true")
                        if not m.game_passed:
                            m.error = f"check_game failed: {game_text}"
                    except Exception as e:
                        m.game_passed = False
                        m.error = f"Play mode error: {e}"
                    finally:
                        try:
                            await session.call_tool("start_stop_play", {"action": "stop"})
                        except Exception:
                            pass

                m.passed = (m.scene_passed is True) and (m.game_passed is not False)

    except Exception as e:
        m.error = f"Fatal: {e}"
        logger.error(f"[{ev.scenario_name}] {e}")
    finally:
        if studio_proc:
            kill_studio(studio_proc)

    m.total_time_ms = int((time.time() - t0) * 1000)
    return m


# ──────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────

def aggregate_results(results: list[EvalMetrics], pass_n: int = 1) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errors = sum(1 for r in results if r.error and "Fatal" in (r.error or ""))
    tool_errors = sum(r.tool_errors for r in results)
    total_tool_calls = sum(r.tool_calls for r in results)

    summary = {
        "total_evals": total,
        "passed": passed,
        "pass_rate": round(passed / total * 100, 2) if total else 0,
        "fatal_errors": errors,
        "tool_error_rate": round(tool_errors / total_tool_calls * 100, 2) if total_tool_calls else 0,
        "avg_llm_calls": round(sum(r.llm_calls for r in results) / total, 1) if total else 0,
        "avg_tokens_in": round(sum(r.total_tokens_in for r in results) / total) if total else 0,
        "avg_tokens_out": round(sum(r.total_tokens_out for r in results) / total) if total else 0,
        "avg_latency_ms": round(sum(r.llm_latency_ms for r in results) / total) if total else 0,
        "avg_total_time_ms": round(sum(r.total_time_ms for r in results) / total) if total else 0,
        "total_time_ms": sum(r.total_time_ms for r in results),
    }

    if pass_n == 5:
        summary["pass_at_5"] = round(passed / total * 100, 2) if total else 0  # >=1/5
        summary["cons_at_5"] = round(sum(1 for r in results if r.passed_cons) / total * 100, 2) if total else 0  # >=3/5
        summary["all_at_5"] = round(sum(1 for r in results if r.passed_all) / total * 100, 2) if total else 0  # 5/5

    return summary


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="OpenGameEval Local Harness")
    p.add_argument("--evals-dir", required=True, help="Path to Evals/ directory")
    p.add_argument("--debug-evals-dir", default=None, help="Path to DebugEvals/ directory (optional, for debug benchmark)")
    p.add_argument("--places-dir", required=True, help="Path to Places/ directory")
    p.add_argument("--studio-exe", required=True, help="Path to RobloxStudioBeta.exe")
    p.add_argument("--mcp-bat", required=True, help="Path to mcp.bat")
    p.add_argument("--model-name", required=True, help="Model name for API")
    p.add_argument("--api-base", default=None, help="OpenAI-compatible API base URL (or set LLM_API_BASE env)")
    p.add_argument("--api-key", default=None, help="API key (or set LLM_API_KEY env)")
    p.add_argument("--system-prompt-file", default=None, help="File with system prompt for skills injection")
    p.add_argument("--pass-n", type=int, default=1, choices=[1, 5], help="Pass@1 or Pass@5")
    p.add_argument("--max-rounds", type=int, default=25, help="Max LLM tool-use rounds per eval")
    p.add_argument("--startup-wait", type=int, default=20, help="Seconds to wait for Studio")
    p.add_argument("--output-dir", default="results", help="Output directory")
    p.add_argument("--screenshots", action="store_true", help="Capture screenshots")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    p.add_argument("--eval-filter", default=None, help="Regex filter for eval scenario names")
    return p.parse_args()


async def main():
    load_dotenv()
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve API base
    api_base = args.api_base or os.getenv("LLM_API_BASE")
    if not api_base:
        print("Error: --api-base or LLM_API_BASE env required")
        sys.exit(1)

    # Resolve API key
    api_key = args.api_key or os.getenv("LLM_API_KEY")
    if not api_key:
        print("Error: --api-key or LLM_API_KEY env required")
        sys.exit(1)

    # Load system prompt
    system_prompt = None
    if args.system_prompt_file:
        system_prompt = Path(args.system_prompt_file).read_text(encoding="utf-8")
        logger.info(f"Loaded system prompt ({len(system_prompt)} chars)")

    model = ModelConfig(
        name=args.model_name,
        api_base=api_base.rstrip("/"),
        api_key=api_key,
        system_prompt=system_prompt,
    )
    studio = StudioConfig(
        exe_path=args.studio_exe,
        mcp_path=args.mcp_bat,
        startup_wait=args.startup_wait,
    )
    run = RunConfig(
        evals_dir=args.evals_dir,
        places_dir=args.places_dir,
        max_tool_rounds=args.max_rounds,
        pass_n=args.pass_n,
        output_dir=args.output_dir,
        screenshots=args.screenshots,
        verbose=args.verbose,
    )

    # Parse eval files
    eval_files = sorted(Path(args.evals_dir).glob("*.lua"))
    if not eval_files:
        print(f"No .lua files found in {args.evals_dir}")
        sys.exit(1)

    evals = [parse_eval(str(f)) for f in eval_files]

    # Apply filter
    if args.eval_filter:
        pattern = re.compile(args.eval_filter)
        evals = [e for e in evals if pattern.search(e.scenario_name)]

    logger.info(f"Loaded {len(evals)} evals")

    # Create output dir
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Helper: run a set of evals
    async def run_eval_set(evals_list, label):
        results = []
        for i, ev in enumerate(evals_list):
            logger.info(f"=== [{label}] [{i+1}/{len(evals_list)}] {ev.scenario_name} ===")

            run_results = []
            for attempt in range(run.pass_n):
                logger.info(f"  Attempt {attempt + 1}/{run.pass_n}")
                result = await run_single_eval(ev, model, studio, run)
                run_results.append(result)

                status = "PASS" if result.passed else "FAIL"
                logger.info(
                    f"  {status} | tokens_in={result.total_tokens_in} "
                    f"tokens_out={result.total_tokens_out} "
                    f"latency={result.llm_latency_ms}ms "
                    f"total={result.total_time_ms}ms "
                    f"tools={result.tool_calls} err={result.tool_errors}"
                )
                if result.error:
                    logger.info(f"  Error: {result.error}")

            if run.pass_n == 5:
                pass_count = sum(1 for r in run_results if r.passed)
                best = run_results[0]
                best.passed = pass_count >= 1
                best.passed_cons = pass_count >= 3
                best.passed_all = pass_count == 5
                results.append(best)
            else:
                results.append(run_results[0])
        return results

    # Run expanded evals
    all_results = await run_eval_set(evals, "EXPANDED")

    # Optionally run debug evals
    debug_results = None
    if args.debug_evals_dir:
        debug_dir = Path(args.debug_evals_dir)
        debug_files = sorted(debug_dir.glob("*.lua"))
        if debug_files:
            debug_evals = [parse_eval(str(f)) for f in debug_files]
            if args.eval_filter:
                pattern = re.compile(args.eval_filter)
                debug_evals = [e for e in debug_evals if pattern.search(e.scenario_name)]
            logger.info(f"Loaded {len(debug_evals)} debug evals")
            debug_results = await run_eval_set(debug_evals, "DEBUG")

    # Save results
    results_path = Path(args.output_dir) / "results.json"
    summary = aggregate_results(all_results, run.pass_n)
    output = {
        "summary": summary,
        "model": {"name": model.name, "api_base": model.api_base},
        "config": {"pass_n": run.pass_n, "max_rounds": run.max_tool_rounds},
        "evals": [asdict(r) for r in all_results],
    }

    debug_summary = None
    if debug_results:
        debug_summary = aggregate_results(debug_results, run.pass_n)
        output["debug_summary"] = debug_summary
        output["debug_evals"] = [asdict(r) for r in debug_results]

    results_path.write_text(json.dumps(output, indent=2))
    logger.info(f"Results saved to {results_path}")

    # Print summary
    def print_summary(label, summ, pass_n):
        print(f"\n  [{label}]")
        if pass_n == 5:
            print(f"    Pass@1: {summ['pass_rate']}% ({summ['passed']}/{summ['total_evals']})")
            print(f"    Pass@5: {summ['pass_at_5']}%")
            print(f"    Cons@5: {summ['cons_at_5']}%")
            print(f"    All@5:  {summ['all_at_5']}%")
        else:
            print(f"    PASS RATE: {summ['pass_rate']}% ({summ['passed']}/{summ['total_evals']})")
        print(f"    AVG TOKENS: in={summ['avg_tokens_in']} out={summ['avg_tokens_out']}")
        print(f"    AVG LATENCY: {summ['avg_latency_ms']}ms")
        print(f"    TOOL ERROR RATE: {summ['tool_error_rate']}%")

    print("\n" + "=" * 60)
    print(f"  MODEL: {model.name}")
    print_summary("EXPANDED (87 evals)", summary, run.pass_n)
    if debug_summary:
        print_summary("DEBUG (30 evals)", debug_summary, run.pass_n)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
