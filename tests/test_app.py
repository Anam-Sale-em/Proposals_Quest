"""Clicks through the Streamlit app headlessly with the scripted LLM: first-run key setup, the
passphrase gate, then paste → confirm → decision → draft → send, Skip with Override, the
duplicate block, and the onboarding rule."""
import pytest
from streamlit.testing.v1 import AppTest

from tests.scripted_llm import ScriptedLLM

PASS = "open sesame"


def _btn(at, label, where=None):
    return next(b for b in (where or at).button if b.label == label)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("PV2_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("APP_PASSPHRASE", PASS)
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GROQ_API_KEY", "test")
    monkeypatch.setenv("PV2_ENV_FILE", str(tmp_path / ".env"))
    yield


def _app(llm=None):
    at = AppTest.from_file("../app.py", default_timeout=30)
    at.session_state["llm"] = llm or ScriptedLLM()
    return at.run()


def _open(at, pw=PASS):
    at.text_input(key="gate_pw").input(pw)
    _btn(at, "Open").click().run()
    return at


def _sample(at):
    at.sidebar.radio(key="workspace").set_value("Sample workspace").run()
    _btn(at, "Load sample data", at.sidebar).click().run()


def _paste(at, cid):
    at.selectbox[0].set_value(next(o for o in at.selectbox[0].options if o.startswith(cid))).run()
    _btn(at, "Fill the form").click().run()
    _btn(at, "Check job").click().run()


def _no_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("PV2_ENV_FILE", str(tmp_path / ".env"))
    monkeypatch.setenv("PV2_DATA_ROOT", str(tmp_path))
    for k in ("APP_PASSPHRASE", "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(k, raising=False)


def test_first_run_setup_saves_keys_then_shows_the_gate(tmp_path, monkeypatch):
    _no_keys(tmp_path, monkeypatch)
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert at.title[0].value == "Set up Proposal Pipeline v2" and not at.sidebar.radio
    _btn(at, "Save and continue").click().run()
    assert any("Fill in every field" in e.value for e in at.error)
    at.text_input(key="setup_invite").input("code-123")
    at.text_input(key="setup_gemini").input("AIza-test")
    at.text_input(key="setup_groq").input("gsk_test")
    _btn(at, "Save and continue").click().run()
    text = (tmp_path / ".env").read_text()
    assert "APP_PASSPHRASE=code-123" in text and "GROQ_API_KEY=gsk_test" in text
    assert at.text_input(key="gate_pw") is not None and not at.exception


def test_setup_form_never_shows_online(tmp_path, monkeypatch):
    """With keys missing on a public host, strangers get a plain message, never the key form."""
    _no_keys(tmp_path, monkeypatch)
    import streamlit as st
    monkeypatch.setattr(type(st.context), "headers", property(lambda self: {"Host": "my-app.streamlit.app"}))
    at = AppTest.from_file("../app.py", default_timeout=30).run()
    assert any("isn't set up yet" in e.value for e in at.error)
    assert not [t for t in at.text_input if t.key == "setup_gemini"]


def test_wrong_passphrase_loads_nothing(env):
    llm = ScriptedLLM()
    at = _open(_app(llm), "wrong")
    assert any("isn't right" in e.value for e in at.error)
    assert not at.sidebar.radio and llm.calls == []


def test_paste_to_send_on_a_sample_job(env):
    at = _open(_app())
    _sample(at)
    _paste(at, "T01")
    assert at.title[0].value == "Confirm the details", [e.value for e in at.error]
    _btn(at, "Confirm and check").click().run()
    assert any('class="verdict"' in m.value and ">Apply<" in m.value for m in at.markdown), [e.value for e in at.error]
    _btn(at, "Write proposal").click().run()
    assert any("Checked against your projects" in m.value for m in at.markdown), [w.value for w in at.warning]
    _btn(at, "Mark as sent").click().run()
    assert any(m.value.startswith("Sent ") for m in at.success), [w.value for w in at.warning]
    at.sidebar.radio(key="page").set_value("My jobs").run()
    assert "Sent" in [m.label for m in at.metric]
    assert not at.exception, at.exception


def test_skip_override_and_duplicate(env):
    at = _open(_app())
    _sample(at)
    _paste(at, "T10")
    _btn(at, "Confirm and check").click().run()
    assert any(">Skip<" in m.value and "WhatsApp" in m.value for m in at.markdown), [e.value for e in at.error]
    _btn(at, "Override and write anyway").click().run()
    assert not at.exception, at.exception
    assert any("Draft 1" in c.value for c in at.caption), [w.value for w in at.warning]  # lands on the draft
    _btn(at, "+ New job", at.sidebar).click().run()
    _paste(at, "T10")
    assert any("already have this job" in w.value for w in at.warning)
    assert not at.exception
    _btn(at, "Check again").click().run()  # removes the old record so the job can be checked fresh
    assert any("Removed the old check" in i.value for i in at.info)
    _btn(at, "Check job").click().run()
    assert at.title[0].value == "Confirm the details", [w.value for w in at.warning]


def test_projects_open_before_rates_are_set(env):
    at = _open(_app())
    assert at.title[0].value == "Welcome"  # New job waits for the rates
    at.sidebar.radio(key="page").set_value("Projects").run()
    assert at.title[0].value == "Projects" and not at.exception


def test_fit_check_can_be_skipped_but_still_warns(env):
    at = _open(_app())
    _sample(at)
    at.checkbox(key="check_fit").uncheck().run()
    _paste(at, "T10")  # the red-flag WhatsApp job
    _btn(at, "Confirm and write").click().run()
    assert not at.exception, at.exception
    assert any("Fit check skipped" in w.value and "WhatsApp" in w.value for w in at.warning), [w.value for w in at.warning]
    assert at.caption and any("Fit check skipped" in c.value for c in at.caption)



def test_plan_only_draft_warns_about_missing_proof(env):
    """My workspace starts with no projects, so a draft can only be plan-only, and the app says so."""
    import json
    from pathlib import Path
    job = json.loads((Path(__file__).resolve().parent.parent / "fixtures" / "jobs" / "T01.json").read_text(encoding="utf-8"))
    at = _open(_app())
    _btn(at, "Save and start").click().run()  # onboarding: default minimum rates
    at.checkbox(key="check_fit").uncheck().run()
    at.text_input(key="f_link").input(job["pastes"][0]["link"])
    at.text_area(key="f_details").input(job["pastes"][0]["job_details"])
    _btn(at, "Check job").click().run()
    _btn(at, "Confirm and write").click().run()
    assert any("No past work is cited" in w.value and "library is empty" in w.value for w in at.warning), [w.value for w in at.warning]
    assert not at.exception


def test_new_job_page_starts_fresh_after_visiting_another_page(env):
    at = _open(_app())
    _sample(at)
    _paste(at, "T01")
    assert at.title[0].value == "Confirm the details"
    at.sidebar.radio(key="page").set_value("My jobs").run()
    at.sidebar.radio(key="page").set_value("New job").run()
    assert at.title[0].value == "New job" and not at.exception


def test_number_fields_accept_loose_input():
    from app import parse_number
    assert parse_number("USD, 300") == 300 and parse_number("$1,500") == 1500 and parse_number("1.5k") == 1500
    assert parse_number("80%") == 80 and parse_number("4.9") == 4.9 and parse_number("  ") == "blank"
    assert parse_number("abc") is None and parse_number("300-500") is None
