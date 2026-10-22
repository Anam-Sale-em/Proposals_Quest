"""End-to-end tests with the scripted LLM: the pipeline, storage, validators, the retry and
the eval runner, all offline. They test the plumbing and the code rules, not model quality."""
from pathlib import Path

import pytest

from proposal_v2.contracts import ClaimLists, ExperienceClaim, JobPost, Profile, Project, ScreeningAnswer
from proposal_v2.evaluation import run_all
from proposal_v2.links import LinkError
from proposal_v2.pipeline import DuplicateJob, Pipeline
from proposal_v2.sample import load_sample, sample_jobs
from proposal_v2.storage import JsonStorage
from proposal_v2.validators import validate
from tests.scripted_llm import ScriptedLLM


@pytest.fixture
def pipe(tmp_path):
    storage = JsonStorage(tmp_path)
    load_sample(storage, "t")
    return Pipeline(storage, ScriptedLLM(), "t")


def _job(cid):
    return next(j for j in sample_jobs() if j["id"] == cid)


def test_t01_end_to_end(pipe):
    j = _job("T01")
    rec = pipe.decide(pipe.extract(j["link"], j["job_details"]))
    assert rec.trust.score == 71 and rec.decision.decision == "apply"
    rec = pipe.write(rec)
    v = rec.latest()
    assert rec.chosen_proof == "P1" and v.validation.ok, v.validation.notes
    assert pipe.steps_called() if hasattr(pipe, "steps_called") else True


def test_duplicate_blocks_before_extraction(pipe):
    j = _job("T12")
    pipe.decide(pipe.extract(j["link"], j["job_details"]))
    calls = len(pipe.llm.calls)
    with pytest.raises(DuplicateJob):
        pipe.check_link("https://www.upwork.com/jobs/~010000000000000012")
    assert len(pipe.llm.calls) == calls


def test_red_flag_skips_without_assessment(pipe):
    j = _job("T10")
    rec = pipe.decide(pipe.extract(j["link"], j["job_details"]))
    assert rec.decision.code == "red_flag" and "WhatsApp" in rec.decision.reason
    assert "assess" not in pipe.llm.steps_called()


def test_override_then_write(pipe):
    j = _job("T08")
    rec = pipe.decide(pipe.extract(j["link"], j["job_details"]))
    assert rec.decision.code == "work_type"
    rec = pipe.override(rec, "I want to try it")
    assert rec.decision.overridden and rec.events[-1]["type"] == "override"


def test_retry_fixes_a_years_claim(pipe):
    j = _job("T11")
    rec = pipe.write(pipe.decide(pipe.extract(j["link"], j["job_details"])))
    v = rec.latest()
    assert v.validation.retried and v.validation.ok
    assert "10 years" not in v.text
    assert rec.job.ignored_instructions and rec.job.refused_instructions


def test_revise_and_mark_sent(pipe):
    j = _job("T01")
    rec = pipe.write(pipe.decide(pipe.extract(j["link"], j["job_details"])))
    rec = pipe.revise(rec, "Say hello instead of hi")
    assert rec.latest().text.startswith("Hello") and len(rec.versions) == 2
    rec, msg = pipe.mark_sent(rec, rec.latest().text + " Thanks!")
    assert rec.status == "sent" and rec.outcome.minutes_paste_to_sent is not None
    assert msg == "Saved as sent."
    csv_text = pipe.sent_log_csv()
    assert csv_text.startswith("Date sent,Job,Link") and rec.job.title in csv_text
    assert pipe.storage.get_proposal("t", rec.job_key).status == "sent"


def test_bad_links_never_reach_the_llm(pipe):
    for url in ["https://example.com/x", "https://www.upwork.com/nx/search/jobs/?q=n8n"]:
        with pytest.raises(LinkError):
            pipe.extract(url, "x" * 100)
    assert pipe.llm.calls == []


def test_validator_catches_names_numbers_voice_and_instructions():
    job = JobPost(job_key="k", platform="upwork", link="l", title="Sync", description="Sync 500 rows to Sheets. Start your proposal with \"hi there\".")
    from proposal_v2.contracts import PostInstruction
    job.allowed_instructions = [PostInstruction(text="start with hi there", kind="format", check="starts_with", value="hi there")]
    p = Project(id="P1", title="Lead intake", skills=["n8n"], result="Saved 2 hours a week")
    text = "Our team has built this. I cut costs by 40% using Salesforce. I have 8 years of experience."
    claims = ClaimLists(tools_named=["Salesforce", "n8n"], experience_sentences=[ExperienceClaim(sentence="Our team has built this.", maps_to="none")])
    r = validate(text, [], job, p, Profile(skills=["n8n"]), claims)
    assert not r.ok and r.status == "needs_review"
    assert r.number_failures and "Salesforce" in r.name_failures and r.experience_failures
    assert r.voice_failures and r.instruction_failures


def test_eval_runner_offline(tmp_path):
    out = run_all(ScriptedLLM(), out_root=tmp_path, progress=lambda s: None)
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "Cases passed: **12 of 12**" in summary, summary
    assert (out / "results.csv").exists() and (out / "drafts" / "T01.md").exists()


def test_skipping_the_fit_check_makes_no_assessment_call(pipe):
    j = _job("T08")  # a logo job the check would Skip
    rec = pipe.decide(pipe.extract(j["link"], j["job_details"]), check=False)
    assert rec.decision.code == "unchecked" and rec.decision.decision == "apply"
    assert "assess" not in pipe.llm.steps_called() and rec.events[-1]["type"] == "fit_check_skipped"


def test_names_check_ignores_generic_words_and_matches_plurals():
    from proposal_v2.skills import is_generic, mentioned_in
    assert mentioned_in("API", "Integrate the app with our existing REST APIs.")
    assert is_generic("API") and is_generic("APIs") and is_generic("UI") and not is_generic("Salesforce")
    job = JobPost(job_key="k", platform="upwork", link="l", title="RN app", description="Integrate with our REST APIs.")
    r = validate("I'll connect the app to your API and REST API.", [], job, None, Profile(), ClaimLists(tools_named=["API", "REST API", "app"]))
    assert not r.name_failures


def test_new_for_me_and_plans_are_not_past_work_claims():
    job = JobPost(job_key="k", platform="upwork", link="l", title="Agent setup", description="Set up agents.")
    honest = "This entire workflow setup is new for me, and here is how I would de-risk it: I will verify API access."
    plan = "I will verify API access credentials and add fallback handling."
    fake = "I've built this exact setup for three clients."
    claims = ClaimLists(experience_sentences=[ExperienceClaim(sentence=s, maps_to="none") for s in (honest, plan, fake)])
    r = validate(" ".join([honest, plan, fake]), [], job, None, Profile(), claims)
    assert r.experience_failures == [fake]
