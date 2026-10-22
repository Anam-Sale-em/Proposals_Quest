"""Eval runner: runs every frozen fixture through the real pipeline and checks it against
evals/test_cases.json. Each case gets a fresh workspace. Writes a CSV, a summary and the drafts."""
from __future__ import annotations

import csv
import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

from .config import ROOT, load_config, prompt_version
from .llm import LLM, LLMError, git_commit
from .links import LinkError
from .pipeline import DuplicateJob, Pipeline, PipelineError
from .sample import load_sample
from .storage import JsonStorage

EVALS = ROOT / "evals"
DECISION_MAP = {"Apply": ("apply", None), "Apply with questions": ("apply_with_questions", None),
                "Skip: work type": ("skip", "work_type"), "Skip: below your minimum": ("skip", "below_minimum"),
                "Skip: red flag": ("skip", "red_flag"), "Skip: low fit": ("skip", "low_fit"),
                "Skip: medium fit with low trust": ("skip", "medium_low_trust")}
GATE_MAP = {"pass": "pass", "below minimum": "below_minimum", "off: placeholder": "placeholder"}
CLIENT_FIELDS = ["payment_verified", "rating", "reviews", "jobs_posted", "hire_rate_pct", "total_spent_usd", "hires", "active_hires"]
DRAFT_STEPS = {"brief", "proposal", "proposal_retry", "revise"}


def _expected_decision(exp: dict) -> tuple[str, Optional[str]]:
    d = exp["decision"]
    return DECISION_MAP.get(d.split(",")[0].strip(), (d, None))


def run_case(case: dict, llm: LLM, workdir: Path) -> dict:
    fixture = json.loads((ROOT / case["fixture"]).read_text(encoding="utf-8"))
    exp = case["expected"]
    storage = JsonStorage(workdir / case["id"])
    load_sample(storage, uid="eval")
    pipe = Pipeline(storage, llm, "eval")
    start_calls = len(llm.calls)
    t0 = time.time()
    checks: dict[str, bool] = {}
    notes: list[str] = []
    rec = None
    paste = fixture["pastes"][0]
    try:
        rec = pipe.extract(paste["link"], paste["job_details"])
        rec = pipe.decide(rec)
        if rec.decision.decision != "skip":
            rec = pipe.write(rec)
    except (LinkError, PipelineError, LLMError) as e:
        notes.append(f"error: {e}")
    elapsed = round(time.time() - t0, 1)
    case_calls = llm.calls[start_calls:]
    steps = [c.step for c in case_calls if not c.error]

    if rec is not None:
        checks["job_key"] = rec.job_key == exp["job_key"]
        checks["link_status"] = rec.job.link_status == exp["link_status"]
        got_client = rec.client.model_dump()
        for f in CLIENT_FIELDS:
            want = exp["client"].get(f)
            if want is not None:
                ok = got_client.get(f) is not None and abs(float(got_client[f]) - float(want)) < 0.051
                checks[f"client.{f}"] = ok
        flags_got = {f.kind for f in rec.job.red_flags}
        for flag in exp["client"].get("post_flags", []):
            checks[f"red_flag.{flag}"] = flag in flags_got
        if not exp["client"].get("post_flags"):
            checks["no_false_red_flag"] = not flags_got
        checks["trust"] = rec.trust is not None and rec.trust.band == exp["trust"]["band"] and rec.trust.score == exp["trust"]["score"]
        checks["budget_gate"] = rec.decision.budget_gate == GATE_MAP.get(exp["budget"]["gate"], exp["budget"]["gate"])
        want_dec, want_code = _expected_decision(exp)
        checks["decision"] = rec.decision.decision == want_dec and (want_code is None or rec.decision.code == want_code)
        if exp.get("card_note"):
            checks["card_note"] = bool(rec.decision.card_note) and exp["card_note"] in rec.decision.card_note
        if case["id"] == "T04":
            checks["placeholder_flagged"] = rec.decision.code == "placeholder" or "placeholder" in (rec.decision.card_note or "")
        if want_dec == "skip":
            checks["no_draft_calls"] = not (DRAFT_STEPS & set(steps))
        if want_code in ("red_flag", "below_minimum"):
            checks["no_assessment_call"] = "assess" not in steps
        if exp.get("proof"):
            checks["proof"] = rec.chosen_proof == exp["proof"]
            want_framing = (exp.get("framing") or "").replace("-", "_")
            if want_framing:
                checks["framing"] = rec.framing == want_framing
        v = rec.latest()
        if v:
            checks["validators_pass"] = v.validation.ok
            text = v.text
            if case["id"] == "T05":
                checks["starts_with_blue_whale"] = text.strip().lower().lstrip("\"'“*_").startswith("blue whale")
            if case["id"] == "T11":
                checks["no_10_years_claim"] = "10 years" not in (text + " ".join(a.answer for a in v.screening_answers)).lower()
                checks["instruction_logged"] = bool(rec.job.ignored_instructions or rec.job.refused_instructions)
            if case["id"] == "T06":
                checks["length_ok"] = v.validation.length_ok
                checks["screening_answers"] = len([a for a in v.screening_answers if a.answer.strip()]) >= max(3, len(rec.job.screening_questions))
            if case["id"] == "T02":
                checks["no_hubspot_claim"] = not any("hubspot" in s.lower() for s in v.validation.experience_failures)
        elif want_dec != "skip":
            checks["draft_written"] = False

    # T12: the second paste is blocked before extraction, with no LLM call and one record.
    if exp.get("second_paste"):
        before = len(llm.calls)
        blocked = False
        try:
            pipe.check_link(exp["second_paste"]["link"])
        except DuplicateJob:
            blocked = True
        except LinkError as e:
            notes.append(f"second paste link error: {e}")
        checks["second_paste_blocked"] = blocked
        checks["second_paste_no_llm"] = len(llm.calls) == before
        checks["one_record"] = len(storage.list_proposals("eval")) == 1

    v = rec.latest() if rec else None
    failed = [k for k, ok in checks.items() if not ok]
    return {
        "case": case["id"], "type": case["type"], "case_text": case["case"],
        "expected_decision": exp["decision"], "got_decision": (f"{rec.decision.decision}:{rec.decision.code}" if rec and rec.decision else "error"),
        "expected_trust": f"{exp['trust']['score']} {exp['trust']['band']}",
        "got_trust": f"{rec.trust.score} {rec.trust.band}" if rec and rec.trust else "",
        "pass": bool(checks) and not failed and not notes,
        "checks_passed": len(checks) - len(failed), "checks_total": len(checks), "failed_checks": "; ".join(failed),
        "validation": v.validation.status if v else "", "retried": v.validation.retried if v else "",
        "claim_notes": " | ".join(v.validation.notes) if v else "",
        "llm_calls": len([c for c in case_calls if not c.error]), "draft_model_calls": len([c for c in case_calls if c.step in DRAFT_STEPS and not c.error]),
        "cache_hits": len([c for c in case_calls if c.cached]), "errors": len([c for c in case_calls if c.error]),
        "providers": ",".join(sorted({c.provider for c in case_calls if not c.error})),
        "latency_s": elapsed, "tokens_in": sum(c.tokens_in for c in case_calls), "tokens_out": sum(c.tokens_out for c in case_calls),
        "draft_words": len(v.text.split()) if v else 0, "draft_chars": len(v.text) if v else 0,
        "notes": " | ".join(notes),
        "rubric_1_goal": "", "rubric_2_specific": "", "rubric_3_proof": "", "rubric_4_plan": "", "rubric_5_ask": "",
        "unsupported_claims_hand": "",
        "_draft": v.text if v else "", "_answers": [a.model_dump() for a in v.screening_answers] if v else [],
        "_brief": rec.brief.model_dump() if rec and rec.brief else None,
    }


def run_all(llm: LLM, only: Optional[list[str]] = None, out_root: Optional[Path] = None,
            progress: Callable[[str], None] = print) -> Path:
    cases = json.loads((EVALS / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    if only:
        cases = [c for c in cases if c["id"] in only]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = (out_root or EVALS / "results") / f"{prompt_version()}_{stamp}"
    (out / "drafts").mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="pv2-eval-"))
    rows = []
    try:
        for case in cases:
            progress(f"{case['id']} ...")
            row = run_case(case, llm, work)
            rows.append(row)
            progress(f"{case['id']}: {'PASS' if row['pass'] else 'FAIL'} ({row['checks_passed']}/{row['checks_total']}) {row['failed_checks']} {row['notes']}")
            if row["_draft"]:
                answers = "\n".join(f"**{a['question']}**\n{a['answer']}\n" for a in row["_answers"])
                (out / "drafts" / f"{case['id']}.md").write_text(f"# {case['id']}: {case['case']}\n\n{row['_draft']}\n\n{answers}", encoding="utf-8")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    fields = [k for k in rows[0] if not k.startswith("_")] if rows else []
    with open(out / "results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in fields})
    _summary(out, rows, llm)
    return out


def _summary(out: Path, rows: list[dict], llm: LLM) -> None:
    lat = sorted(r["latency_s"] for r in rows if r["latency_s"])

    def pct(p):
        return lat[min(len(lat) - 1, int(round(p * (len(lat) - 1))))] if lat else 0

    prices = load_config().get("prices", {})
    tin, tout = sum(r["tokens_in"] for r in rows), sum(r["tokens_out"] for r in rows)
    lines = [
        f"# Eval run {out.name}", "",
        f"- prompt_version: {prompt_version()} · commit: {git_commit()} · LLM mode: {llm.mode}",
        f"- Cases passed: **{sum(r['pass'] for r in rows)} of {len(rows)}**",
        f"- Checks passed: {sum(r['checks_passed'] for r in rows)} of {sum(r['checks_total'] for r in rows)}",
        f"- Drafts needing review after the retry: {sum(1 for r in rows if r['validation'] == 'needs_review')}",
        f"- Drafts that needed the retry: {sum(1 for r in rows if r['retried'] is True)}",
        f"- Latency per case: p50 {pct(0.5)} s, p95 {pct(0.95)} s",
        f"- Tokens: {tin} in, {tout} out" + (f" · list-price cost ${tin / 1e6 * prices.get('input_per_m', 0) + tout / 1e6 * prices.get('output_per_m', 0):.4f}" if prices else ""),
        f"- LLM errors (retried or fell back): {sum(r['errors'] for r in rows)}",
        "", "| Case | Type | Expected | Got | Trust (exp → got) | Result | Failed checks |", "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r['case']} | {r['type']} | {r['expected_decision']} | {r['got_decision']} | {r['expected_trust']} → {r['got_trust']} | "
                     f"{'PASS' if r['pass'] else 'FAIL'} | {r['failed_checks'] or r['notes']} |")
    lines += ["", "Rubric scores and unsupported claims are filled in by hand in results.csv, then by `scripts/judge.py`."]
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
