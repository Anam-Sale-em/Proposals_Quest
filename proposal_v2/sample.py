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
