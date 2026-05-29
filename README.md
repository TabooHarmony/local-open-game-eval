# OpenGameEval Local Harness

Runs OpenGameEval evals locally against Roblox Studio via MCP.
Supports skills injection for benchmarking LLMs with/without context.

## Setup

```powershell
pip install mcp aiohttp python-dotenv
git clone https://github.com/Roblox/open-game-eval.git
cd open-game-eval\local_harness
copy .env.example .env
# Edit .env with your API key
```

## Usage

```powershell
python harness.py ^
  --evals-dir ..\Evals ^
  --places-dir ..\Places ^
  --studio-exe "C:\Users\taboo\AppData\Local\Roblox\Versions\version-ac9bdbe6aedb4e5e\RobloxStudioBeta.exe" ^
  --mcp-bat "%LOCALAPPDATA%\Roblox\mcp.bat" ^
  --model-name "your-model" ^
  --api-base "https://your-endpoint/v1" ^
  --pass-n 1
```

## Options

- `--system-prompt-file FILE` — inject skills context (the whole point)
- `--pass-n 1|5` — Pass@1 or Pass@5
- `--eval-filter REGEX` — run subset of evals
- `--screenshots` — capture Studio viewport
- `--output-dir DIR` — results output directory
- `--max-rounds N` — max LLM tool-use rounds (default 25)
- `--startup-wait N` — seconds to wait for Studio (default 20)

## Output

Results saved to `results/results.json` with:
- Per-eval: pass/fail, tokens, latency, tool calls, errors
- Summary: pass rate, avg tokens, avg latency, tool error rate
