"""Client trust score: 0-100 from hiring and payment history, plus red flags from the post.

The LLM extracts the numbers and spots red flags; this module does all the scoring.
Every point is returned as a reason, so the Details expander can show the top three.
"""
from __future__ import annotations

from typing import Iterable, Optional

from .config import load_config
from .contracts import ClientProfile, TrustResult

COVERAGE_FIELDS = ["payment_verified", "rating", "jobs_posted", "hire_rate_pct", "total_spent_usd", "hires"]
FLAG_TEXT = {
    "off_platform": "the post asks to move chat or payment off the platform",
    "pay_to_apply": "the post asks you to pay something",
    "unpaid_test": "the post asks for an unpaid test that looks like real work",
}


def band_for(score: int, cutoffs: Optional[dict] = None) -> str:
    c = dict(load_config()["trust"])
    if cutoffs:
        c.update({k: v for k, v in cutoffs.items() if v is not None})
    if score >= c["excellent"]:
        return "Excellent"
    if score >= c["high"]:
        return "High"
    if score >= c["medium"]:
        return "Medium"
    if score >= c["low"]:
        return "Low"
    return "Red flag"


def _money(x: float) -> str:
    return f"${x:,.0f}"


def score_client(client: ClientProfile, post_flags: Iterable[str] = (), cutoffs: Optional[dict] = None) -> TrustResult:
    flags = set(post_flags)
    covered = sum(1 for f in COVERAGE_FIELDS if getattr(client, f) is not None)
    coverage = f"{covered} of 6 fields"
    if client.hires is None or client.total_spent_usd is None:
        reasons = ["Hires or total spend isn't shown, so the client's history can't be scored"]
        reasons += [f"Red flag: {FLAG_TEXT[f]}" for f in sorted(flags) if f in FLAG_TEXT]
        if "off_platform" in flags or "pay_to_apply" in flags:
            return TrustResult(score=5 if "pay_to_apply" in flags else 15, band="Red flag", coverage=coverage, reasons=reasons)
        return TrustResult(score=None, band="Unknown", coverage=coverage, reasons=reasons)

    hires, spent = client.hires, client.total_spent_usd
    active = client.active_hires or 0
    reasons: list[tuple[int, str]] = []
    caps: list[int] = []
    history_flag = False

    # Step 1: base score, highest row where hires and spend both hold
    if hires >= 1 and spent == 0:
        if active == 0:
            base, history_flag = 15, True
            caps.append(15)
            reasons.append((15, f"{hires} hire(s) but $0 spent and nothing active (red flag)"))
        else:
            base = 25
            reasons.append((25, f"{hires} hire(s), $0 spent so far, a contract still active"))
    elif hires == 0:
        base = 25
        reasons.append((25, "No hires yet"))
    else:
        base, label = 40, "1+ hire with money spent"
        if hires >= 3 and spent >= 500:
            base, label = 48, "3+ hires and $500+ spent"
        if hires >= 5 and spent >= 2500:
            base, label = 56, "5+ hires and $2,500+ spent"
        if hires >= 10 and spent >= 10000:
            base, label = 64, "10+ hires and $10,000+ spent"
        reasons.append((base, f"{label} ({hires} hires, {_money(spent)})"))
    score = base

    # Step 2: modifiers (no points for account tenure)
    pv = client.payment_verified
    if pv is True:
        score += 10
        reasons.append((10, "Payment verified"))
    elif pv is False:
        score -= 5
        caps.append(39)
        reasons.append((-5, "Payment not verified (score can't go above 39)"))
    reviews = client.reviews or 0
    if client.rating is not None and reviews >= 3:
        r = client.rating
        if r >= 4.8:
            score += 10
            reasons.append((10, f"Rated {r} from {reviews} reviews"))
        elif r >= 4.5:
            score += 5
            reasons.append((5, f"Rated {r} from {reviews} reviews"))
        elif r < 4.0:
            score -= 25
            reasons.append((-25, f"Low rating: {r} from {reviews} reviews"))
    jp = client.jobs_posted or 0
    hr = client.hire_rate_pct
    if hr is not None and jp >= 5:
        if hr >= 70:
            score += 5
            reasons.append((5, f"Hires on {hr:.0f}% of {jp} jobs"))
        elif 25 <= hr <= 39:
            score -= 5
            reasons.append((-5, f"Hires on only {hr:.0f}% of {jp} jobs"))
        elif hr < 25:
            score -= 10
            reasons.append((-10, f"Hires on only {hr:.0f}% of {jp} jobs"))
    if hires >= 3:
        per_hire = spent / hires
        if per_hire >= 1000:
            score += 5
            reasons.append((5, f"{_money(per_hire)} spent per hire"))
        elif per_hire < 100:
            score -= 15
            reasons.append((-15, f"Only {_money(per_hire)} spent per hire"))

    # Step 3: red flags in the post
    if "off_platform" in flags:
        caps.append(15)
        reasons.append((-100, f"Red flag: {FLAG_TEXT['off_platform']} (capped at 15)"))
    if "pay_to_apply" in flags:
        caps.append(5)
        reasons.append((-100, f"Red flag: {FLAG_TEXT['pay_to_apply']} (capped at 5)"))
    if "unpaid_test" in flags:
        score -= 15
        reasons.append((-15, f"Red flag: {FLAG_TEXT['unpaid_test']}"))

    excellent_ok = (
        hires >= 10 and spent >= 10000 and pv is True
        and client.rating is not None and client.rating >= 4.7 and reviews >= 5
        and hr is not None and hr >= 60 and not flags and not history_flag
    )
    if not excellent_ok:
        caps.append(79)

    score = max(0, min(100, score))
    if caps:
        score = min(score, min(caps))
    band = band_for(score, cutoffs)
    ordered = [text for _, text in sorted(reasons, key=lambda r: -abs(r[0]))]
    return TrustResult(score=score, band=band, coverage=coverage, reasons=ordered)
