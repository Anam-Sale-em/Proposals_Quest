"""Blind scoring by a second person: drafts shuffled, labels removed, then agreement with my scores.

  python scripts/blind_pack.py make evals/results/<run>
      writes <run>/blind/pack.md (rubric, each job post and its draft as D01, D02...),
      <run>/blind/scores.csv (empty sheet for the scorer) and <run>/blind/key.csv (keep this to yourself)

  python scripts/blind_pack.py compare evals/results/<run> --hand evals/rubric_scores_live_v2.0.6.csv
      after the scorer fills scores.csv (yes/no per item): agreement per item and per verdict

The pack mixes v2's drafts with the plain-ChatGPT baseline drafts, so the scorer can't tell which is which.
"""
import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from judge import ITEMS, load_drafts  # noqa: E402
from proposal_v2.config import ROOT  # noqa: E402


def make(run: Path) -> None:
    drafts = load_drafts(run)
    random.Random(11).shuffle(drafts)
    out = run / "blind"
    out.mkdir(exist_ok=True)
    profile = json.loads((ROOT / "fixtures" / "profile_sample.json").read_text(encoding="utf-8"))
    lines = ["# Blind scoring pack", "",
             "Score each draft yes or no on the five rubric items in scores.csv. You don't need to know who wrote it.", "",
             (ROOT / "evals" / "rubric.md").read_text(encoding="utf-8").split("## How drafts are scored")[0], "",
             "## The freelancer's profile and projects (the only allowed source of past work)", "",
             "```json", json.dumps(profile, indent=2, ensure_ascii=False), "```", ""]
    key = []
    for i, d in enumerate(drafts, 1):
        did = f"D{i:02d}"
        post = json.loads((ROOT / "fixtures" / "jobs" / f"{d['case']}.json").read_text(encoding="utf-8"))["pastes"][0]["job_details"]
        lines += [f"## {did}", "", "**Job post**", "", "```", post.strip(), "```", "", "**Draft**", "", d["text"].strip(), ""]
        key.append({"draft_id": did, "source": d["source"], "case": d["case"]})
    (out / "pack.md").write_text("\n".join(lines), encoding="utf-8")
    with open(out / "key.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["draft_id", "source", "case"])
        w.writeheader()
        w.writerows(key)
    with open(out / "scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["draft_id", *ITEMS, "notes"])
        for k in key:
            w.writerow([k["draft_id"], "", "", "", "", "", ""])
    print(f"Send {out / 'pack.md'} and {out / 'scores.csv'} to the scorer. Keep {out / 'key.csv'}.")


def compare(run: Path, hand_path: Path) -> None:
    key = {r["draft_id"]: r for r in csv.DictReader(open(run / "blind" / "key.csv", encoding="utf-8"))}
    yes = lambda v: int(str(v).strip().lower() in ("yes", "y", "1"))  # noqa: E731
    theirs = {(key[r["draft_id"]]["source"], key[r["draft_id"]]["case"]): [yes(r[k]) for k in ITEMS]
              for r in csv.DictReader(open(run / "blind" / "scores.csv", encoding="utf-8")) if r["draft_id"] in key}
    mine = {("v2", r["case"]): [yes(r[k]) for k in ITEMS]
            for r in csv.DictReader(open(hand_path, encoding="utf-8")) if r.get("run") == run.name}
    for case in ("T01", "T02", "T03"):  # baseline.md: I scored every ChatGPT draft 5 of 5
        mine.setdefault(("chatgpt", case), [1, 1, 1, 1, 1])
    pairs = [(mine[k], theirs[k]) for k in theirs if k in mine]
    if not pairs:
        print("No drafts in common between scores.csv and the hand scores for this run.")
        return
    passed = lambda s: sum(s) >= 4 and s[2]  # noqa: E731
    print(f"Second scorer vs me, {len(pairs)} drafts, labels hidden from them:")
    for n, name in enumerate(ITEMS):
        print(f"  item {n + 1} ({name}): {sum(a[n] == b[n] for a, b in pairs) / len(pairs):.0%}")
    print(f"  pass/fail verdict: {sum(passed(a) == passed(b) for a, b in pairs)} of {len(pairs)} agree")
    for src in ("v2", "chatgpt"):
        sub = [b for k, b in theirs.items() if k[0] == src]
        if sub:
            print(f"  their pass count, {src}: {sum(passed(b) for b in sub)} of {len(sub)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["make", "compare"])
    ap.add_argument("run", type=Path)
    ap.add_argument("--hand", type=Path, default=ROOT / "evals" / "rubric_scores_live_v2.0.6.csv")
    a = ap.parse_args()
    make(a.run) if a.action == "make" else compare(a.run, a.hand)


if __name__ == "__main__":
    main()
