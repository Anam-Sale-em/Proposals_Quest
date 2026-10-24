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


def score_freelancer(client: ClientProfile, flags: set, cutoffs: Optional[dict] = None) -> TrustResult:
    """Freelancer.com shows no hires or spend, only reviews, a star rating and payment verified.
    Each employer review is a finished project, so the review count stands in for hires."""
    shown = [client.rating, client.reviews, client.payment_verified]
    coverage = f"{sum(1 for f in shown if f is not None)} of 3 fields"
    if client.reviews is None and client.rating is None:
        reasons = ["Reviews and rating aren't filled in, so the client can't be scored"]
        reasons += [f"Red flag: {FLAG_TEXT[f]}" for f in sorted(flags) if f in FLAG_TEXT]
        if "off_platform" in flags or "pay_to_apply" in flags:
            return TrustResult(score=5 if "pay_to_apply" in flags else 15, band="Red flag", coverage=coverage, reasons=reasons)
        return TrustResult(score=None, band="Unknown", coverage=coverage, reasons=reasons)

    reviews = client.reviews or 0
    reasons: list[tuple[int, str]] = []
    caps = [79]  # Freelancer.com shows too little for Excellent
    if reviews == 0:
        base, label = 25, "No reviews yet"
    else:
        base, label = 40, f"{reviews} review(s)"
        for n, b in ((3, 48), (10, 56), (25, 64)):
            if reviews >= n:
                base, label = b, f"{n}+ reviews ({reviews})"
    reasons.append((base, label))
    score = base

    r = client.rating
    if r is not None and reviews >= 1:
        if reviews >= 3 and r >= 4.8:
            score += 10
            reasons.append((10, f"Rated {r} from {reviews} reviews"))
        elif reviews >= 3 and r >= 4.5:
            score += 5
            reasons.append((5, f"Rated {r} from {reviews} reviews"))
        elif r < 4.0:
            cut = 25 if reviews >= 3 else 10
            score -= cut
            reasons.append((-cut, f"Low rating: {r} from {reviews} reviews"))

    pv = client.payment_verified
    if pv is True:
        score += 10
        reasons.append((10, "Payment verified"))
    elif pv is False:
        score -= 5
        caps.append(39)
        reasons.append((-5, "Payment not verified (score can't go above 39)"))

    score, caps = _post_flags(score, caps, reasons, flags)
    score = min(max(0, min(100, score)), min(caps))
    ordered = [text for _, text in sorted(reasons, key=lambda x: -abs(x[0]))]
    return TrustResult(score=score, band=band_for(score, cutoffs), coverage=coverage, reasons=ordered)


def _post_flags(score: int, caps: list, reasons: list, flags: set) -> tuple[int, list]:
    if "off_platform" in flags:
        caps.append(15)
        reasons.append((-100, f"Red flag: {FLAG_TEXT['off_platform']} (capped at 15)"))
    if "pay_to_apply" in flags:
        caps.append(5)
        reasons.append((-100, f"Red flag: {FLAG_TEXT['pay_to_apply']} (capped at 5)"))
    if "unpaid_test" in flags:
        score -= 15
        reasons.append((-15, f"Red flag: {FLAG_TEXT['unpaid_test']}"))
    return score, caps


def score_guru(client: ClientProfile, flags: set, cutoffs: Optional[dict] = None) -> TrustResult:
    """Guru's "Posted By" box: feedback %, total spend, jobs posted, jobs paid, paid invoices %, outstanding invoices.
    Jobs paid stand in for hires (a job the client actually paid for); paid invoices stand in for payment verified."""
    shown = [client.feedback_pct, client.total_spent_usd, client.jobs_posted, client.jobs_paid,
             client.paid_invoices_pct, client.outstanding_invoices]
    coverage = f"{sum(1 for f in shown if f is not None)} of 6 fields"
    if client.jobs_paid is None or client.total_spent_usd is None:
        reasons = ["Jobs paid or total spend isn't filled in, so the client's history can't be scored"]
        reasons += [f"Red flag: {FLAG_TEXT[f]}" for f in sorted(flags) if f in FLAG_TEXT]
        if "off_platform" in flags or "pay_to_apply" in flags:
            return TrustResult(score=5 if "pay_to_apply" in flags else 15, band="Red flag", coverage=coverage, reasons=reasons)
        return TrustResult(score=None, band="Unknown", coverage=coverage, reasons=reasons)

    paid, spent = client.jobs_paid, client.total_spent_usd
    reasons: list[tuple[int, str]] = []
    caps = [79]  # Guru shows too little for Excellent
    if paid == 0:
        base, label = 25, "No paid jobs yet"
    elif spent == 0:
        base, label = 15, f"{paid} paid job(s) but $0 spent (red flag)"
        caps.append(15)
    else:
        base, label = 40, f"{paid} paid job(s), {_money(spent)} spent"
        for n, m, b, lab in ((3, 500, 48, "3+ paid jobs and $500+ spent"), (5, 2500, 56, "5+ paid jobs and $2,500+ spent"),
                             (10, 10000, 64, "10+ paid jobs and $10,000+ spent")):
            if paid >= n and spent >= m:
                base, label = b, f"{lab} ({paid} jobs, {_money(spent)})"
    reasons.append((base, label))
    score = base

    fb = client.feedback_pct
    if fb is not None and paid >= 3:
        if fb >= 98:
            score += 10
            reasons.append((10, f"{fb:.0f}% feedback over {paid} paid jobs"))
        elif fb >= 90:
            score += 5
            reasons.append((5, f"{fb:.0f}% feedback over {paid} paid jobs"))
        elif fb < 80:
            score -= 25
            reasons.append((-25, f"Low feedback: {fb:.0f}%"))
    pi = client.paid_invoices_pct
    if pi is not None and paid >= 1:
        if pi >= 100:
            score += 10
            reasons.append((10, "Pays every invoice (100% paid)"))
        elif pi < 90:
            score -= 10
            reasons.append((-10, f"Only {pi:.0f}% of invoices paid"))
    if client.outstanding_invoices:
        score -= 5
        reasons.append((-5, f"{client.outstanding_invoices} outstanding invoice(s)"))
    jp = client.jobs_posted or 0
    if jp >= 5:
        hr = 100 * paid / jp
        if hr >= 70:
            score += 5
            reasons.append((5, f"Paid on {hr:.0f}% of {jp} jobs posted"))
        elif hr < 25:
            score -= 10
            reasons.append((-10, f"Paid on only {hr:.0f}% of {jp} jobs posted"))
        elif hr < 40:
            score -= 5
            reasons.append((-5, f"Paid on only {hr:.0f}% of {jp} jobs posted"))

    score, caps = _post_flags(score, caps, reasons, flags)
    score = min(max(0, min(100, score)), min(caps))
    ordered = [text for _, text in sorted(reasons, key=lambda x: -abs(x[0]))]
    return TrustResult(score=score, band=band_for(score, cutoffs), coverage=coverage, reasons=ordered)


def score_client(client: ClientProfile, post_flags: Iterable[str] = (), cutoffs: Optional[dict] = None,
                 platform: str = "") -> TrustResult:
    flags = set(post_flags)
    if platform == "freelancer":
        return score_freelancer(client, flags, cutoffs)
    if platform == "guru":
        return score_guru(client, flags, cutoffs)
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
    score, caps = _post_flags(score, caps, reasons, flags)

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
