#!/usr/bin/env python3
"""Aggregate results from an agent pool delegation session.

Usage:
    python3 aggregate.py <pool_dir> [--synthesize]

    pool_dir:    Path to ~/.hermes/agent-pool/results/<session_id>/
    --synthesize: Optional. Use LLM to produce a synthesis of all results.

Examples:
    python3 aggregate.py ~/.hermes/agent-pool/results/20260225_143052
    python3 aggregate.py ~/.hermes/agent-pool/results/20260225_143052 --synthesize
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime

POOL_DIR = Path.home() / ".hermes" / "agent-pool" / "results"


def list_results(pool_dir: Path) -> dict:
    """List all result files in the pool directory."""
    if not pool_dir.exists():
        return {"error": f"Directory not found: {pool_dir}"}

    files = sorted(pool_dir.rglob("*"))
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]

    output = {
        "pool_dir": str(pool_dir),
        "session_id": pool_dir.name,
        "files": [],
        "summary": "",
    }

    for f in files:
        rel = f.relative_to(pool_dir)
        output["files"].append({
            "path": str(f),
            "name": f.name,
            "size": f.stat().st_size,
            "type": f.suffix,
        })

    output["summary"] = f"Session {pool_dir.name} — {len(output['files'])} files"
    return output


def read_all_results(pool_dir: Path) -> str:
    """Read all text-readable results into a single string."""
    content_lines = [f"=== Agent Pool Results: {pool_dir.name} ===\n"]

    for f in sorted(pool_dir.rglob("*")):
        if not f.is_file() or f.name.startswith("."):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            content_lines.append(f"\n--- {f.relative_to(pool_dir)} ---\n")
            content_lines.append(text[:10000])  # cap at 10k chars per file
        except Exception as e:
            content_lines.append(f"\n--- {f.name}: [read error: {e}] ---\n")

    return "\n".join(content_lines)


def synthesize_results(pool_dir: Path, api_key: str = None) -> str:
    """Call LLM to synthesize results into a coherent summary."""
    # Check for MiniMax API key in env
    api_key = api_key or os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "[synthesis skipped: no API key in MINIMAX_API_KEY or OPENAI_KEY]"

    results = read_all_results(pool_dir)

    prompt = f"""You are a synthesizer. Given results from multiple specialized agents working in parallel, produce a coherent final summary.

## Task
The agents were all part of a single delegation session. Read their outputs and synthesize them into:
1. A brief executive summary (2-3 sentences)
2. Key findings or deliverables
3. Any conflicts or gaps between agent results
4. Recommended next steps

## Agent Results
{results}

## Output
Format as markdown. Be concise but complete."""

    # Use minimax API if available, else fall back to OpenAI
    try:
        import urllib.request
        import urllib.parse

        # MiniMax M2.7 API
        data = json.dumps({
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
        }).encode()

        req = urllib.request.Request(
            "https://api.minimax.io/anthropic/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[synthesis error: {e}]"


def main():
    parser = argparse.ArgumentParser(description="Aggregate agent pool results")
    parser.add_argument("pool_dir", type=Path, help="Path to pool session directory")
    parser.add_argument("--synthesize", action="store_true", help="LLM-synthesize results")
    parser.add_argument("--list-only", action="store_true", help="Only list files, don't read")
    parser.add_argument("--api-key", type=str, default=None, help="API key for synthesis")
    args = parser.parse_args()

    pool_dir = args.pool_dir
    if not pool_dir.is_absolute():
        pool_dir = POOL_DIR / args.pool_dir

    if args.list_only:
        result = list_results(pool_dir)
        print(json.dumps(result, indent=2))
        return

    results_text = read_all_results(pool_dir)

    if args.synthesize:
        print("=== Raw Results ===")
        print(results_text)
        print("\n=== Synthesis ===")
        synthesis = synthesize_results(pool_dir, args.api_key)
        print(synthesis)
    else:
        print(results_text)


if __name__ == "__main__":
    main()
