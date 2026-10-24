"""The v2 path: link check → duplicate check → extraction (LLM) → user confirms →
trust + budget gate (code) → assessment (LLM) → decision (code) → Solution Brief (LLM) →
proposal (LLM) → claim check (LLM lists + code) → one retry → user edits and sends.

Every step that can stop the job raises an error with a plain message for the user.
"""
from __future__ import annotations

import difflib
from datetime import datetime, timezone
from typing import Optional

from . import prompts
from .config import load_config
from .contracts import (Assessment, Brief, ClaimLists, CVImport, Decision, Extraction, JobPost, Profile, Project,
                        ProposalDraft, ProposalRecord, ProposalVersion, now_iso)
from .decision import majority, proof_label, budget_gate, decide, fit_result, pre_decision
from .links import LinkError, ParsedLink, parse_link, title_match
from .llm import LLM
from .policy import apply_policy
from .skills import overlap, overlap_text
from .storage import Storage
from .trust import score_client
from .validators import failures_for_retry, validate


SENT_LOG_HEADER = ["Date sent", "Job", "Link", "v2's call", "You overrode it", "Client trust", "Proof", "Minutes, paste to sent",
                   "Share edited before send", "Outcome"]


def _call(d) -> str:
    """v2's recommendation in words, for the sent log."""
    if d is None:
        return ""
    if d.code == "unchecked":
        return "Fit check skipped"
    return {"apply": "Apply", "apply_with_questions": "Apply with questions", "skip": "Skip"}[d.decision]


def _tags_in_project(tags: list[str], project: Project) -> int:
    """How many of the post's skill tags the project mentions in its own words (title, problem, what was done, skills).
    A vague post like "Automation · API Integration" is matched on what the project was, not on alias lookups."""
    import re

    text = "\n".join([project.title, project.problem, project.what_i_did, " ".join(project.skills)]).lower()
    return sum(1 for t in tags if t.strip() and re.search(r"(?<![a-z0-9])" + re.escape(t.strip().lower()) + r"s?(?![a-z0-9])", text))


def _specific_tags_in_project(job: JobPost, project: Project) -> int:
    """Specific (non-generic) tools named in the post that the project also names."""
    from .skills import is_generic

    tags = [t for t in [*job.skills, *job.client_tools] if t.strip() and not is_generic(t)]
    return _tags_in_project(tags, project)


class PipelineError(Exception):
    """Shown to the user as written."""


class DuplicateJob(PipelineError):
    def __init__(self, record: ProposalRecord):
        super().__init__("You already have a draft for this job.")
        self.record = record


class Pipeline:
    def __init__(self, storage: Storage, llm: LLM, uid: str):
        self.storage, self.llm, self.uid = storage, llm, uid

    # ------------------------------------------------------------------ data
    def profile(self) -> Profile:
        return self.storage.get_profile(self.uid) or Profile()

    def projects(self) -> list[Project]:
        return self.storage.get_projects(self.uid)

    def project(self, project_id: Optional[str]) -> Optional[Project]:
        return next((p for p in self.projects() if p.id == project_id), None) if project_id else None

    # ------------------------------------------------------------------ intake
    def check_link(self, link: str) -> ParsedLink:
        """Step 1 of the link check, then the duplicate check. Runs before any LLM call."""
        parsed = parse_link(link)  # raises LinkError
        existing = self.storage.get_proposal(self.uid, parsed.job_key)
        if existing:
            raise DuplicateJob(existing)
        return parsed

    def extract(self, link: str, job_details: str, client_box: str = "") -> ProposalRecord:
        parsed = self.check_link(link)
        if len((job_details or "").strip()) < 40:
            raise PipelineError("Paste the whole job post into Job details, client box included.")
        system, user = prompts.extraction(parsed.url, parsed.platform, job_details, client_box)
        ex = self.llm.call("extract", "light", system, user, Extraction, load_config()["models"]["temperature_extract"])
        if not ex.title.strip() or not ex.description.strip():
            raise PipelineError("No job title or description was found in the paste. Copy the job's own page and try again.")
        allowed, refused, ignored, flags = apply_policy(ex.instructions, ex.red_flags, ex.description)
        job = JobPost(
            job_key=parsed.job_key, platform=parsed.platform if parsed.platform in
            ("upwork", "freelancer", "guru", "fiverr", "peopleperhour") else "other",
            link=parsed.url, source="paste", title=ex.title, description=ex.description, budget=ex.budget,
            skills=ex.skills, screening_questions=ex.screening_questions, explicit_requirements=ex.explicit_requirements,
            client_tools=ex.client_tools, allowed_instructions=allowed, refused_instructions=refused,
            ignored_instructions=ignored, red_flags=flags, link_status=title_match(parsed, ex.title), raw_text=job_details,
        )
        rec = ProposalRecord(uid=self.uid, job_key=job.job_key, job=job, client=ex.client)
        if ignored:
            rec.events.append({"at": now_iso(), "type": "ignored_ai_instruction", "text": [i.text for i in ignored]})
        if refused:
            rec.events.append({"at": now_iso(), "type": "refused_claim_instruction", "text": [i.text for i in refused]})
        # Keep only sections that really are in the paste: models tend to echo the prompt's examples.
        seen = [sec for sec in ex.ignored_sections if sec.strip() and sec.strip().lower() in job_details.lower()]
        if seen:
            rec.events.append({"at": now_iso(), "type": "ignored_sections", "text": seen})
        return rec

    def from_fetched(self, job: JobPost) -> ProposalRecord:
        """Fetched jobs skip the link check: link and details come from the same API response."""
        existing = self.storage.get_proposal(self.uid, job.job_key)
        if existing:
            raise DuplicateJob(existing)
        return ProposalRecord(uid=self.uid, job_key=job.job_key, job=job)

    # ------------------------------------------------------------------ decide
    def decide(self, rec: ProposalRecord, check: bool = True) -> ProposalRecord:
        """Called once the user confirms the extracted fields. With check=False the user skips the
        fit check: no assessment call and no Skip, but red flags and a low budget still show as warnings."""
        profile = self.profile()
        flags = [f.kind for f in rec.job.red_flags]
        rec.trust = score_client(rec.client, flags, profile.trust_cutoffs or None, rec.job.platform)
        gate, gate_text = budget_gate(rec.job.budget, profile)
        red_text = next((f"the post says \"{f.evidence.strip().rstrip('.!')[:120]}\"" for f in rec.job.red_flags), "")
        if not check:
            warnings = []
            if rec.trust.band == "Red flag":
                warnings.append(f"red-flag client: {red_text or rec.trust.reasons[0]}")
            if gate == "below_minimum":
                warnings.append(f"the budget is below your minimum ({gate_text})")
            rec.decision = Decision(decision="apply", code="unchecked", budget_gate=gate,
                                    reason="Not checked: you chose to write the proposal without the fit check.",
                                    card_note="; ".join(warnings) or None)
            rec.chosen_proof, rec.framing = self.suggested_proof(rec)
            rec.events.append({"at": now_iso(), "type": "fit_check_skipped"})
            rec.status = "decided"
            self.storage.put_proposal(rec)
            return rec
        d = pre_decision(rec.trust, gate, gate_text, red_text)
        if d is None:
            projects = self.projects()
            system, user = prompts.assessment(rec.job, profile, projects)
            m = load_config()["models"]
            runs = [self.llm.call("assess", "light", system, user, Assessment, m["temperature_extract"])]
            for i in range(2, int(m.get("assess_votes", 1)) + 1):
                # Separate runs (distinct prompt tail, so the cache keeps each), then the majority per fact.
                runs.append(self.llm.call("assess", "light", system, user + f"\n\n(Independent check {i}.)",
                                          Assessment, m.get("temperature_vote", 0.3)))
            rec.assessment = majority(runs)
            by_id = {pr.id: pr for pr in projects}
            for j in rec.assessment.project_labels:  # the label comes from the facts, by rule
                j.label = proof_label(j)
                # "Similar" needs evidence in both texts: a specific tool the post names that the project also used.
                # A post that names none (only "Automation", "API Integration") can't be "nearly this".
                if j.label == "similar" and j.project_id in by_id and not _specific_tags_in_project(rec.job, by_id[j.project_id]):
                    j.label = "same_skills"
            if gate in ("placeholder", "none_stated") and not rec.assessment.realistic_yes:
                # The rule, not the model, decides this: a placeholder or missing budget says nothing about scope.
                rec.assessment.realistic_yes = True
                rec.assessment.realistic_reason = "No real budget to judge against (missing or a placeholder), so assumed realistic; ask what they'll pay."
            proof = any(l.label in ("similar", "same_skills") for l in rec.assessment.project_labels
                        if any(p.id == l.project_id for p in projects))
            have = profile.skills + [s for p in projects for s in p.skills]
            fit = fit_result(rec.assessment, proof, overlap_text(rec.job.skills, have))
            d = decide(rec.trust, gate, gate_text, fit)
            rec.chosen_proof, rec.framing = self.suggested_proof(rec)
        rec.decision = d
        rec.status = "skipped" if d.decision == "skip" else "decided"
        self.storage.put_proposal(rec)
        return rec

    def suggested_proof(self, rec: ProposalRecord) -> tuple[Optional[str], str]:
        if not rec.assessment:
            # No assessment (fit check skipped): pick the project with the most skill overlap, and frame it
            # conservatively as same-skills, since nothing has judged it "similar". The user can switch it.
            best, best_n = None, 0
            for p in self.projects():
                n = overlap(rec.job.skills, p.skills)[0]
                if n > best_n:
                    best, best_n = p.id, n
            return (best, "same_skills") if best else (None, "plan_only")
        projects = {p.id: p for p in self.projects()}
        for label in ("similar", "same_skills"):
            cands = [l for l in rec.assessment.project_labels if l.label == label and l.project_id in projects]
            if cands:
                # Ties: the same kind of work first, then platform, records, then skill-tag overlap with the post.
                # Same kind of work first, then how many of the post's own tools the project used, then platform and records.
                best = max(cands, key=lambda l: (bool(l.same_kind_of_work),
                                                 _tags_in_project(rec.job.skills, projects[l.project_id]),
                                                 bool(l.same_platform), bool(l.same_records),
                                                 overlap(rec.job.skills, projects[l.project_id].skills)[0],
                                                 -rec.assessment.project_labels.index(l)))
                return best.project_id, label
        return None, "plan_only"

    def override(self, rec: ProposalRecord, reason: str = "") -> ProposalRecord:
        rec.decision.overridden = True
        rec.decision.override_reason = reason
        rec.events.append({"at": now_iso(), "type": "override", "from": rec.decision.decision, "reason": reason})
        rec.status = "decided"
        if rec.assessment is None:
            # Skipped before the assessment ran (red flag or below minimum): assess now, so proof can be suggested.
            system, user = prompts.assessment(rec.job, self.profile(), self.projects())
            rec.assessment = self.llm.call("assess", "light", system, user, Assessment, 0.0)
            rec.chosen_proof, rec.framing = self.suggested_proof(rec)
        self.storage.put_proposal(rec)
        return rec

    # ------------------------------------------------------------------ write
    def write(self, rec: ProposalRecord, project_id: Optional[str] = "auto", comment: str = "") -> ProposalRecord:
        """Solution Brief, then the proposal, then the claim check with one retry."""
        profile = self.profile()
        if project_id == "auto":
            project_id, framing = rec.chosen_proof, rec.framing or "plan_only"
            if project_id is None and rec.assessment:
                project_id, framing = self.suggested_proof(rec)
        else:
            label = next((l.label for l in (rec.assessment.project_labels if rec.assessment else []) if l.project_id == project_id), None)
            framing = "plan_only" if project_id is None else ("similar" if label == "similar" else "same_skills")
        project = self.project(project_id)
        if project is None:
            project_id, framing = None, "plan_only"
        cfg = load_config()
        temp = cfg["models"]["temperature_draft"]
        system, user = prompts.brief(rec.job, profile, project, framing)
        rec.brief = self.llm.call("brief", "draft", system, user, Brief, temp)
        mode = "questions_first" if rec.decision and rec.decision.decision == "apply_with_questions" else "full"
        max_words = cfg["length"]["questions_first_max_words" if mode == "questions_first" else "proposal_max_words"]

        system, user = prompts.proposal(rec.job, profile, project, framing, rec.brief, mode, max_words)
        draft = self.llm.call("proposal", "draft", system, user, ProposalDraft, temp)
        report = self._check(draft, rec.job, project, profile, mode)
        if not report.ok:
            fails = failures_for_retry(report)
            system, user = prompts.proposal(rec.job, profile, project, framing, rec.brief, mode, max_words, fails, draft.text)
            draft = self.llm.call("proposal_retry", "draft", system, user, ProposalDraft, temp)
            report = self._check(draft, rec.job, project, profile, mode)
            report.retried = True
        rec.chosen_proof, rec.framing = project_id, framing
        rec.versions.append(ProposalVersion(n=len(rec.versions) + 1, framing=framing, project_id=project_id, mode=mode,
                                            text=draft.text, screening_answers=draft.screening_answers,
                                            validation=report, comment=comment))
        rec.status = "drafted"
        self.storage.put_proposal(rec)
        return rec

    def revise(self, rec: ProposalRecord, comment: str, current_text: Optional[str] = None) -> ProposalRecord:
        """Rewrites only what the comment asks, then re-runs the claim check."""
        v = rec.latest()
        if not v:
            raise PipelineError("Write a draft first.")
        profile = self.profile()
        project = self.project(v.project_id)
        system, user = prompts.revise(rec.job, profile, project, current_text or v.text, v.screening_answers, comment)
        draft = self.llm.call("revise", "draft", system, user, ProposalDraft, load_config()["models"]["temperature_draft"])
        report = self._check(draft, rec.job, project, profile, v.mode)
        rec.versions.append(ProposalVersion(n=len(rec.versions) + 1, framing=v.framing, project_id=v.project_id, mode=v.mode,
                                            text=draft.text, screening_answers=draft.screening_answers,
                                            validation=report, comment=comment))
        self.storage.put_proposal(rec)
        return rec

    def _check(self, draft: ProposalDraft, job: JobPost, project: Optional[Project], profile: Profile, mode: str):
        system, user = prompts.claim_lists(draft.text, draft.screening_answers, project, job.user_notes)
        claims = self.llm.call("claims", "light", system, user, ClaimLists, 0.0)
        return validate(draft.text, draft.screening_answers, job, project, profile, claims, mode)

    # ------------------------------------------------------------------ send and outcomes
    def mark_sent(self, rec: ProposalRecord, sent_text: str) -> tuple[ProposalRecord, str]:
        v = rec.latest()
        now = datetime.now(timezone.utc)
        created = datetime.fromisoformat(rec.created_at)
        rec.outcome.sent_at = now.isoformat(timespec="seconds")
        rec.outcome.minutes_paste_to_sent = round((now - created).total_seconds() / 60, 1)
        rec.outcome.ai_draft = v.text if v else ""
        rec.outcome.sent_text = sent_text
        if v:
            rec.outcome.edit_share = round(1 - difflib.SequenceMatcher(None, v.text, sent_text).ratio(), 3)
        rec.status = "sent"
        self.storage.put_proposal(rec)
        return rec, "Saved as sent."

    def sent_log_csv(self) -> str:
        """Every sent proposal as CSV, for the My jobs download (open it in any spreadsheet)."""
        import csv
        import io

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(SENT_LOG_HEADER)
        for r in sorted(self.storage.list_proposals(self.uid), key=lambda r: r.outcome.sent_at or ""):
            if r.status != "sent":
                continue
            o = r.outcome
            w.writerow([(o.sent_at or "")[:10], r.job.title, r.job.link, _call(r.decision),
                        "Yes" if r.decision and r.decision.overridden else "",
                        r.trust.band if r.trust else "", r.framing or "",
                        o.minutes_paste_to_sent, o.edit_share, (o.result or "").replace("_", " ")])
        return buf.getvalue()

    def set_outcome(self, rec: ProposalRecord, result: str) -> ProposalRecord:
        rec.outcome.result = result
        rec.outcome.result_at = now_iso()
        self.storage.put_proposal(rec)
        return rec

    @staticmethod
    def still_waiting(rec: ProposalRecord) -> bool:
        if rec.status != "sent" or rec.outcome.result or not rec.outcome.sent_at:
            return False
        days = (datetime.now(timezone.utc) - datetime.fromisoformat(rec.outcome.sent_at)).days
        return days >= load_config()["outcomes"]["still_waiting_days"]

    # ------------------------------------------------------------------ CV import
    def propose_projects(self, cv_text: str) -> CVImport:
        if len(cv_text.strip()) < 40:
            raise PipelineError("Paste more of your CV or portfolio, or upload a PDF with selectable text.")
        system, user = prompts.cv_import(cv_text)
        return self.llm.call("cv_import", "light", system, user, CVImport, 0.0)


__all__ = ["Pipeline", "PipelineError", "DuplicateJob", "LinkError"]
