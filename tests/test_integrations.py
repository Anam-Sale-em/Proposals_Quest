"""Integrations with the network mocked: Freelancer.com adapter and the Google Sheet fallback."""
import pytest

from proposal_v2 import integrations
from proposal_v2.integrations import FetchError, append_sheet_row, fetch_by_link, search_jobs

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


def test_sheet_failure_never_raises(monkeypatch):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_FILE", raising=False)
    ok, msg = append_sheet_row("", ["x"])
    assert not ok and "No Google Sheet" in msg
    ok, msg = append_sheet_row("https://docs.google.com/spreadsheets/d/abc", ["x"])
    assert not ok and "saved here" in msg


def test_app_llm_never_caches_into_the_committed_eval_folder(tmp_path, monkeypatch):
    from proposal_v2.llm import CACHE_DIR, make_llm
    monkeypatch.setenv("PV2_DATA_ROOT", str(tmp_path))
    llm = make_llm("live")
    assert llm.cache_dir == tmp_path / "llm_cache" and CACHE_DIR in llm.read_dirs
    from proposal_v2.contracts import ClaimLists
    llm._write_cache("k1", ClaimLists(), "gemini", "m", "claims")
    assert (tmp_path / "llm_cache" / "k1.json").exists() and not (CACHE_DIR / "k1.json").exists()


def test_sent_log_writes_header_once_then_rows(monkeypatch):
    class WS:
        def __init__(self):
            self.rows = []

        def acell(self, a1):
            return type("C", (), {"value": self.rows[0][0] if self.rows else None})()

        def append_row(self, row, value_input_option=None):
            self.rows.append(row)

    ws = WS()
    client = type("Cl", (), {"open_by_url": lambda self, url: type("Sh", (), {"sheet1": ws})()})()
    monkeypatch.setattr(integrations, "gspread_client", lambda: client)
    for _ in range(2):
        ok, _ = append_sheet_row("https://docs.google.com/spreadsheets/d/x", ["2026-10-22", "Job", 12.5], header=["Date", "Job", "Minutes"])
        assert ok
    assert ws.rows == [["Date", "Job", "Minutes"], ["2026-10-22", "Job", 12.5], ["2026-10-22", "Job", 12.5]]
