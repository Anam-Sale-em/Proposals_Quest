"""Pydantic contracts. One schema per step, shared by the prompt, the parser and the validator.

LLM output models (suffix-free, used as response schemas) stay flat and simple so every
provider can produce them. App records build on top of them.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- shared pieces
BudgetKind = Literal["hourly", "fixed", "fixed_range", "none"]
InstructionKind = Literal["format", "claim", "off_platform", "ai_directed"]
CheckType = Literal["starts_with", "contains", "answer_question", "other"]
RedFlagKind = Literal["off_platform", "pay_to_apply", "unpaid_test"]
TrustBand = Literal["Excellent", "High", "Medium", "Low", "Red flag", "Unknown"]
FitBand = Literal["High", "Medium", "Low"]
DecisionKind = Literal["apply", "apply_with_questions", "skip"]
ProofLabel = Literal["similar", "same_skills", "not_relevant"]
Framing = Literal["similar", "same_skills", "plan_only"]
LinkStatus = Literal["Matched", "Warned", "Unchecked", "Fetched"]
Platform = Literal["upwork", "freelancer", "guru", "fiverr", "peopleperhour", "other"]


class Budget(BaseModel):
    kind: BudgetKind = "none"
    amount_usd: Optional[float] = None  # fixed price or a single hourly rate
    min_usd: Optional[float] = None  # range low end (hourly or fixed range)
    max_usd: Optional[float] = None  # range top end
    approximate: bool = False  # "$10K+" or "~$500"
    raw_text: str = ""


class ClientProfile(BaseModel):
    payment_verified: Optional[bool] = None
    rating: Optional[float] = None
    reviews: Optional[int] = None
    jobs_posted: Optional[int] = None
    hire_rate_pct: Optional[float] = None
    total_spent_usd: Optional[float] = None
    total_spent_approximate: bool = False
    hires: Optional[int] = None
    active_hires: Optional[int] = None


class PostInstruction(BaseModel):
    text: str  # the instruction as written in the post
    kind: InstructionKind
    check: CheckType = "other"  # how the validator checks a format instruction
    value: str = ""  # e.g. the words a draft must start with


class RedFlag(BaseModel):
    kind: RedFlagKind
    evidence: str


# --------------------------------------------------------------------------- LLM outputs
class Extraction(BaseModel):
    """Step: extraction. Fields pulled from the main posting and its own client box only."""

    title: str
    description: str
    budget: Budget
    skills: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(default_factory=list)
    explicit_requirements: list[str] = Field(default_factory=list)
    client_tools: list[str] = Field(default_factory=list)  # tools the client names as theirs
    client: ClientProfile
    instructions: list[PostInstruction] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    ignored_sections: list[str] = Field(default_factory=list)  # e.g. "Similar jobs", "footer"


class ProjectJudgement(BaseModel):
    """The model answers four facts per project; code turns them into the label (proof_label in decision.py)."""
    project_id: str
    same_kind_of_work: Optional[bool] = None  # same kind of deliverable as the post asks for
    same_platform: Optional[bool] = None  # built around the post's main platform (usually where the data comes from)
    same_records: Optional[bool] = None  # handled the same kind of records (orders, contacts, leads, inventory...)
    shares_core_skills: Optional[bool] = None  # uses the core skills the post needs
    label: ProofLabel = "not_relevant"
    reason: str = ""


class Assessment(BaseModel):
    """Step: assessment. Three of the four fit questions, clarity, and proof labels."""

    skills_yes: bool
    skills_reason: str
    work_type_yes: bool
    work_type_reason: str
    realistic_yes: bool
    realistic_reason: str
    clear_yes: bool  # could a 3-step plan be written from the post alone?
    clear_reason: str
    project_labels: list[ProjectJudgement] = Field(default_factory=list)
    votes: int = 1  # how many times the check ran (majority vote)
    split_facts: list[str] = Field(default_factory=list)  # facts the runs didn't all agree on


class PlanStep(BaseModel):
    step: str
    tools: list[str] = Field(default_factory=list)
    suggested_tools: list[str] = Field(default_factory=list)  # tools the client didn't name


class Milestone(BaseModel):
    name: str
    deliverable: str
    budget_share: str = ""


class ProofMapping(BaseModel):
    step: str
    project_id: Optional[str] = None
    gap: bool = False  # no proof for this step


class Risk(BaseModel):
    risk: str
    mitigation: str


class Brief(BaseModel):
    """Step: Solution Brief. Plans this exact job from real proof."""

    goal: str
    plan: list[PlanStep]
    milestones: list[Milestone]
    proof_map: list[ProofMapping]
    risks: list[Risk]
    questions: list[str]
    assumptions: list[str]


class ScreeningAnswer(BaseModel):
    question: str
    answer: str


class ProposalDraft(BaseModel):
    """Step: proposal (or revision)."""

    text: str
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)


class ExperienceClaim(BaseModel):
    sentence: str
    maps_to: str  # a project id, "profile" or "none"


class ClaimLists(BaseModel):
    """Step: claim lists for the names and experience passes of the claim check."""

    tools_named: list[str] = Field(default_factory=list)
    experience_sentences: list[ExperienceClaim] = Field(default_factory=list)


class ProposedProject(BaseModel):
    title: str
    problem: str = ""
    what_i_did: str = ""
    skills: list[str] = Field(default_factory=list)
    result: str = ""
    link: Optional[str] = None
    role: Literal["solo", "led", "contributed"] = "solo"


class CVImport(BaseModel):
    projects: list[ProposedProject] = Field(default_factory=list)


class RubricItem(BaseModel):
    item: int
    passed: bool
    reason: str


class JudgeScore(BaseModel):
    items: list[RubricItem]


# --------------------------------------------------------------------------- app records
class Project(BaseModel):
    id: str
    title: str
    problem: str = ""
    what_i_did: str = ""
    skills: list[str] = Field(default_factory=list)
    result: str = ""  # verifiable numbers only
    link: Optional[str] = None
    role: Literal["solo", "led", "contributed"] = "solo"
    can_name_client: bool = False


class Profile(BaseModel):
    """Settings plus the parts of the profile the prompts read."""

    work_types: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    min_hourly_usd: Optional[float] = None
    min_fixed_usd: Optional[float] = None
    trust_cutoffs: dict[str, float] = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    exclude_terms: list[str] = Field(default_factory=list)
    budget_floor_usd: Optional[float] = None


class JobPost(BaseModel):
    job_key: str
    platform: Platform
    link: str
    source: Literal["paste", "fetch"] = "paste"
    title: str
    description: str
    budget: Budget = Field(default_factory=Budget)
    skills: list[str] = Field(default_factory=list)
    screening_questions: list[str] = Field(default_factory=list)
    user_notes: str = ""  # what the freelancer wants in the proposal, in their own words
    explicit_requirements: list[str] = Field(default_factory=list)
    client_tools: list[str] = Field(default_factory=list)
    allowed_instructions: list[PostInstruction] = Field(default_factory=list)
    refused_instructions: list[PostInstruction] = Field(default_factory=list)
    ignored_instructions: list[PostInstruction] = Field(default_factory=list)
    red_flags: list[RedFlag] = Field(default_factory=list)
    link_status: LinkStatus = "Unchecked"
    raw_text: str = ""


class TrustResult(BaseModel):
    score: Optional[int]
    band: TrustBand
    coverage: str
    reasons: list[str] = Field(default_factory=list)  # every point, biggest first


class FitResult(BaseModel):
    skills: bool
    work_type: bool
    proof: bool
    realistic: bool
    clear: bool
    band: FitBand
    reasons: dict[str, str] = Field(default_factory=dict)
    skill_overlap: str = ""


class Decision(BaseModel):
    decision: DecisionKind
    reason: str  # one plain-English reason for the card
    code: str  # machine reason: red_flag, below_minimum, work_type, low_fit, medium_low_trust, apply, unclear, placeholder
    card_note: Optional[str] = None  # "low-trust warning", "check client manually", "budget looks like a placeholder"
    budget_gate: str = "pass"
    fit: Optional[FitResult] = None
    overridden: bool = False
    override_reason: str = ""


class ValidationReport(BaseModel):
    ok: bool
    status: Literal["pass", "needs_review"] = "pass"
    length_ok: bool = True
    length_chars: int = 0
    number_failures: list[str] = Field(default_factory=list)
    name_failures: list[str] = Field(default_factory=list)
    experience_failures: list[str] = Field(default_factory=list)
    instruction_failures: list[str] = Field(default_factory=list)
    voice_failures: list[str] = Field(default_factory=list)
    screening_failures: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)  # plain words for the draft screen
    retried: bool = False


class ProposalVersion(BaseModel):
    n: int
    created_at: str = Field(default_factory=now_iso)
    framing: Framing
    project_id: Optional[str] = None
    mode: Literal["full", "questions_first"] = "full"
    text: str
    screening_answers: list[ScreeningAnswer] = Field(default_factory=list)
    validation: ValidationReport
    comment: str = ""  # the revise comment that produced it, if any


class Outcome(BaseModel):
    sent_at: Optional[str] = None
    minutes_paste_to_sent: Optional[float] = None
    ai_draft: str = ""
    sent_text: str = ""
    edit_share: Optional[float] = None  # 0 = sent as drafted, 1 = fully rewritten
    result: Optional[Literal["replied", "interview", "hired", "no_reply"]] = None
    result_at: Optional[str] = None


class ProposalRecord(BaseModel):
    """users/{uid}/proposals/{job_key}"""

    uid: str
    job_key: str
    created_at: str = Field(default_factory=now_iso)
    status: Literal["extracted", "decided", "drafted", "sent", "skipped"] = "extracted"
    job: JobPost
    client: ClientProfile = Field(default_factory=ClientProfile)
    trust: Optional[TrustResult] = None
    assessment: Optional[Assessment] = None
    decision: Optional[Decision] = None
    brief: Optional[Brief] = None
    chosen_proof: Optional[str] = None  # project id, or None for plan only
    framing: Optional[Framing] = None
    versions: list[ProposalVersion] = Field(default_factory=list)
    outcome: Outcome = Field(default_factory=Outcome)
    events: list[dict] = Field(default_factory=list)  # overrides, regenerations, link warnings

    def latest(self) -> Optional[ProposalVersion]:
        return self.versions[-1] if self.versions else None
