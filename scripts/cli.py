"""v0 in the terminal: one job from paste to proposal, no UI.

  python scripts/cli.py --link URL --file job.txt [--client-file box.txt] [--workspace sample]
  python scripts/cli.py --fixture T01
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from proposal_v2.config import ROOT  # noqa: E402
from proposal_v2.links import LinkError  # noqa: E402
from proposal_v2.llm import LLMError, make_llm  # noqa: E402
from proposal_v2.pipeline import DuplicateJob, Pipeline, PipelineError  # noqa: E402
from proposal_v2.sample import load_sample  # noqa: E402
from proposal_v2.storage import make_storage  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--link")
    ap.add_argument("--file")
    ap.add_argument("--client-file", default="")
    ap.add_argument("--fixture")
    ap.add_argument("--workspace", default="sample")
    a = ap.parse_args()
    if a.fixture:
        d = json.loads((ROOT / "fixtures" / "jobs" / f"{a.fixture}.json").read_text(encoding="utf-8"))
        link, text = d["pastes"][0]["link"], d["pastes"][0]["job_details"]
    else:
        link, text = a.link, Path(a.file).read_text(encoding="utf-8")
    client = Path(a.client_file).read_text(encoding="utf-8") if a.client_file else ""
    storage = make_storage()
    if a.workspace == "sample":
        load_sample(storage)
    pipe = Pipeline(storage, make_llm(), a.workspace)
    try:
        rec = pipe.extract(link, text, client)
        print(f"Job: {rec.job.title}\nLink check: {rec.job.link_status}\nBudget: {rec.job.budget.raw_text}")
        rec = pipe.decide(rec)
        t = rec.trust
        print(f"Trust: {t.score} {t.band} ({t.coverage})\n  " + "\n  ".join(t.reasons[:3]))
        print(f"\nDECISION: {rec.decision.reason}" + (f" [{rec.decision.card_note}]" if rec.decision.card_note else ""))
        if rec.decision.decision == "skip":
            return
        rec = pipe.write(rec)
        v = rec.latest()
        print(f"\nProof: {rec.chosen_proof or 'plan only'} ({rec.framing})\n\n{v.text}\n")
        for ans in v.screening_answers:
            print(f"Q: {ans.question}\nA: {ans.answer}\n")
        print(f"Claim check: {v.validation.status}" + ("" if v.validation.ok else "\n  " + "\n  ".join(v.validation.notes)))
    except DuplicateJob as e:
        print(f"{e} (status: {e.record.status})")
    except (LinkError, PipelineError, LLMError) as e:
        print(f"Stopped: {e}")


if __name__ == "__main__":
    main()
