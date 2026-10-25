"""Storage behind one interface: local JSON files under data/users/{uid}/ (proposals/, projects/,
settings/profile, settings_log). A database can replace it by implementing the same Storage protocol."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Optional, Protocol

from .config import ROOT, load_config, secret
from .contracts import Profile, Project, ProposalRecord, now_iso


def doc_id(key: str) -> str:
    """Filename-safe id for a job key, stable and collision-free."""
    safe = re.sub(r"[^A-Za-z0-9~_-]", "_", key)[:80]
    return f"{safe}-{hashlib.sha1(key.encode()).hexdigest()[:8]}"


class Storage(Protocol):
    def get_proposal(self, uid: str, job_key: str) -> Optional[ProposalRecord]: ...
    def put_proposal(self, rec: ProposalRecord) -> None: ...
    def list_proposals(self, uid: str) -> list[ProposalRecord]: ...
    def delete_proposal(self, uid: str, job_key: str) -> None: ...
    def get_projects(self, uid: str) -> list[Project]: ...
    def put_project(self, uid: str, p: Project) -> None: ...
    def delete_project(self, uid: str, project_id: str) -> None: ...
    def get_profile(self, uid: str) -> Optional[Profile]: ...
    def put_profile(self, uid: str, profile: Profile, changed_by: str = "user") -> None: ...
    def settings_log(self, uid: str) -> list[dict]: ...
    def clear_user(self, uid: str) -> None: ...


class JsonStorage:
    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or secret("PV2_DATA_ROOT") or (ROOT / load_config()["storage"]["json_root"]))

    def _p(self, *parts: str) -> Path:
        return self.root.joinpath("users", *parts)

    def _read(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def get_proposal(self, uid, job_key):
        d = self._read(self._p(uid, "proposals", doc_id(job_key) + ".json"))
        return ProposalRecord.model_validate(d) if d else None

    def put_proposal(self, rec):
        self._write(self._p(rec.uid, "proposals", doc_id(rec.job_key) + ".json"), rec.model_dump(mode="json"))

    def delete_proposal(self, uid, job_key):
        self._p(uid, "proposals", doc_id(job_key) + ".json").unlink(missing_ok=True)

    def list_proposals(self, uid):
        folder = self._p(uid, "proposals")
        if not folder.exists():
            return []
        recs = [ProposalRecord.model_validate_json(f.read_text(encoding="utf-8")) for f in folder.glob("*.json")]
        return sorted(recs, key=lambda r: r.created_at, reverse=True)

    def get_projects(self, uid):
        folder = self._p(uid, "projects")
        if not folder.exists():
            return []
        return sorted((Project.model_validate_json(f.read_text(encoding="utf-8")) for f in folder.glob("*.json")), key=lambda p: p.id)

    def put_project(self, uid, p):
        self._write(self._p(uid, "projects", re.sub(r"[^A-Za-z0-9_-]", "_", p.id) + ".json"), p.model_dump(mode="json"))

    def delete_project(self, uid, project_id):
        path = self._p(uid, "projects", re.sub(r"[^A-Za-z0-9_-]", "_", project_id) + ".json")
        if path.exists():
            path.unlink()

    def get_profile(self, uid):
        d = self._read(self._p(uid, "settings", "profile.json"))
        return Profile.model_validate(d) if d else None

    def put_profile(self, uid, profile, changed_by="user"):
        old = self.get_profile(uid)
        self._write(self._p(uid, "settings", "profile.json"), profile.model_dump(mode="json"))
        changes = _diff(old, profile)
        if changes:
            log = self._p(uid, "settings_log.jsonl")
            log.parent.mkdir(parents=True, exist_ok=True)
            with open(log, "a", encoding="utf-8") as f:
                f.write(json.dumps({"at": now_iso(), "by": changed_by, "changes": changes}) + "\n")

    def settings_log(self, uid):
        log = self._p(uid, "settings_log.jsonl")
        if not log.exists():
            return []
        return [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]

    def clear_user(self, uid):
        shutil.rmtree(self._p(uid), ignore_errors=True)


def _diff(old: Optional[Profile], new: Profile) -> dict:
    o = old.model_dump() if old else {}
    n = new.model_dump()
    return {k: {"from": o.get(k), "to": v} for k, v in n.items() if o.get(k) != v}


def make_storage() -> Storage:
    return JsonStorage()
