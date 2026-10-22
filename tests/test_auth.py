"""Accounts: hashing, invite code, validation, generic sign-in errors, reset, and the Sheet store
with gspread mocked."""
import pytest

from proposal_v2 import auth
from proposal_v2.auth import (AuthError, LocalUserStore, SheetUserStore, create_account, hash_password,
                              reset_password, sign_in, verify_password)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setenv("PV2_HASH_ITERATIONS", "1000")
    monkeypatch.setenv("APP_PASSPHRASE", "invite-1")


def test_hash_is_salted_and_verifies():
    a, salt_a, _ = hash_password("secret-pass")
    b, salt_b, _ = hash_password("secret-pass")
    assert a != b and salt_a != salt_b
    rec = auth.UserRecord("u_1", "x", a, salt_a, 1000, "")
    assert verify_password("secret-pass", rec) and not verify_password("wrong-pass", rec)


def test_create_and_sign_in(tmp_path):
    store = LocalUserStore(tmp_path / "a.json")
    rec = create_account(store, "  Anam_S ", "long-enough", "long-enough", "invite-1")
    assert rec.username == "anam_s" and rec.user_id.startswith("u_")
    assert sign_in(store, "ANAM_S", "long-enough").user_id == rec.user_id
    assert "long-enough" not in (tmp_path / "a.json").read_text()


@pytest.mark.parametrize("user,pw,confirm,invite,msg", [
    ("anam", "long-enough", "long-enough", "bad", "invite code"),
    ("a", "long-enough", "long-enough", "invite-1", "3–32 characters"),
    ("bad name!", "long-enough", "long-enough", "invite-1", "3–32 characters"),
    ("anam", "short", "short", "invite-1", "at least 8"),
    ("anam", "long-enough", "different!", "invite-1", "don't match"),
])
def test_create_account_validation(tmp_path, user, pw, confirm, invite, msg):
    with pytest.raises(AuthError, match=msg):
        create_account(LocalUserStore(tmp_path / "a.json"), user, pw, confirm, invite)


def test_sign_in_errors_dont_reveal_usernames(tmp_path):
    store = LocalUserStore(tmp_path / "a.json")
    create_account(store, "anam", "long-enough", "long-enough", "invite-1")
    with pytest.raises(AuthError) as unknown:
        sign_in(store, "nobody", "long-enough")
    with pytest.raises(AuthError) as wrong:
        sign_in(store, "anam", "wrong-password")
    assert str(unknown.value) == str(wrong.value)


def test_reset_password_keeps_the_user_id(tmp_path):
    store = LocalUserStore(tmp_path / "a.json")
    rec = create_account(store, "anam", "long-enough", "long-enough", "invite-1")
    reset_password(store, "anam", "brand-new-pass")
    assert sign_in(store, "anam", "brand-new-pass").user_id == rec.user_id


class FakeWS:
    def __init__(self):
        self.rows = []

    def get_all_values(self):
        return [list(map(str, r)) for r in self.rows]

    def append_row(self, row):
        self.rows.append(list(row))

    def update(self, range_name, values):
        i = int(range_name.split(":")[0][1:]) - 1
        self.rows[i] = list(values[0])


class FakeSheet:
    def __init__(self):
        self.ws = None

    def worksheet(self, title):
        import gspread
        if self.ws is None:
            raise gspread.WorksheetNotFound(title)
        return self.ws

    def add_worksheet(self, title, rows, cols):
        self.ws = FakeWS()
        return self.ws


class FakeClient:
    def __init__(self):
        self.sheet = FakeSheet()

    def open_by_url(self, url):
        return self.sheet


def test_sheet_store_creates_users_tab_and_round_trips():
    client = FakeClient()
    store = SheetUserStore("https://docs.google.com/spreadsheets/d/x", client=client)
    rec = create_account(store, "anam", "long-enough", "long-enough", "invite-1")
    rows = client.sheet.ws.rows
    assert rows[0] == auth.HEADER and rows[1][1] == "anam" and "long-enough" not in rows[1]
    assert sign_in(store, "anam", "long-enough").user_id == rec.user_id
    reset_password(store, "anam", "brand-new-pass")
    assert sign_in(store, "anam", "brand-new-pass").user_id == rec.user_id


def test_sheet_store_unreachable_gives_a_plain_message():
    class Broken:
        def open_by_url(self, url):
            raise RuntimeError("403")
    with pytest.raises(AuthError, match="Couldn't reach the accounts Sheet"):
        SheetUserStore("u", client=Broken()).find("anam")
