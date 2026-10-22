"""AI judge: scores drafts on the 5-item rubric with the v1/v2/baseline labels removed.

  python scripts/judge.py evals/results/<run>            # v2 drafts from a run + the ChatGPT baseline drafts
  python scripts/judge.py evals/results/<run> --hand evals/hand_scores.csv

The judge is a different model (config [models].judge) from the drafting models, so nothing
grades itself. With --hand, agreement with my own scores is reported per rubric item; items
where the judge disagrees with me are scored by hand only.

hand_scores.csv columns: draft_id,item1,item2,item3,item4,item5   (1 = pass, 0 = fail)
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal_v2 import prompts  # noqa: E402
from proposal_v2.config import ROOT  # noqa: E402
from proposal_v2.contracts import JudgeScore  # noqa: E402
from proposal_v2.llm import LLM  # noqa: E402


def load_drafts(run: Path) -> list[dict]:
    drafts = []
    for f in sorted((run / "drafts").glob("T*.md")):
        drafts.append({"source": "v2", "case": f.stem, "text": f.read_text(encoding="utf-8").split("\n", 2)[-1]})
    for f in sorted((ROOT / "evals" / "baseline_runs").glob("chatgpt_T*_raw.txt")):
        drafts.append({"source": "chatgpt", "case": f.stem.split("_")[1], "text": f.read_text(encoding="utf-8")})
    return drafts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--hand", type=Path)
    a = ap.parse_args()
    profile = (ROOT / "fixtures" / "profile_sample.json").read_text(encoding="utf-8")
    drafts = load_drafts(a.run)
    random.Random(7).shuffle(drafts)
    llm = LLM(mode="cache_first")
    rows = []
    for i, d in enumerate(drafts, 1):
        job = json.loads((ROOT / "fixtures" / "jobs" / f"{d['case']}.json").read_text(encoding="utf-8"))
        system, user = prompts.judge(job["pastes"][0]["job_details"], profile, d["text"])
        score = llm.call("judge", "judge", system, user, JudgeScore, 0.0)
        items = {it.item: it.passed for it in score.items}
        passed = sum(items.get(n, False) for n in range(1, 6))
        rows.append({"draft_id": f"D{i:02d}", "source": d["source"], "case": d["case"],
                     **{f"item{n}": int(items.get(n, False)) for n in range(1, 6)},
                     "rubric_pass": int(passed >= 4 and items.get(3, False)),
                     "reasons": " | ".join(f"{it.item}: {it.reason}" for it in score.items)})
    out = a.run / "judge.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Judge scores: {out}")
    for src in ("v2", "chatgpt"):
        sub = [r for r in rows if r["source"] == src]
        if sub:
            print(f"  {src}: {sum(r['rubric_pass'] for r in sub)} of {len(sub)} pass")

    if a.hand:
        hand = {r["draft_id"]: r for r in csv.DictReader(open(a.hand, encoding="utf-8"))}
        by_id = {r["draft_id"]: r for r in rows}
        print("\nAgreement with my scores, per rubric item:")
        for n in range(1, 6):
            pairs = [(int(h[f"item{n}"]), by_id[i][f"item{n}"]) for i, h in hand.items() if i in by_id]
            if pairs:
                agree = sum(x == y for x, y in pairs) / len(pairs)
                flag = "" if agree >= 0.8 else "  -> score this item by hand only"
                print(f"  item {n}: {agree:.0%} of {len(pairs)}{flag}")


if __name__ == "__main__":
    main()
