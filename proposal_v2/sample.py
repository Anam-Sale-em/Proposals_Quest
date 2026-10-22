"""Sample data: the synthetic profile, its three projects and the fixture jobs.
Loads into its own workspace, separate from the user's data."""
from __future__ import annotations

import json

from .config import ROOT
from .contracts import Profile, Project
from .storage import Storage

SAMPLE_UID = "sample"
FIXTURES = ROOT / "fixtures"


def sample_profile() -> tuple[Profile, list[Project]]:
    d = json.loads((FIXTURES / "profile_sample.json").read_text(encoding="utf-8"))
    profile = Profile(work_types=d["work_types"], skills=d["skills"], min_hourly_usd=d["min_hourly_usd"],
                      min_fixed_usd=d["min_fixed_usd"], keywords=["n8n", "automation"])
    projects = [Project(**{k: v for k, v in p.items() if k in Project.model_fields}) for p in d["projects"]]
    return profile, projects


def load_sample(storage: Storage, uid: str = SAMPLE_UID) -> None:
    storage.clear_user(uid)
    profile, projects = sample_profile()
    storage.put_profile(uid, profile, changed_by="sample data")
    for p in projects:
        storage.put_project(uid, p)


def sample_jobs() -> list[dict]:
    """[{id, title, link, job_details}] for the 'Try a sample job' picker (first paste of each case)."""
    out = []
    for f in sorted((FIXTURES / "jobs").glob("T*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        first = d["pastes"][0]
        out.append({"id": d["id"], "title": d["title"], "link": first["link"], "job_details": first["job_details"]})
    return out


# T07 is the whole-page paste test, so it stays in one piece.
WHOLE_PAGE_CASES = {"T07"}


def split_client_box(case_id: str, job_details: str) -> tuple[str, str]:
    """For the form: the post goes in Job details and its "About the client" box in Client history,
    the way a user fills it in. T07 keeps everything in Job details on purpose."""
    i = job_details.find("About the client")
    if case_id in WHOLE_PAGE_CASES or i < 0:
        return job_details, ""
    return job_details[:i].rstrip(), job_details[i:].strip()


# ------------------------------------------------------------------ Freelancer.com tabs, offline
def _freelancer_projects() -> list[dict]:
    return json.loads((FIXTURES / "freelancer_sample.json").read_text(encoding="utf-8"))["projects"]


def sample_fetched_job():
    """The saved sample project for the Freelancer.com link tab, built exactly as a live fetch would be."""
    from .integrations import _to_jobpost

    return _to_jobpost(_freelancer_projects()[0])


def sample_search(keywords: list[str], exclude: list[str], budget_floor):
    """The Freelancer.com search tab on saved sample projects, with the same filters as a live search."""
    from .integrations import FetchError, filter_projects

    if not keywords:
        raise FetchError("Add at least one keyword.")
    return filter_projects(_freelancer_projects(), keywords, exclude, budget_floor)
