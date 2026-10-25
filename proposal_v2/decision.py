"""Budget gate, fit band and the decision. All in code, no LLM."""
from __future__ import annotations

from typing import Optional

from .config import load_config
from .contracts import Assessment, Budget, Decision, FitResult, Profile, TrustResult

TABLE = {
    "High": {"Excellent": "Apply", "High": "Apply", "Medium": "Apply",
             "Low": "Apply, low-trust warning", "Unknown": "Apply, check client manually"},
    "Medium": {"Excellent": "Apply", "High": "Apply", "Medium": "Apply",
               "Low": "Skip", "Unknown": "Apply, check client manually"},
    "Low": {b: "Skip" for b in ["Excellent", "High", "Medium", "Low", "Unknown"]},
}


def budget_gate(budget: Budget, profile: Profile) -> tuple[str, str]:
    """Returns (gate, plain text). gate: pass | below_minimum | placeholder | none_stated | no_minimum."""
    floor = load_config()["budget"]["placeholder_floor_usd"]
    k = budget.kind
    if k == "hourly":
        rate = budget.max_usd if budget.max_usd is not None else budget.amount_usd
        if rate is None:
            return "none_stated", "No rate stated"
        if profile.min_hourly_usd is None:
            return "no_minimum", f"${rate:,.0f}/hr (no minimum hourly rate set)"
        if rate < profile.min_hourly_usd:
            return "below_minimum", f"${rate:,.0f}/hr vs your ${profile.min_hourly_usd:,.0f}/hr minimum"
        return "pass", f"${rate:,.0f}/hr"
    if k in ("fixed", "fixed_range"):
        # Fixed ranges compare their top end, same as hourly (decision log #10).
        amount = budget.max_usd if k == "fixed_range" else budget.amount_usd
        if amount is None:
            return "none_stated", "No budget stated"
        if amount < floor:
            return "placeholder", f"${amount:,.0f} looks like a placeholder"
        if profile.min_fixed_usd is None:
            return "no_minimum", f"${amount:,.0f} fixed (no minimum fixed price set)"
        if amount < profile.min_fixed_usd:
            return "below_minimum", f"${amount:,.0f} fixed vs your ${profile.min_fixed_usd:,.0f} minimum"
        return "pass", f"${amount:,.0f} fixed"
    return "none_stated", "No budget stated"


def fit_result(a: Assessment, proof: bool, skill_overlap: str = "") -> FitResult:
    yes = sum([a.skills_yes, a.work_type_yes, proof, a.realistic_yes])
    if not a.work_type_yes or yes <= 2:
        band = "Low"
    elif yes == 4:
        band = "High"
    else:
        band = "Medium"
    return FitResult(
        skills=a.skills_yes, work_type=a.work_type_yes, proof=proof, realistic=a.realistic_yes,
        clear=a.clear_yes, band=band, skill_overlap=skill_overlap,
        reasons={"skills": a.skills_reason, "work_type": a.work_type_reason,
                 "realistic": a.realistic_reason, "clear": a.clear_reason},
    )


def pre_decision(trust: TrustResult, gate: str, gate_text: str, red_flag_text: str = "") -> Optional[Decision]:
    """Decision steps 1-2, before any assessment call. None means: run the assessment."""
    if trust.band == "Red flag":
        why = red_flag_text or (trust.reasons[0] if trust.reasons else "the client's history")
        return Decision(decision="skip", code="red_flag", budget_gate=gate,
                        reason=f"Skip: red-flag client. {why[0].upper() + why[1:].rstrip('.')}.")
    if gate == "below_minimum":
        return Decision(decision="skip", code="below_minimum", budget_gate=gate,
                        reason=f"Skip: the budget is below your minimum ({gate_text}).")
    return None


def decide(trust: TrustResult, gate: str, gate_text: str, fit: FitResult) -> Decision:
    """Decision steps 3-4: fit band x trust band, then clarity."""
    cell = TABLE[fit.band][trust.band if trust.band in TABLE["High"] else "Unknown"]
    if cell == "Skip":
        if not fit.work_type:
            reason = f"Skip: this isn't the kind of work you do. {fit.reasons.get('work_type', '')}".strip()
            code = "work_type"
        elif fit.band == "Low":
            missing = [name for name, ok in [("your skills", fit.skills), ("your past projects", fit.proof),
                                             ("a realistic scope for the budget", fit.realistic)] if not ok]
            reason = "Skip: weak fit, missing " + " and ".join(missing) + "."
            code = "low_fit"
        else:
            reason = "Skip: only a partial fit, and the client's history is weak."
            code = "medium_low_trust"
        return Decision(decision="skip", code=code, reason=reason, budget_gate=gate, fit=fit)

    note = cell.split(", ", 1)[1] if ", " in cell else None
    if gate == "placeholder":
        return Decision(decision="apply_with_questions", code="placeholder", budget_gate=gate, fit=fit,
                        card_note=note or "budget looks like a placeholder",
                        reason=f"Apply with questions: {gate_text}, so ask what they'll pay.")
    if not fit.clear:
        return Decision(decision="apply_with_questions", code="unclear", budget_gate=gate, fit=fit, card_note=note,
                        reason="Apply with questions: the post doesn't say enough to plan the work.")
    band_word = {"Excellent": "an excellent", "High": "a strong", "Medium": "a decent",
                 "Low": "a weak", "Unknown": None}[trust.band if trust.band in TABLE["High"] else "Unknown"]
    return Decision(decision="apply", code="apply", budget_gate=gate, fit=fit, card_note=note,
                    reason=(f"Apply: {fit.band.lower()} fit and {band_word} client." if band_word else
                            f"Apply: {fit.band.lower()} fit. The client can't be rated: their details weren't shared."))


def proof_label(j) -> str:
    """similar: same kind of work around the same main platform or the same kind of records.
    same_skills: same kind of work, or the same core skills, otherwise. Facts left blank keep the model's label."""
    facts = (j.same_kind_of_work, j.same_platform, j.same_records, j.shares_core_skills)
    if all(f is None for f in facts):
        return j.label
    if j.same_kind_of_work and (j.same_platform or j.same_records):
        return "similar"
    if j.same_kind_of_work or j.shares_core_skills:
        return "same_skills"
    return "not_relevant"


FIT_FACTS = [("skills_yes", "skills"), ("work_type_yes", "kind of work"), ("realistic_yes", "realistic for the budget"),
             ("clear_yes", "clear enough to plan")]
PROJECT_FACTS = [("same_kind_of_work", "same kind of work"), ("same_platform", "same platform"),
                 ("same_records", "same records"), ("shares_core_skills", "core skills")]


def majority(runs: list):
    """Combines several assessment runs: each yes/no fact takes the majority answer, and its reason comes from
    a run that gave that answer. Facts the runs split on are listed, so the screen can show the confidence."""
    first = runs[0].model_copy(deep=True)
    if len(runs) == 1:
        return first
    split = []
    for field, name in FIT_FACTS:
        vals = [getattr(r, field) for r in runs]
        win = sum(vals) * 2 > len(vals)
        if len(set(vals)) > 1:
            split.append(name)
        setattr(first, field, win)
        reason_field = field.replace("_yes", "_reason")
        setattr(first, reason_field, next(getattr(r, reason_field) for r in runs if getattr(r, field) == win))
    labels = []
    for j in first.project_labels:
        same = [next((l for l in r.project_labels if l.project_id == j.project_id), None) for r in runs]
        same = [l for l in same if l is not None]
        for field, name in PROJECT_FACTS:
            vals = [getattr(l, field) for l in same if getattr(l, field) is not None]
            if not vals:
                continue
            win = sum(vals) * 2 > len(vals)
            if len(set(vals)) > 1:
                split.append(f"{j.project_id} {name}")
            setattr(j, field, win)
        labels.append(j)
    first.project_labels = labels
    first.votes = len(runs)
    first.split_facts = split
    return first
