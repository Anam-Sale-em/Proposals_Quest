"""Storage behind one interface. Local JSON and Firestore use the same paths:
users/{uid}/proposals/{job_key}, users/{uid}/projects/{id}, users/{uid}/settings/profile,
users/{uid}/settings_log/{ts}. Adding login later doesn't change the data model."""
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
    """Firestore- and filename-safe id for a job key, stable and collision-free."""
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


class FirestoreStorage:
    """Same interface on Firestore (firebase-admin + a service-account). First thing cut if time runs short."""

    def __init__(self):
        import firebase_admin
        from firebase_admin import credentials, firestore

        if not firebase_admin._apps:
            info = secret("FIREBASE_SERVICE_ACCOUNT_JSON")
            path = secret("FIREBASE_SERVICE_ACCOUNT_FILE")
            if info:
                cred = credentials.Certificate(json.loads(info))
            elif path:
                cred = credentials.Certificate(path)
            else:
                raise RuntimeError("Firestore is on, but no FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT_FILE is set.")
            firebase_admin.initialize_app(cred)
        self.db = firestore.client()

    def _u(self, uid):
        return self.db.collection("users").document(uid)

    def get_proposal(self, uid, job_key):
        d = self._u(uid).collection("proposals").document(doc_id(job_key)).get()
        return ProposalRecord.model_validate(d.to_dict()) if d.exists else None

    def put_proposal(self, rec):
        self._u(rec.uid).collection("proposals").document(doc_id(rec.job_key)).set(rec.model_dump(mode="json"))

    def delete_proposal(self, uid, job_key):
        self._u(uid).collection("proposals").document(doc_id(job_key)).delete()

    def list_proposals(self, uid):
        recs = [ProposalRecord.model_validate(d.to_dict()) for d in self._u(uid).collection("proposals").stream()]
        return sorted(recs, key=lambda r: r.created_at, reverse=True)

    def get_projects(self, uid):
        return sorted((Project.model_validate(d.to_dict()) for d in self._u(uid).collection("projects").stream()), key=lambda p: p.id)

    def put_project(self, uid, p):
        self._u(uid).collection("projects").document(p.id).set(p.model_dump(mode="json"))

    def delete_project(self, uid, project_id):
        self._u(uid).collection("projects").document(project_id).delete()

    def get_profile(self, uid):
        d = self._u(uid).collection("settings").document("profile").get()
        return Profile.model_validate(d.to_dict()) if d.exists else None

    def put_profile(self, uid, profile, changed_by="user"):
        old = self.get_profile(uid)
        self._u(uid).collection("settings").document("profile").set(profile.model_dump(mode="json"))
        changes = _diff(old, profile)
        if changes:
            self._u(uid).collection("settings_log").add({"at": now_iso(), "by": changed_by, "changes": json.loads(json.dumps(changes, default=str))})

    def settings_log(self, uid):
        return sorted((d.to_dict() for d in self._u(uid).collection("settings_log").stream()), key=lambda d: d.get("at", ""))

    def clear_user(self, uid):
        for coll in ("proposals", "projects", "settings", "settings_log"):
            for d in self._u(uid).collection(coll).stream():
                d.reference.delete()


def make_storage() -> Storage:
    if load_config()["storage"]["backend"] == "firestore" or secret("STORAGE_BACKEND") == "firestore":
        return FirestoreStorage()
    return JsonStorage()
