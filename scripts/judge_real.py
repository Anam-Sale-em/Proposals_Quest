"""AI judge on the real-job drafts (v2 and plain ChatGPT), which can't live in the repo.

  python scripts/judge_real.py private/real_jobs.json
  python scripts/judge_real.py private/real_jobs.json --hand private/real_hand_scores.csv

real_jobs.json (kept in private/, gitignored):
  {"sources": {"projects": "<my project library as text>", "resume": "<resume text>"},
   "drafts": [{"id": "R1", "job": "short name", "by": "v2" | "chatgpt", "source": "projects" | "resume",
               "post": "<job post>", "draft": "<the final draft>"}]}

Each draft is judged against the material its writer actually had: v2 had my project library,
ChatGPT had my resume or the projects I pasted. Drafts are shuffled and sent without the v2/ChatGPT
label. Results go to private/real_judge.csv; only the totals belong in the docs.

real_hand_scores.csv (optional): id,goal,specific,honest_proof,plan,ask  with yes/no.
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal_v2 import prompts  # noqa: E402
from proposal_v2.contracts import JudgeScore  # noqa: E402
from proposal_v2.llm import LLM  # noqa: E402

ITEMS = ["goal", "specific", "honest_proof", "plan", "ask"]


def passed(s: list[int]) -> bool:
    return sum(s) >= 4 and bool(s[2])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", type=Path)
    ap.add_argument("--hand", type=Path)
    a = ap.parse_args()
    data = json.loads(a.data.read_text(encoding="utf-8"))
    drafts = list(data["drafts"])
    random.Random(5).shuffle(drafts)
    llm = LLM(mode="cache_first")
    rows = []
    for d in drafts:
        system, user = prompts.judge(d["post"], data["sources"][d["source"]], d["draft"])
        score = llm.call("judge_real", "judge", system, user, JudgeScore, 0.0)
        items = {it.item: it for it in score.items}
        s = [int(bool(items.get(n) and items[n].passed)) for n in range(1, 6)]
        rows.append({"id": d["id"], "job": d["job"], "by": d["by"], **dict(zip(ITEMS, s)), "pass": int(passed(s)),
                     "reasons": " | ".join(f"{n}: {items[n].reason}" for n in range(1, 6) if n in items)})
    out = a.data.parent / "real_judge.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["id"]))
    print(f"Judge scores: {out}")
    for by in ("v2", "chatgpt"):
        sub = [r for r in rows if r["by"] == by]
        if sub:
            print(f"  {by}: {sum(r['pass'] for r in sub)} of {len(sub)} pass · honest proof {sum(r['honest_proof'] for r in sub)} of {len(sub)}")
            for r in sorted(sub, key=lambda r: r["id"]):
                fails = [k for k in ITEMS if not r[k]]
                print(f"    {r['id']} {r['job']}: {'pass' if r['pass'] else 'FAIL'}" + (f" (missed: {', '.join(fails)})" if fails else ""))
    if a.hand:
        yes = lambda v: int(str(v).strip().lower() in ("yes", "y", "1"))  # noqa: E731
        hand = {r["id"]: [yes(r[k]) for k in ITEMS] for r in csv.DictReader(open(a.hand, encoding="utf-8"))}
        pairs = [(hand[r["id"]], [r[k] for k in ITEMS]) for r in rows if r["id"] in hand]
        if pairs:
            print(f"\nAgreement with my scores on {len(pairs)} drafts:")
            for n, k in enumerate(ITEMS):
                print(f"  item {n + 1} ({k}): {sum(h[n] == j[n] for h, j in pairs) / len(pairs):.0%}")
            print(f"  pass/fail verdict: {sum(passed(h) == passed(j) for h, j in pairs)} of {len(pairs)} agree")


if __name__ == "__main__":
    main()
