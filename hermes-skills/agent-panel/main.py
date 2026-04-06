#!/usr/bin/env python3
"""
Hermes Agent Panel — CLI entry point.
Run multiple agents in parallel, evaluate with DSPy judge, return best answer.
"""

import argparse
import sys
import os

# Load .env if present
from pathlib import Path
env_path = Path.home() / ".hermes" / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k] = v


def main():
    parser = argparse.ArgumentParser(
        description="Hermes Agent Panel — Multi-agent orchestration with DSPy judge"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="The question or task to ask the panel"
    )
    parser.add_argument(
        "-a", "--agents",
        nargs="+",
        default=["general", "coder", "researcher"],
        help="Agent types to use (default: general coder researcher)"
    )
    parser.add_argument(
        "--judge-model",
        default="claude-sonnet-4-5-20250929",
        help="Model for the judge (default: claude-sonnet-4-5-20250929)"
    )
    parser.add_argument(
        "--judge-provider",
        default="anthropic",
        choices=["anthropic", "openai"],
        help="Judge model provider"
    )
    parser.add_argument(
        "--no-refinement",
        action="store_true",
        help="Skip the refinement step"
    )
    parser.add_argument(
        "--no-cot",
        action="store_true",
        help="Disable Chain-of-Thought in the judge"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print verbose progress"
    )
    parser.add_argument(
        "--list-agents",
        action="store_true",
        help="List available agent types and exit"
    )
    parser.add_argument(
        "--optimize",
        action="store_true",
        help="Optimize the judge on collected feedback"
    )

    args = parser.parse_args()

    if args.list_agents:
        from agent_panel.agents import AGENT_REGISTRY
        print("Available agents:")
        for name, cls in AGENT_REGISTRY.items():
            print(f"  {name:<15} — {cls.description}")
        return 0

    if not args.query:
        parser.print_help()
        print("\n--- Examples ---")
        print('python main.py "Best way to handle auth in FastAPI?"')
        print('python main.py "Explain quantum computing" -a general creative researcher')
        print('python main.py --optimize  # optimize judge on feedback data')
        return 0

    if args.optimize:
        from agent_panel import AgentPanel
        panel = AgentPanel()
        print("Optimizing judge on collected feedback...")
        panel.optimize_judge()
        return 0

    # Run the panel
    try:
        from agent_panel import AgentPanel

        panel = AgentPanel(
            judge_model=args.judge_model,
            judge_provider=args.judge_provider,
            use_refinement=not args.no_refinement,
            enable_cot=not args.no_cot,
        )

        print(f"\n{'='*60}")
        print(f"QUERY: {args.query}")
        print(f"{'='*60}")

        result = panel.run(
            query=args.query,
            agent_types=args.agents,
            verbose=args.verbose,
        )

        print(f"\n{'='*60}")
        print(f"WINNER: {result.winner_agent}")
        print(f"{'='*60}")
        print(f"\nJUDGE REASONING:\n{result.judge_reasoning}")
        print(f"\n{'='*60}")
        print(f"BEST ANSWER:\n{result.best_answer}")
        print(f"\n{'='*60}")

        if result.refined_answer and result.refined_answer != result.best_answer:
            print(f"\nREFINED ANSWER:\n{result.refined_answer}")

        # Optionally save feedback prompt
        print("\n[Optional] To record feedback:")
        print(f"  panel.feedback(query={repr(args.query)}, ")
        print(f"            proposals=result.proposals, ")
        print(f"            chosen_agent={repr(result.winner_agent)}, ")
        print(f"            score=5)")

        return 0

    except ImportError as e:
        print(f"Import error: {e}")
        print("\nInstall dependencies:")
        print("  pip install dspy anthropic openai")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
