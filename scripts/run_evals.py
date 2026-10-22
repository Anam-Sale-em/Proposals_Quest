"""Run every frozen test case and write evals/results/<prompt_version>_<time>/.

  python scripts/run_evals.py            # cached responses when present, otherwise live (default)
  python scripts/run_evals.py --replay   # cached responses only: same result every time, offline
  python scripts/run_evals.py --record   # always call the APIs and refresh the cache
  python scripts/run_evals.py T05 T11    # only these cases
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal_v2.evaluation import run_all  # noqa: E402
from proposal_v2.llm import LLM  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="*")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--replay", action="store_true")
    g.add_argument("--record", action="store_true")
    a = ap.parse_args()
    mode = "replay" if a.replay else "live" if a.record else "cache_first"
    out = run_all(LLM(mode=mode), only=a.cases or None)
    print(f"\nResults: {out / 'results.csv'}\nSummary: {out / 'summary.md'}")


if __name__ == "__main__":
    main()
