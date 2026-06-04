"""
runner.py — Stable eval runner + monitor for the VM.

Usage:
  python runner.py run <eval_filter>     Run evals matching regex filter
  python runner.py run-all               Run all 87 evals
  python runner.py status                Check current run progress
  python runner.py tail                  Tail the current run log
  python runner.py stability             Run stability tests (launch/kill/mcp)
  python runner.py cleanup               Kill all Roblox processes

Writes structured JSON lines to runner_status.json for external monitoring.
All output also goes to runner.log.
"""
import subprocess, time, os, sys, json, re, glob, signal
from datetime import datetime
from pathlib import Path

# === CONFIG ===
HARNESS_DIR = r"C:\Users\Admin\local-open-game-eval"
OPEN_GAME_EVAL = r"C:\Users\Admin\open-game-eval"
STUDIO_EXE = r"C:\Users\Admin\AppData\Local\Roblox\Versions\version-8ec813a8524f409b\RobloxStudioBeta.exe"
MCP_EXE = os.path.join(os.path.dirname(STUDIO_EXE), "StudioMCP.exe")
MCP_BAT = r"C:\Users\Admin\AppData\Local\Roblox\mcp.bat"
PLACES_DIR = os.path.join(OPEN_GAME_EVAL, "Places")
PLACE = os.path.join(PLACES_DIR, "baseplate.rbxl")
EVALS_DIR = os.path.join(OPEN_GAME_EVAL, "Evals")
DEBUG_EVALS_DIR = os.path.join(OPEN_GAME_EVAL, "DebugEvals")
RESULTS_DIR = os.path.join(HARNESS_DIR, "results")
STATUS_FILE = os.path.join(HARNESS_DIR, "runner_status.json")
LOG_FILE = os.path.join(HARNESS_DIR, "runner.log")

PROC_NAMES = ["StudioMCP.exe", "RobloxStudioBeta.exe", "RobloxCrashHandler.exe"]


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_status(data):
    """Write structured status for external monitoring."""
    data["updated"] = datetime.now().isoformat()
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_status():
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def kill_all():
    """Kill all Roblox/Studio processes. Returns count killed."""
    killed = 0
    for name in PROC_NAMES:
        r = subprocess.run(["taskkill", "/f", "/im", name], capture_output=True, text=True)
        if "SUCCESS" in r.stdout:
            killed += 1
    time.sleep(2)
    # Verify
    for _ in range(10):
        remaining = count_studio()
        if remaining == 0:
            return killed
        time.sleep(1)
        for name in PROC_NAMES:
            subprocess.run(["taskkill", "/f", "/im", name], capture_output=True)
    return killed


def count_studio():
    r = subprocess.run(["tasklist", "/fi", "imagename eq RobloxStudioBeta.exe", "/nh"],
                       capture_output=True, text=True)
    return 1 if "RobloxStudioBeta.exe" in r.stdout else 0


def count_all_roblox():
    total = 0
    for name in PROC_NAMES:
        proc = name.replace(".exe", "")
        r = subprocess.run(["tasklist", "/fi", f"imagename eq {name}", "/nh"],
                           capture_output=True, text=True)
        if name in r.stdout:
            total += 1
    return total


def studio_mem_mb():
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "(Get-Process RobloxStudioBeta -EA SilentlyContinue).WorkingSet64"],
                       capture_output=True, text=True)
    try:
        return int(int(r.stdout.strip()) / (1024 * 1024))
    except:
        return 0


def launch_studio(place_file):
    """Launch Studio with a place file via schtasks. Returns True if started."""
    kill_all()
    tn = f"Run{int(time.time()) % 100000}"
    tr = f'"{STUDIO_EXE}" -localPlaceFile "{place_file}"'
    subprocess.run(["schtasks", "/create", "/tn", tn, "/tr", tr,
                    "/sc", "once", "/st", "00:00", "/f", "/it"],
                   capture_output=True)
    subprocess.run(["schtasks", "/run", "/tn", tn], capture_output=True)
    subprocess.run(["schtasks", "/delete", "/tn", tn, "/f"], capture_output=True)

    for i in range(30):
        time.sleep(1)
        if count_studio():
            return True
    return False


def get_latest_results():
    """Parse the most recent results directory."""
    dirs = sorted(glob.glob(os.path.join(RESULTS_DIR, "*")),
                  key=os.path.getmtime, reverse=True)
    for d in dirs:
        rf = os.path.join(d, "results.json")
        if os.path.exists(rf):
            with open(rf, "r", encoding="utf-8") as f:
                return json.load(f), os.path.basename(d)
    return None, None


def get_eval_list():
    """Return list of eval .lua files."""
    return sorted(glob.glob(os.path.join(EVALS_DIR, "*.lua")))


# === COMMANDS ===

def cmd_status():
    """Show current status: last run + any active processes."""
    status = read_status()

    print("=== VM STATUS ===")
    print(f"Studio processes: {count_studio()}")
    print(f"Studio memory: {studio_mem_mb()}MB")
    print(f"All Roblox procs: {count_all_roblox()}")
    print(f"Eval files: {len(get_eval_list())}")
    print()

    if status:
        print("=== LAST RUNNER ACTION ===")
        print(json.dumps(status, indent=2))
        print()

    results, name = get_latest_results()
    if results:
        summary = results.get("summary", {})
        print(f"=== LATEST RESULTS: {name} ===")
        print(f"Total: {summary.get('total_evals', '?')}")
        print(f"Passed: {summary.get('passed', '?')}")
        print(f"Pass rate: {summary.get('pass_rate', '?')}%")
        print(f"Time: {summary.get('total_time_ms', 0) / 1000:.0f}s")

        errors = summary.get("error_breakdown", {})
        if errors:
            print(f"Errors: {json.dumps(errors)}")

        evals = results.get("evals", [])
        print(f"\nPer-eval:")
        for ev in evals:
            p = "PASS" if ev.get("passed") else "FAIL"
            err = ev.get("error", "")
            if err and len(err) > 70:
                err = err[:70] + "..."
            print(f"  {ev.get('scenario', '?'):<45} {p:<5} {err}")
    else:
        print("No results found.")


def cmd_run(eval_filter=None):
    """Run evals via the harness. eval_filter is a regex for scenario names."""
    if not os.path.exists(STUDIO_EXE):
        log(f"ERROR: Studio not found at {STUDIO_EXE}")
        return 1

    if not os.path.exists(EVALS_DIR):
        log(f"ERROR: Evals dir not found at {EVALS_DIR}")
        return 1

    evals = get_eval_list()
    if eval_filter:
        evals = [e for e in evals if re.search(eval_filter, os.path.basename(e))]
    if not evals:
        log(f"No evals match filter: {eval_filter}")
        return 1

    log(f"Running {len(evals)} evals" + (f" matching '{eval_filter}'" if eval_filter else ""))

    write_status({
        "state": "running",
        "eval_filter": eval_filter,
        "total_evals": len(evals),
        "completed": 0,
        "passed": 0,
        "failed": 0,
        "current_eval": None,
        "errors": []
    })

    # Run harness as subprocess
    cmd = [
        sys.executable, os.path.join(HARNESS_DIR, "harness.py"),
        "--evals-dir", EVALS_DIR,
        "--places-dir", PLACES_DIR,
        "--studio-exe", STUDIO_EXE,
        "--mcp-bat", MCP_BAT,
        "--model-name", "mimo-v2.5",
        "--verbose",
        "--verbose",
        "--debug-evals-dir", DEBUG_EVALS_DIR,
    ]
    if eval_filter:
        cmd += ["--eval-filter", eval_filter]

    log(f"CMD: {' '.join(cmd)}")

    # Stream output and parse progress
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, bufsize=1, cwd=HARNESS_DIR)

    completed = 0
    passed = 0
    failed = 0
    errors = []
    current = None

    try:
        for line in proc.stdout:
            line = line.rstrip()
            log(line)

            # Parse progress from harness output
            if "Running eval:" in line or "eval (" in line:
                m = re.search(r"(\d+)/(\d+).*?:\s*(\S+)", line)
                if m:
                    current = m.group(3)

            if "] PASS" in line:
                completed += 1
                passed += 1
            elif "] FAIL" in line:
                completed += 1
                failed += 1
            elif "error" in line.lower() and "harness" in line.lower():
                errors.append(line[:100])

            # Update status file every eval
            if completed > 0 or current:
                write_status({
                    "state": "running",
                    "eval_filter": eval_filter,
                    "total_evals": len(evals),
                    "completed": completed,
                    "passed": passed,
                    "failed": failed,
                    "current_eval": current,
                    "pass_rate": round(passed / max(completed, 1) * 100, 1),
                    "errors": errors[-5:]  # last 5 errors
                })

    except KeyboardInterrupt:
        log("Interrupted, killing harness...")
        proc.kill()

    proc.wait()
    log(f"Harness exited with code {proc.returncode}")

    write_status({
        "state": "done",
        "eval_filter": eval_filter,
        "total_evals": len(evals),
        "completed": completed,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / max(completed, 1) * 100, 1),
        "errors": errors,
        "exit_code": proc.returncode
    })

    return proc.returncode


def cmd_stability():
    """Run stability tests: launch/kill cycles, MCP connectivity, zombie check."""
    log("=== STABILITY TEST START ===")

    write_status({"state": "stability_running", "phase": "launch_kill_cycles"})

    results = {"launch_kill_cycles": [], "mcp_connectivity": None, "zombie_check": None}

    # TEST 1: Launch/Kill x3
    log("\n--- TEST 1: Studio Launch/Kill Cycle x3 ---")
    for cycle in range(1, 4):
        log(f"  Cycle {cycle}")
        kill_all()

        t0 = time.time()
        ok = launch_studio(PLACE)
        launch_time = time.time() - t0

        if not ok:
            log(f"    FAIL: Studio did not start in 30s")
            results["launch_kill_cycles"].append({"cycle": cycle, "launched": False})
            continue

        time.sleep(10)  # settle
        mem = studio_mem_mb()
        procs = count_all_roblox()

        kill_all()
        remaining = count_all_roblox()

        r = {"cycle": cycle, "launched": True, "launch_time_s": round(launch_time, 1),
             "mem_mb": mem, "procs": procs, "remaining_after_kill": remaining}
        results["launch_kill_cycles"].append(r)
        log(f"    OK: {launch_time:.1f}s, {mem}MB, {procs} procs, {remaining} after kill")

    # TEST 2: MCP Connectivity
    log("\n--- TEST 2: MCP Connectivity ---")
    write_status({"state": "stability_running", "phase": "mcp_connectivity"})
    kill_all()

    ok = launch_studio(PLACE)
    if ok:
        time.sleep(10)
        log("  Studio running, testing MCP spawn...")
        try:
            p = subprocess.Popen([MCP_EXE], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(8)
            alive = p.poll() is None
            if alive:
                log(f"  MCP alive (PID: {p.pid})")
                p.kill()
                results["mcp_connectivity"] = {"alive": True, "pid": p.pid}
            else:
                log(f"  MCP died (code: {p.returncode})")
                results["mcp_connectivity"] = {"alive": False, "exit_code": p.returncode}
        except Exception as e:
            log(f"  MCP error: {e}")
            results["mcp_connectivity"] = {"alive": False, "error": str(e)}
    else:
        results["mcp_connectivity"] = {"alive": False, "error": "Studio failed to start"}

    kill_all()

    # TEST 3: Rapid Kill x5 (zombie check)
    log("\n--- TEST 3: Rapid Launch/Kill x5 ---")
    write_status({"state": "stability_running", "phase": "zombie_check"})

    for i in range(1, 6):
        ok = launch_studio(PLACE)
        if ok:
            time.sleep(3)
        kill_all()
        log(f"  Round {i}")

    final = count_all_roblox()
    results["zombie_check"] = {"remaining": final, "pass": final == 0}
    log(f"  Result: {final} zombies {'PASS' if final == 0 else 'FAIL'}")

    # Summary
    log("\n=== STABILITY SUMMARY ===")
    cycles = results["launch_kill_cycles"]
    all_launched = all(c.get("launched") for c in cycles)
    all_clean = all(c.get("remaining_after_kill", 99) == 0 for c in cycles)
    mcp_ok = results["mcp_connectivity"] and results["mcp_connectivity"].get("alive")
    zombie_ok = results["zombie_check"] and results["zombie_check"].get("pass")

    log(f"  Launch/Kill: {'PASS' if all_launched and all_clean else 'FAIL'}")
    log(f"  MCP: {'PASS' if mcp_ok else 'FAIL'}")
    log(f"  Zombies: {'PASS' if zombie_ok else 'FAIL'}")

    overall = all_launched and all_clean and mcp_ok and zombie_ok
    log(f"  OVERALL: {'PASS' if overall else 'FAIL'}")

    write_status({"state": "stability_done", "results": results, "overall": "PASS" if overall else "FAIL"})
    return 0 if overall else 1


def cmd_cleanup():
    """Kill all Roblox processes."""
    killed = kill_all()
    remaining = count_all_roblox()
    log(f"Killed {killed}, remaining: {remaining}")
    write_status({"state": "clean", "remaining": remaining})
    return 0


def cmd_tail():
    """Print last 50 lines of runner log."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[-50:]:
            print(line.rstrip())
    else:
        print("No log file yet.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        cmd_status()
    elif cmd == "run":
        filt = sys.argv[2] if len(sys.argv) > 2 else None
        sys.exit(cmd_run(filt))
    elif cmd == "run-all":
        sys.exit(cmd_run())
    elif cmd == "stability":
        sys.exit(cmd_stability())
    elif cmd == "cleanup":
        sys.exit(cmd_cleanup())
    elif cmd == "tail":
        cmd_tail()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)

