# local-open-game-eval

Run [OpenGameEval](https://github.com/Roblox/open-game-eval) evals **locally** against Roblox Studio via MCP. Supports skills injection for benchmarking LLMs with/without context.

A community extension of Roblox's OpenGameEval, running the same evals, extended with local execution, skills injection, and richer metrics.

## Quick Start

### 1. Prerequisites

- **64-bit Windows 10, or Windows 11.**
- **Roblox Studio** 
- **Python 3.10+** https://www.python.org/downloads/
- **Studio MCP server** enabled (Assistant → Manage MCP Servers) https://create.roblox.com/docs/studio/mcp
- **An OpenAI-compatible LLM endpoint** (any provider)

### 2. Clone the Repos

```powershell
# Clone this harness
git clone https://github.com/TabooHarmony/local-open-game-eval.git
cd local-open-game-eval

# Clone OpenGameEval for eval files and places
git clone https://github.com/Roblox/open-game-eval.git ../open-game-eval
```

### 3. Install Dependencies

```powershell
pip install mcp aiohttp python-dotenv
```

### 4. Configure

```powershell
copy .env.example .env
# Edit .env with your API key
```

### 5. Run

```powershell
python harness.py ^
  --evals-dir ..\open-game-eval\Evals ^
  --places-dir ..\open-game-eval\Places ^
  --studio-exe "C:\Users\YOU\AppData\Local\Roblox\Versions\version-xxx\RobloxStudioBeta.exe" ^
  --mcp-bat "%LOCALAPPDATA%\Roblox\mcp.bat" ^
  --model-name "your-model-name" ^
  --api-base "https://your-endpoint/v1"
```

Results saved to `results/results.json`.

## How It Works

The harness runs each eval locally against your Studio instance:

1. Launches Studio with the eval's `.rbxl` place file (`-localPlaceFile`)
2. Connects to Studio's built-in MCP server via stdio
3. Sends the eval prompt to your LLM with Studio MCP tools available
4. The LLM explores the place and makes changes using MCP tools (`execute_luau`, `multi_edit`, `script_read`, `search_game_tree`, etc.)
5. Runs `check_scene` (edit mode) and `check_game` (play mode) assertions
6. Collects metrics: pass/fail, tokens, latency, tool calls, errors

This matches how the cloud API works, so the LLM gets tool-calling access to Studio and decides where to place code.

## Skills Injection

Benchmark the same model with and without context:

```powershell
# Vanilla (no context)
python harness.py --evals-dir ..\Evals --places-dir ..\Places ... --output-dir results/vanilla

# With skills
python harness.py --evals-dir ..\Evals --places-dir ..\Places ... --system-prompt-file skills.txt --output-dir results/skills
```

The `--system-prompt-file` injects a system message containing curated knowledge (e.g., Luau best practices, Roblox APIs, common footguns). Compare pass rates to measure the impact.

## Command Line Options

```
Required:
  --evals-dir DIR          Path to Evals/ directory
  --places-dir DIR         Path to Places/ directory
  --studio-exe PATH        Path to RobloxStudioBeta.exe
  --mcp-bat PATH           Path to mcp.bat
  --model-name NAME        Model name for API
  --api-base URL           OpenAI-compatible API base URL

Optional:
  --api-key KEY            API key (or set LLM_API_KEY in .env)
  --system-prompt-file F   System prompt file for skills injection
  --pass-n 1|5             Pass@1 or Pass@5 (default: 1)
  --max-rounds N           Max LLM tool-use rounds per eval (default: 25)
  --startup-wait N         Seconds to wait for Studio (default: 20)
  --output-dir DIR         Output directory (default: results)
  --screenshots            Capture Studio viewport per eval
  --eval-filter REGEX      Filter evals by scenario name
  --verbose                Verbose logging
```

## Metrics

Unlike the cloud API (which only returns pass/fail), the local harness collects:

| Metric | Description |
|--------|-------------|
| `passed` | Whether all assertions passed |
| `scene_passed` / `game_passed` | Edit mode vs play mode results |
| `llm_calls` | Number of LLM API calls |
| `total_tokens_in` / `total_tokens_out` | Token consumption |
| `llm_latency_ms` | Total LLM response time |
| `tool_calls` / `tool_errors` | MCP tool usage and error rate |
| `total_time_ms` | Wall clock time per eval |
| `rounds_used` | How many tool-use rounds the LLM needed |
| `error` | Error details if eval failed |

Results are saved as JSON with per-eval details and an aggregate summary.

## Understanding Results

Evaluations typically take 3-5 minutes each (LLM calls + Studio startup). A pass requires all assertions to succeed in both edit mode (`check_scene`) and play mode (`check_game`).

```json
{
  "summary": {
    "pass_rate": 35.63,
    "passed": 31,
    "total_evals": 87,
    "avg_tokens_in": 2450,
    "avg_tokens_out": 1200,
    "avg_latency_ms": 4500,
    "tool_error_rate": 2.1
  }
}
```

## Supported Models

Any OpenAI-compatible endpoint works. Tested with:

- **MiMo v2.5 Pro** (via `custom:xiaomi`)
- **DeepSeek V4 Flash** (via OpenRouter)
- **GLM-5.1** (via Ollama)
- Any model behind an OpenAI-compatible proxy

## Evaluation Structure

Evals are unchanged from upstream OpenGameEval:

```lua
local eval: BaseEval = {
    scenario_name = "001_make_cars_faster",
    prompt = { { { role = "user", content = "Make the cars of this game 2x faster" } } },
    place = "racing.rbxl",
}

eval.setup = function() end
eval.check_scene = function() end
eval.check_game = function() end

return eval
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Studio doesn't open | Verify `--studio-exe` path. Test with `.\RobloxStudioBeta.exe -localPlaceFile "path.rbxl"` manually. |
| MCP connection fails | Ensure Studio MCP is enabled. Check `%LOCALAPPDATA%\Roblox\mcp.bat` exists. |
| `LoadedCode` not found | The harness injects it automatically. If this fails, check that `execute_luau` works. |
| LLM returns errors | Verify `--api-base` and `--api-key`. Test with curl to the `/chat/completions` endpoint. |
| Play mode hangs | Increase `--startup-wait`. Some evals need more time for play mode to initialize. |
| 404 from cloud API | This harness runs locally — no cloud API needed. You're in the right place. |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test with at least one eval before submitting
4. Submit a pull request

## License

MIT; see [LICENSE](LICENSE).

## Acknowledgments

- [Roblox OpenGameEval](https://github.com/Roblox/open-game-eval): the eval framework this extends
