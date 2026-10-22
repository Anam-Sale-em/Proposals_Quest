"""Integrations with the network mocked: the Freelancer.com adapter and the LLM fallbacks."""
import pytest

from proposal_v2 import integrations
from proposal_v2.integrations import FetchError, fetch_by_link, search_jobs

PROJECT = {"id": 39811234, "title": "Python script for Shopify orders", "seo_url": "python/python-script-shopify-orders",
           "description": "Pull orders daily into Google Sheets.", "type": "fixed", "budget": {"minimum": 250, "maximum": 750},
           "currency": {"code": "USD"}, "jobs": [{"name": "Python"}, {"name": "Shopify"}], "status": "active", "time_submitted": 2}


class Resp:
    def __init__(self, code, data):
        self.status_code, self._d = code, data

    def json(self):
        return self._d


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    monkeypatch.setattr(integrations, "_last_call", [0.0])
    monkeypatch.setattr(integrations.time, "sleep", lambda s: None)


def test_fetch_by_link_normalizes_into_jobpost(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", lambda url, params, timeout: Resp(200, {"status": "success", "result": {"projects": [PROJECT]}}))
    job = fetch_by_link("https://www.freelancer.com/projects/python/python-script-shopify-orders")
    assert job.job_key == "freelancer:39811234" and job.source == "fetch" and job.link_status == "Fetched"
    assert job.budget.kind == "fixed_range" and job.budget.max_usd == 750 and job.skills == ["Python", "Shopify"]


def test_closed_job_and_errors(monkeypatch):
    import requests
    closed = dict(PROJECT, status="closed", frontend_project_status="complete")
    monkeypatch.setattr(requests, "get", lambda url, params, timeout: Resp(200, {"status": "success", "result": {"projects": [closed]}}))
    with pytest.raises(FetchError, match="closed"):
        fetch_by_link("https://www.freelancer.com/projects/python/python-script-shopify-orders")
    monkeypatch.setattr(requests, "get", lambda url, params, timeout: Resp(429, {}))
    with pytest.raises(FetchError, match="rate-limiting"):
        search_jobs(["shopify"], [], None)
    with pytest.raises(FetchError, match="only fetch Freelancer.com"):
        fetch_by_link("https://www.upwork.com/jobs/~01abc")


def test_search_filters_excludes_and_floor(monkeypatch):
    import requests
    cheap = dict(PROJECT, id=2, title="Cheap job", budget={"minimum": 10, "maximum": 30}, time_submitted=3)
    wp = dict(PROJECT, id=3, title="WordPress fix", time_submitted=1)
    monkeypatch.setattr(requests, "get", lambda url, params, timeout: Resp(200, {"status": "success", "result": {"projects": [PROJECT, cheap, wp]}}))
    jobs = search_jobs(["python"], ["wordpress"], 100)
    assert [j.title for j in jobs] == ["Python script for Shopify orders"]


def test_app_llm_never_caches_into_the_committed_eval_folder(tmp_path, monkeypatch):
    from proposal_v2.llm import CACHE_DIR, make_llm
    monkeypatch.setenv("PV2_DATA_ROOT", str(tmp_path))
    llm = make_llm("live")
    assert llm.cache_dir == tmp_path / "llm_cache" and CACHE_DIR in llm.read_dirs
    from proposal_v2.contracts import ClaimLists
    llm._write_cache("k1", ClaimLists(), "gemini", "m", "claims")
    assert (tmp_path / "llm_cache" / "k1.json").exists() and not (CACHE_DIR / "k1.json").exists()


def test_busy_gemini_retries_then_falls_back_through_the_model_list(monkeypatch, tmp_path):
    """Gemini 503 is retried, then the other Gemini model, then Groq models in order; a missing Groq model is skipped."""
    from proposal_v2 import llm as llm_mod
    from proposal_v2.contracts import ClaimLists
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: None)
    monkeypatch.setattr(llm_mod.LLM, "_throttle", lambda self, m: None)
    tried = []

    def gemini(self, model, *a):
        tried.append(model)
        raise llm_mod._Unavailable("gemini 503: high demand", retryable=True)

    def groq(self, model, *a):
        tried.append(model)
        if model == "openai/gpt-oss-120b":  # e.g. not available to this key
            raise llm_mod._Unavailable("groq: 404 model does not exist")
        return '{"tools_named": ["n8n"], "experience_sentences": []}', 10, 5

    monkeypatch.setattr(llm_mod.LLM, "_gemini", gemini)
    monkeypatch.setattr(llm_mod.LLM, "_groq", groq)
    llm = llm_mod.LLM(mode="live", cache_dir=tmp_path, log_dir=None)
    out = llm.call("claims", "light", "s", "u", ClaimLists)
    assert out.tools_named == ["n8n"]
    assert tried == ["gemini-3.5-flash-lite"] * 3 + ["gemini-3.8-flash"] * 2 + ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]


def test_all_models_busy_gives_a_plain_message(monkeypatch, tmp_path):
    from proposal_v2 import llm as llm_mod
    from proposal_v2.contracts import ClaimLists
    monkeypatch.setattr(llm_mod.time, "sleep", lambda s: None)
    monkeypatch.setattr(llm_mod.LLM, "_throttle", lambda self, m: None)
    busy = lambda self, model, *a: (_ for _ in ()).throw(llm_mod._Unavailable("gemini 503: high demand", retryable=True))  # noqa: E731
    monkeypatch.setattr(llm_mod.LLM, "_gemini", busy)
    monkeypatch.setattr(llm_mod.LLM, "_groq", busy)
    with pytest.raises(llm_mod.LLMError, match="busy right now"):
        llm_mod.LLM(mode="live", cache_dir=tmp_path, log_dir=None).call("claims", "light", "s", "u", ClaimLists)


def test_search_keeps_only_whole_phrase_matches_and_converts_currency(monkeypatch):
    import requests
    turkish = dict(PROJECT, id=4, title="Native Turkish Translation Audit", description="Review translations.",
                   jobs=[{"name": "Translation"}], time_submitted=5)
    weather = dict(PROJECT, id=5, title="Luxury Expo Weather App", description="Build a weather app.",
                   jobs=[{"name": "React Native"}, {"name": "Expo"}], time_submitted=4)
    inr = dict(PROJECT, id=6, title="Delivery app in React Native", description="Two screens.", jobs=[],
               currency={"code": "INR", "exchange_rate": 0.01}, budget={"minimum": 12500, "maximum": 37500}, time_submitted=3)
    monkeypatch.setattr(requests, "get", lambda url, params, timeout: Resp(200, {"status": "success", "result": {"projects": [turkish, weather, inr]}}))
    jobs = search_jobs(["React Native"], [], 300)
    assert [j.title for j in jobs] == ["Luxury Expo Weather App", "Delivery app in React Native"]
    j = jobs[1]
    assert j.budget.kind == "fixed_range" and j.budget.max_usd == 375 and "about $125 – 375" in j.budget.raw_text
    assert [x.title for x in search_jobs(["React Native"], [], 400)] == ["Luxury Expo Weather App"]  # $375 top is under the floor


def test_match_places_says_where_the_keyword_is():
    from proposal_v2.contracts import JobPost
    from proposal_v2.integrations import match_places
    j = JobPost(job_key="k", platform="freelancer", link="l", title="SaaS build",
                description="Workflows run on n8n.", skills=["PHP", "Supabase"])
    assert match_places(j, ["n8n", "Flutter"]) == [("n8n", "description")]


def test_sample_freelancer_tabs_work_offline():
    from proposal_v2.sample import sample_fetched_job, sample_search
    job = sample_fetched_job()
    assert job.job_key == "freelancer:90000001" and job.budget.max_usd == 750 and "n8n" in job.skills
    titles = [j.title for j in sample_search(["n8n", "automation"], [], 300)]
    assert titles == ["n8n workflow to sync Airtable leads into HubSpot", "Move 6 Zapier zaps to n8n"]  # INR job under the floor, logo job no match
    assert len(sample_search(["n8n", "automation"], [], None)) == 3
