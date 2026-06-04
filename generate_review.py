#!/usr/bin/env python3
"""
generate_review.py — Generate a detailed observational review from OpenGameEval results.

Usage:
    python generate_review.py results/vanilla_0603_1634/results.json
    python generate_review.py results/vanilla_0603_1634/results.json --output review.md
"""
import json
import sys
import argparse
from pathlib import Path
from collections import Counter


def load_results(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_tool_usage(evals: list) -> dict:
    """Analyze tool usage patterns across all evals."""
    tool_counts = Counter()
    tool_errors = Counter()
    total_calls = 0
    total_errors = 0

    for ev in evals:
        tools = ev.get("tools_used", "")
        if isinstance(tools, str):
            tools = tools.split() if tools else []
        for t in tools:
            tool_counts[t] += 1
        total_calls += ev.get("tool_calls", 0)
        total_errors += ev.get("tool_errors", 0)

    error_rate = total_errors / total_calls if total_calls > 0 else 0
    avg_calls = total_calls / len(evals) if evals else 0

    return {
        "tool_counts": tool_counts,
        "total_calls": total_calls,
        "total_errors": total_errors,
        "error_rate": error_rate,
        "avg_calls_per_eval": avg_calls,
    }


def categorize_failures(evals: list) -> dict:
    """Categorize failures by error type and pattern."""
    categories = Counter()
    failure_details = []

    for ev in evals:
        if ev.get("passed"):
            continue
        cat = ev.get("error_category", "unknown")
        categories[cat] += 1
        error = ev.get("error", "") or ""
        failure_details.append({
            "scenario": ev.get("scenario", "?"),
            "category": cat,
            "error": error[:200],
            "rounds": ev.get("rounds_used", 0),
            "tokens_in": ev.get("total_tokens_in", 0),
            "tool_calls": ev.get("tool_calls", 0),
            "edit_count": ev.get("edit_count", 0),
        })

    return {
        "categories": categories,
        "details": failure_details,
    }


def analyze_behavioral_patterns(evals: list) -> dict:
    """Identify behavioral patterns from eval data."""
    patterns = {
        "under_exploration": [],  # few tool calls, failed
        "over_exploration": [],   # many tool calls, failed
        "no_edits": [],           # failed without making any edits
        "high_token_fail": [],    # used lots of tokens but failed
        "quick_pass": [],         # passed in few rounds
        "multi_edit_pass": [],    # passed with multiple edits
    }

    for ev in evals:
        rounds = ev.get("rounds_used", 0)
        tokens = ev.get("total_tokens_in", 0)
        tools = ev.get("tool_calls", 0)
        edits = ev.get("edit_count", 0)
        passed = ev.get("passed", False)
        scenario = ev.get("scenario", "?")

        if passed:
            if rounds <= 3:
                patterns["quick_pass"].append(scenario)
            if edits >= 2:
                patterns["multi_edit_pass"].append(scenario)
        else:
            if tools <= 3:
                patterns["under_exploration"].append(scenario)
            if tools >= 15:
                patterns["over_exploration"].append(scenario)
            if edits == 0:
                patterns["no_edits"].append(scenario)
            if tokens > 300000:
                patterns["high_token_fail"].append(scenario)

    return patterns


def generate_review(data: dict) -> str:
    """Generate a markdown review from results data."""
    summary = data.get("summary", {})
    model = data.get("model", {})
    config = data.get("config", {})
    evals = data.get("evals", [])

    if not evals:
        return "No eval data found."

    tool_analysis = analyze_tool_usage(evals)
    failures = categorize_failures(evals)
    patterns = analyze_behavioral_patterns(evals)

    total = summary.get("total_evals", len(evals))
    passed = summary.get("passed", 0)
    pass_rate = summary.get("pass_rate", 0)
    avg_rounds = summary.get("avg_llm_calls", 0)
    avg_tokens = summary.get("avg_tokens_in", 0)
    avg_latency = summary.get("avg_latency_ms", 0)
    avg_edits = summary.get("avg_edit_count", 0)
    avg_ctx = summary.get("avg_max_context_tokens", 0)

    lines = []
    lines.append(f"# {model.get('name', 'Unknown')} — Detailed Review")
    lines.append("")
    lines.append(f"**Eval Suite**: {total} evals (open-game-eval/Evals + DebugEvals)")
    lines.append(f"**Configuration**: k={config.get('pass_n', 1)}, timeout={config.get('eval_timeout', '?')}s")
    lines.append(f"**API**: `{model.get('api_base', '?')}`")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(f"- **Pass Rate**: {pass_rate}% ({passed}/{total})")
    lines.append(f"- **Avg Rounds/Eval**: {avg_rounds:.1f}")
    lines.append(f"- **Avg Tokens In/Eval**: {avg_tokens:,.0f}")
    lines.append(f"- **Avg Latency/Eval**: {avg_latency/1000:.1f}s")
    lines.append(f"- **Avg Edits/Eval**: {avg_edits:.1f}")
    lines.append(f"- **Avg Peak Context**: {avg_ctx:,.0f} tokens")
    lines.append("")

    # Error Breakdown
    lines.append("## Error Breakdown")
    lines.append("")
    for cat, count in failures["categories"].most_common():
        pct = count / (total - passed) * 100 if (total - passed) > 0 else 0
        lines.append(f"- **{cat}**: {count} ({pct:.0f}% of failures)")
    lines.append("")

    # Tool Usage
    lines.append("## Tool Usage")
    lines.append("")
    lines.append(f"- **Total Tool Calls**: {tool_analysis['total_calls']}")
    lines.append(f"- **Avg Calls/Eval**: {tool_analysis['avg_calls_per_eval']:.1f}")
    lines.append(f"- **Tool Error Rate**: {tool_analysis['error_rate']*100:.2f}%")
    lines.append("")
    lines.append("**Tool Distribution** (number of evals using each tool):")
    lines.append("")
    for tool, count in tool_analysis["tool_counts"].most_common(10):
        lines.append(f"- `{tool}`: {count} evals")
    lines.append("")

    # Token Efficiency
    lines.append("## Token Efficiency")
    lines.append("")
    total_tokens = sum(ev.get("total_tokens_in", 0) for ev in evals)
    lines.append(f"- **Total Tokens Used**: {total_tokens:,.0f}")
    tokens_per_pass = total_tokens / passed if passed > 0 else float("inf")
    lines.append(f"- **Tokens per Successful Eval**: {tokens_per_pass:,.0f}")
    lines.append("")

    # Behavioral Patterns
    lines.append("## Behavioral Patterns")
    lines.append("")

    if patterns["under_exploration"]:
        lines.append(f"### Under-Exploration ({len(patterns['under_exploration'])} evals)")
        lines.append("Model made ≤3 tool calls and failed. May not have explored enough:")
        lines.append("")
        for s in patterns["under_exploration"][:5]:
            lines.append(f"- `{s}`")
        lines.append("")

    if patterns["no_edits"]:
        lines.append(f"### No Edits on Failure ({len(patterns['no_edits'])} evals)")
        lines.append("Model failed without making any code edits:")
        lines.append("")
        for s in patterns["no_edits"][:5]:
            lines.append(f"- `{s}`")
        lines.append("")

    if patterns["over_exploration"]:
        lines.append(f"### Over-Exploration ({len(patterns['over_exploration'])} evals)")
        lines.append("Model used ≥15 tool calls but still failed:")
        lines.append("")
        for s in patterns["over_exploration"][:5]:
            lines.append(f"- `{s}`")
        lines.append("")

    if patterns["high_token_fail"]:
        lines.append(f"### High-Token Failures ({len(patterns['high_token_fail'])} evals)")
        lines.append("Model used >300K tokens but failed:")
        lines.append("")
        for s in patterns["high_token_fail"][:5]:
            lines.append(f"- `{s}`")
        lines.append("")

    if patterns["quick_pass"]:
        lines.append(f"### Quick Passes ({len(patterns['quick_pass'])} evals)")
        lines.append("Model passed in ≤3 rounds:")
        lines.append("")
        for s in patterns["quick_pass"]:
            lines.append(f"- `{s}`")
        lines.append("")

    # Per-Eval Results
    lines.append("## Per-Eval Results")
    lines.append("")
    for ev in evals:
        status = "✅" if ev.get("passed") else "❌"
        scenario = ev.get("scenario", "?")
        rounds = ev.get("rounds_used", 0)
        tokens = ev.get("total_tokens_in", 0)
        edits = ev.get("edit_count", 0)
        cat = ev.get("error_category", "")
        error = ev.get("error", "") or ""

        line = f"- {status} `{scenario}` — {rounds} rounds, {tokens:,} tokens, {edits} edits"
        if not ev.get("passed") and cat:
            line += f" [{cat}]"
        if error and len(error) > 80:
            error = error[:80] + "..."
        if error:
            line += f" — {error}"
        lines.append(line)

    lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    if failures["categories"].get("timeout", 0) > 3:
        lines.append("- **Timeouts**: Multiple evals timed out. Consider increasing eval timeout or improving model efficiency.")
    if len(patterns["under_exploration"]) > 5:
        lines.append("- **Under-Exploration**: Model frequently fails to explore the game tree sufficiently. System prompt should encourage deeper exploration before acting.")
    if len(patterns["no_edits"]) > 5:
        lines.append("- **No Edits**: Model often fails without making any changes. May lack confidence or understanding of the task.")
    if tool_analysis["error_rate"] > 0.05:
        lines.append(f"- **Tool Errors**: {tool_analysis['error_rate']*100:.1f}% error rate is high. Check for API issues or incorrect tool usage.")
    if pass_rate < 30:
        lines.append("- **Low Pass Rate**: Model struggles with most evals. May need stronger model or better system prompt.")
    elif pass_rate < 50:
        lines.append("- **Moderate Pass Rate**: Model handles simpler tasks but struggles with complex ones. Focus on improving exploration and multi-step reasoning.")
    else:
        lines.append("- **Good Pass Rate**: Model performs well on this eval set.")

    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate a detailed review from OpenGameEval results")
    parser.add_argument("results_json", help="Path to results.json")
    parser.add_argument("--output", "-o", default=None, help="Output file (default: stdout)")
    args = parser.parse_args()

    data = load_results(args.results_json)
    review = generate_review(data)

    if args.output:
        Path(args.output).write_text(review, encoding="utf-8")
        print(f"Review written to {args.output}")
    else:
        print(review)


if __name__ == "__main__":
    main()
