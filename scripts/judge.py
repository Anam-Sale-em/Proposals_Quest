"""AI judge: scores drafts on the 5-item rubric with the v1/v2/baseline labels removed.

  python scripts/judge.py evals/results/<run>            # v2 drafts from a run + the ChatGPT baseline drafts
  python scripts/judge.py evals/results/<run> --hand evals/rubric_scores_live_v2.0.6.csv
  python scripts/judge.py --real private/real_jobs.json   # real jobs: v2 and ChatGPT drafts on the same posts

The judge is a different model (config [models].judge) from the drafting models, so nothing
grades itself. With --hand, agreement with my own scores is reported per rubric item; items
where the judge disagrees with me are scored by hand only.

--hand takes my rubric scores as evals/rubric_scores_live_*.csv writes them (case, run, goal, specific,
honest_proof, plan, ask with yes/no). The rows for this run are matched by case. The ChatGPT baseline
drafts are matched against my scores in evals/baseline.md (5 of 5 on T01-T03).
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
    ap.add_argument("run", type=Path, nargs="?")
    ap.add_argument("--hand", type=Path)
    ap.add_argument("--real", type=Path, help="JSON list of {id, job, source, post, profile, draft}; kept in private/")
    a = ap.parse_args()
    if a.real:
        return judge_real(a.real)
    if not a.run or not (a.run / "drafts").is_dir():
        found = sorted(p.name for p in (ROOT / "evals" / "results").glob("*") if (p / "drafts").is_dir())
        sys.exit(f"No drafts folder in {a.run}. Runs with drafts: {', '.join(found[-5:]) or 'none yet'}. "
                 "Copy the folder name exactly.")
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
        report_agreement(rows, a.hand, a.run.name)


ITEMS = ["goal", "specific", "honest_proof", "plan", "ask"]


def judge_real(path: Path) -> None:
    """Scores real-job drafts (the posts and my real projects stay in private/). Same judge, same rubric;
    the judge never sees which tool wrote a draft."""
    jobs = json.loads(path.read_text(encoding="utf-8"))
    random.Random(7).shuffle(jobs)
    llm = LLM(mode="cache_first")
    rows = []
    for j in jobs:
        system, user = prompts.judge(j["post"], j["profile"], j["draft"])
        score = llm.call("judge", "judge", system, user, JudgeScore, 0.0)
        items = {it.item: it.passed for it in score.items}
        rows.append({"id": j["id"], "job": j["job"], "source": j["source"],
                     **{f"item{n}": int(items.get(n, False)) for n in range(1, 6)},
                     "rubric_pass": int(sum(items.get(n, False) for n in range(1, 6)) >= 4 and items.get(3, False)),
                     "reasons": " | ".join(f"{it.item}: {it.reason}" for it in score.items)})
    rows.sort(key=lambda r: (r["id"], r["source"]))
    out = path.with_name("real_judge.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"Judge scores: {out}")
    for r in rows:
        marks = "".join("Y" if r[f"item{n}"] else "-" for n in range(1, 6))
        print(f"  {r['id']} {r['source']:<8} {marks}  {'PASS' if r['rubric_pass'] else 'fail'}  {r['job']}")
    for src in sorted({r["source"] for r in rows}):
        sub = [r for r in rows if r["source"] == src]
        if sub:
            print(f"  {src}: {sum(r['rubric_pass'] for r in sub)} of {len(sub)} pass")


def report_agreement(rows: list[dict], hand_path: Path, run_name: str) -> None:
    """Per-item agreement between the judge and my hand scores, matched by source and case."""
    hand = {}
    for r in csv.DictReader(open(hand_path, encoding="utf-8")):
        if r.get("run") == run_name:
            hand[("v2", r["case"])] = [int(r[k].strip().lower() == "yes") for k in ITEMS]
    for case in ("T01", "T02", "T03"):  # baseline.md: every ChatGPT draft scored 5 of 5 by me
        hand.setdefault(("chatgpt", case), [1, 1, 1, 1, 1])
    pairs = [(hand[(r["source"], r["case"])], [r[f"item{n}"] for n in range(1, 6)]) for r in rows
             if (r["source"], r["case"]) in hand]
    if not pairs:
        print(f"\nNo hand scores in {hand_path} match run {run_name}.")
        return
    print(f"\nAgreement with my scores on {len(pairs)} drafts, per rubric item:")
    for n, name in enumerate(ITEMS):
        agree = sum(h[n] == j[n] for h, j in pairs) / len(pairs)
        flag = "" if agree >= 0.8 else "  -> score this item by hand only"
        print(f"  item {n + 1} ({name}): {agree:.0%}{flag}")
    both = sum((sum(h) >= 4 and h[2]) == (sum(j) >= 4 and j[2]) for h, j in pairs)
    print(f"  pass/fail verdict: {both} of {len(pairs)} agree")

if __name__ == "__main__":
    main()
