"""Validators: length, the three-part claim check, allowed instructions, voice and screening answers.

The claim check has three passes:
  1. Numbers: every number in the draft must appear in the chosen project's result or the post.
  2. Names: every tool or skill the draft names must be the user's, the chosen project's,
     or the client's own tool named in the post.
  3. Experience: every sentence that claims past work must map to the chosen project or the profile.
"""
from __future__ import annotations

import re
from typing import Optional

from .config import load_config
from .contracts import ClaimLists, JobPost, Profile, Project, ScreeningAnswer, ValidationReport
from .skills import is_generic, mentioned_in, norm, norm_set

NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?\s?[kK]?(?![\w])%?")
LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.M)
YEARS_CLAIM = re.compile(r"\b\d+\+?\s*(?:years?|yrs)\b[^.]*?\b(?:experience|exp)\b|\b(?:years?) of (?:hands-on )?experience\b", re.I)
VOICE = re.compile(r"\b(our team|our agency|our developers|our engineers|our engineering team|we've built|we have built|we built)\b", re.I)
ATTACHMENT = re.compile(r"(video walkthrough|recorded (?:a|an)\b[^.]{0,30}\bvideo|personali[sz]ed video|see attached|attached (?:is|are)|loom video)", re.I)


def number_values(text: str) -> set[str]:
    """Every number in the text, normalized, including the K-expanded form."""
    values: set[str] = set()
    for m in NUM.finditer(text):
        raw = m.group(0).replace("$", "").replace(",", "").replace("%", "").strip()
        k = raw[-1:].lower() == "k"
        raw = raw.rstrip("kK").strip()
        try:
            v = float(raw)
        except ValueError:
            continue
        values.add(_fmt(v))
        if k:
            values.add(_fmt(v * 1000))
    return values


def _fmt(v: float) -> str:
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0").rstrip(".")


def _draft_numbers(text: str) -> list[tuple[str, str]]:
    """(display, normalized) for numbers in the draft, skipping list markers like '1.'."""
    cleaned = LIST_MARKER.sub(" ", text)
    out = []
    for m in NUM.finditer(cleaned):
        shown = m.group(0).strip()
        vals = number_values(shown)
        if vals:
            out.append((shown, sorted(vals, key=len)[-1]))
    return out


def job_text(job: JobPost) -> str:
    parts = [job.title, job.description, job.budget.raw_text, " ".join(job.screening_questions),
             " ".join(job.skills), " ".join(job.client_tools), job.raw_text]
    return "\n".join(p for p in parts if p)


def project_text(p: Optional[Project]) -> str:
    if not p:
        return ""
    return "\n".join([p.title, p.problem, p.what_i_did, " ".join(p.skills), p.result])


def _sentences_with(text: str, needle: str) -> str:
    for s in re.split(r"(?<=[.!?])\s+|\n+", text):
        if needle.lower() in s.lower():
            return s.strip()
    return needle


def validate(
    text: str,
    screening: list[ScreeningAnswer],
    job: JobPost,
    project: Optional[Project],
    profile: Profile,
    claims: ClaimLists,
    mode: str = "full",
) -> ValidationReport:
    cfg = load_config()["length"]
    full_text = text + "\n" + "\n".join(a.answer for a in screening)
    r = ValidationReport(ok=True)

    # Length: the platform's hard limit in characters.
    limit = cfg.get(f"{job.platform}_chars", cfg["default_chars"])
    r.length_chars = len(text)
    if len(text) > limit:
        r.length_ok = False
        r.notes.append(f"Too long for {job.platform}: {len(text)} characters, the limit is {limit}. Shorten it before sending.")
    target = cfg["questions_first_max_words"] if mode == "questions_first" else cfg["proposal_max_words"]
    words = len(text.split())
    if words > target * 1.5:
        r.notes.append(f"It's {words} words; aim for about {target}.")

    # Pass 1: numbers come only from the chosen project's result or the post.
    allowed_nums = number_values(job_text(job)) | number_values(project.result if project else "")
    allowed_nums |= number_values(" ".join(i.value for i in job.allowed_instructions))
    for shown, value in _draft_numbers(full_text):
        if value not in allowed_nums:
            r.number_failures.append(_sentences_with(full_text, shown))
    for s in sorted(set(r.number_failures)):
        r.notes.append(f"Check this number: \"{s}\". It isn't in your project's result or the post.")

    # Pass 2: names. Tools or skills must be the user's, the chosen project's, or the client's own.
    allowed_names = norm_set(profile.skills) | norm_set(project.skills if project else []) | norm_set(job.skills) | norm_set(job.client_tools)
    jt, pt = job_text(job), project_text(project)
    for name in claims.tools_named:
        if is_generic(name) or norm(name) in allowed_names or mentioned_in(name, jt) or mentioned_in(name, pt):
            continue
        r.name_failures.append(name)
        r.notes.append(f"Check this: the draft mentions {name}, which isn't in your skills, your project or the post.")

    # Pass 3: experience. Every past-work sentence maps to the chosen project or the profile.
    chosen_id = project.id if project else None
    for c in claims.experience_sentences:
        target_id = (c.maps_to or "none").strip()
        ok = (chosen_id is not None and target_id == chosen_id) or target_id == "profile"
        if target_id == "profile":
            # A profile claim can't carry numbers or tools the profile doesn't have.
            nums_bad = [v for _, v in _draft_numbers(c.sentence) if v not in allowed_nums]
            ok = not nums_bad
        if not ok:
            r.experience_failures.append(c.sentence)
    for m in YEARS_CLAIM.finditer(full_text):
        r.experience_failures.append(_sentences_with(full_text, m.group(0)))
    r.experience_failures = list(dict.fromkeys(r.experience_failures))
    for s in r.experience_failures:
        r.notes.append(f"Check this claim: \"{s}\". It doesn't match your chosen project or profile.")

    # Voice and attachments (rubric item 3): the freelancer applies as themselves.
    for m in VOICE.finditer(full_text):
        r.voice_failures.append(_sentences_with(full_text, m.group(0)))
    for m in ATTACHMENT.finditer(full_text):
        r.voice_failures.append(_sentences_with(full_text, m.group(0)))
    r.voice_failures = list(dict.fromkeys(r.voice_failures))
    for s in r.voice_failures:
        r.notes.append(f"Check this: \"{s}\". Write as yourself, and only mention files or videos you've actually added.")

    # Allowed instructions from the post.
    for ins in job.allowed_instructions:
        if ins.check == "starts_with" and ins.value:
            start = re.sub(r"^[\s\"'“‘*_#>-]+", "", text).lower()
            if not start.startswith(ins.value.lower()):
                r.instruction_failures.append(f"Start with \"{ins.value}\"")
                r.notes.append(f"The post asks you to start with \"{ins.value}\". The draft doesn't.")
        elif ins.check == "contains" and ins.value:
            if ins.value.lower() not in full_text.lower():
                r.instruction_failures.append(f"Include \"{ins.value}\"")
                r.notes.append(f"The post asks you to include \"{ins.value}\". The draft doesn't.")
        else:
            r.notes.append(f"Check by hand: the post says \"{ins.text}\".")

    # Screening questions all answered.
    answered = {a.question.strip().lower() for a in screening if a.answer.strip()}
    if len([a for a in screening if a.answer.strip()]) < len(job.screening_questions):
        for q in job.screening_questions:
            if q.strip().lower() not in answered:
                r.screening_failures.append(q)
        if r.screening_failures:
            r.notes.append(f"{len(r.screening_failures)} screening question(s) have no answer yet.")

    r.ok = r.length_ok and not (r.number_failures or r.name_failures or r.experience_failures
                                or r.instruction_failures or r.voice_failures or r.screening_failures)
    r.status = "pass" if r.ok else "needs_review"
    return r


def failures_for_retry(r: ValidationReport) -> list[str]:
    """The failure list sent back to the model on the one retry."""
    items = []
    if not r.length_ok:
        items.append(f"The draft is {r.length_chars} characters; it must be shorter.")
    items += [f"Remove or fix this number, which isn't in the project's result or the post: {s}" for s in r.number_failures]
    items += [f"Don't name {n}: it isn't in the user's skills, the chosen project or the post." for n in r.name_failures]
    items += [f"This past-work claim doesn't match the chosen project or profile; rewrite it: {s}" for s in r.experience_failures]
    items += [f"Write in first person as the freelancer, with no team or video/attachment claims: {s}" for s in r.voice_failures]
    items += [f"Follow the post's instruction: {s}" for s in r.instruction_failures]
    items += [f"Answer this screening question: {q}" for q in r.screening_failures]
    return items
