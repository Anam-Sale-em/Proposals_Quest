"""Accounts: username + password. Passwords are stored only as a salted PBKDF2-SHA256 hash,
never as plain text. Accounts live in the "Users" tab of the Google Sheet at USERS_SHEET_URL;
until that's set, they're kept in a local file so the app still runs.

Creating an account needs the invite code (APP_PASSPHRASE), so strangers on a public link
can't sign up or spend the Gemini quota. Every record in storage is keyed by the user id, so
duplicate prevention and data are per user."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Protocol

from .config import ROOT, load_config, secret
from .contracts import now_iso

USERNAME = re.compile(r"^[a-z0-9._-]{3,32}$")
MIN_PASSWORD = 8
HEADER = ["user_id", "username", "password_hash", "salt", "iterations", "created_at"]


class AuthError(Exception):
    """Shown to the user as written."""


@dataclass
class UserRecord:
    user_id: str
    username: str
    password_hash: str
    salt: str
    iterations: int
    created_at: str


def _iterations() -> int:
    # 600,000 follows OWASP's guidance for PBKDF2-HMAC-SHA256; tests lower it for speed.
    return int(os.environ.get("PV2_HASH_ITERATIONS", "600000"))


def hash_password(password: str, salt: Optional[str] = None, iterations: Optional[int] = None) -> tuple[str, str, int]:
    salt = salt or secrets.token_hex(16)
    iterations = iterations or _iterations()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations)
    return digest.hex(), salt, iterations


def verify_password(password: str, rec: UserRecord) -> bool:
    digest, _, _ = hash_password(password, rec.salt, int(rec.iterations))
    return hmac.compare_digest(digest, rec.password_hash)


# --------------------------------------------------------------------------- stores
class UserStore(Protocol):
    label: str

    def find(self, username: str) -> Optional[UserRecord]: ...
    def add(self, rec: UserRecord) -> None: ...
    def update(self, rec: UserRecord) -> None: ...


class LocalUserStore:
    """Fallback when USERS_SHEET_URL isn't set: a JSON file in the data folder (gitignored)."""

    label = "a file on this computer (set USERS_SHEET_URL to keep accounts in a Google Sheet)"

    def __init__(self, path: Optional[Path] = None):
        root = Path(secret("PV2_DATA_ROOT") or (ROOT / load_config()["storage"]["json_root"]))
        self.path = Path(path or root / "accounts.json")

    def _all(self) -> list[dict]:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, rows: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, indent=1), encoding="utf-8")

    def find(self, username):
        row = next((r for r in self._all() if r["username"] == username), None)
        return UserRecord(**row) if row else None

    def add(self, rec):
        self._save(self._all() + [asdict(rec)])

    def update(self, rec):
        self._save([asdict(rec) if r["username"] == rec.username else r for r in self._all()])


class SheetUserStore:
    """Accounts in the "Users" tab of a Google Sheet shared with the app's service account."""

    label = "your Google Sheet"

    def __init__(self, url: str, client=None):
        self.url = url
        self._client = client

    def _ws(self):
        try:
            import gspread

            from .integrations import gspread_client

            sh = (self._client or gspread_client()).open_by_url(self.url)
            try:
                ws = sh.worksheet("Users")
            except gspread.WorksheetNotFound:
                ws = sh.add_worksheet(title="Users", rows=200, cols=len(HEADER))
                ws.append_row(HEADER)
            return ws
        except AuthError:
            raise
        except Exception:
            raise AuthError("Couldn't reach the accounts Sheet. Try again in a minute; if it keeps happening, "
                            "check USERS_SHEET_URL and that the Sheet is shared with the service account as an editor.")

    def _rows(self, ws) -> list[dict]:
        values = ws.get_all_values()
        if not values:
            ws.append_row(HEADER)
            return []
        head = values[0]
        return [dict(zip(head, v)) for v in values[1:] if any(v)]

    def find(self, username):
        ws = self._ws()
        row = next((r for r in self._rows(ws) if r.get("username", "").lower() == username), None)
        if not row:
            return None
        return UserRecord(row["user_id"], row["username"], row["password_hash"], row["salt"],
                          int(row["iterations"]), row["created_at"])

    def add(self, rec):
        self._ws().append_row([rec.user_id, rec.username, rec.password_hash, rec.salt, rec.iterations, rec.created_at])

    def update(self, rec):
        ws = self._ws()
        for i, r in enumerate(self._rows(ws), start=2):
            if r.get("username", "").lower() == rec.username:
                ws.update(range_name=f"A{i}:F{i}", values=[[rec.user_id, rec.username, rec.password_hash, rec.salt, rec.iterations, rec.created_at]])
                return
        raise AuthError("No account with that username.")


def make_user_store() -> UserStore:
    url = secret("USERS_SHEET_URL")
    return SheetUserStore(url) if url else LocalUserStore()


# --------------------------------------------------------------------------- actions
def _clean_username(username: str) -> str:
    return (username or "").strip().lower()


def create_account(store: UserStore, username: str, password: str, confirm: str, invite: str) -> UserRecord:
    code = secret("APP_PASSPHRASE") or ""
    if not code or not hmac.compare_digest((invite or "").encode(), code.encode()):
        raise AuthError("That invite code isn't right. Ask the app's owner for it.")
    name = _clean_username(username)
    if not USERNAME.match(name):
        raise AuthError("Usernames are 3–32 characters: letters, numbers, dots, dashes or underscores.")
    if len(password or "") < MIN_PASSWORD:
        raise AuthError(f"Use a password of at least {MIN_PASSWORD} characters.")
    if password != confirm:
        raise AuthError("The two passwords don't match.")
    if store.find(name):
        raise AuthError("That username is taken. Pick another, or sign in.")
    digest, salt, iters = hash_password(password)
    rec = UserRecord(user_id="u_" + secrets.token_hex(5), username=name, password_hash=digest, salt=salt,
                     iterations=iters, created_at=now_iso())
    store.add(rec)
    return rec


def sign_in(store: UserStore, username: str, password: str) -> UserRecord:
    rec = store.find(_clean_username(username))
    # Same message either way, so the form doesn't reveal which usernames exist.
    if not rec or not verify_password(password or "", rec):
        raise AuthError("Wrong username or password.")
    return rec


def reset_password(store: UserStore, username: str, new_password: str) -> UserRecord:
    rec = store.find(_clean_username(username))
    if not rec:
        raise AuthError("No account with that username.")
    if len(new_password) < MIN_PASSWORD:
        raise AuthError(f"Use a password of at least {MIN_PASSWORD} characters.")
    rec.password_hash, rec.salt, rec.iterations = hash_password(new_password)
    store.update(rec)
    return rec
