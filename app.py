"""Proposal Pipeline v2: Streamlit app.  Run:  python -m streamlit run app.py

Screens: Passphrase → New job → Confirm details → Decision → Draft → Send. Plus My jobs, Projects, Settings.
Nothing loads, and no LLM call runs, until the passphrase is entered.
"""
from __future__ import annotations

import hmac
import statistics

import streamlit as st

from proposal_v2.config import load_config, save_env, secret

st.set_page_config(page_title="Proposal Pipeline v2", page_icon="📝", layout="centered")


# =========================================================================== passphrase gate
def is_local() -> bool:
    try:
        host = (st.context.headers.get("Host") or "").split(":")[0].lower()
    except Exception:
        host = ""
    return host in ("", "localhost", "127.0.0.1", "::1", "[::1]")


def setup() -> None:
    """First run: paste the keys here instead of editing .env by hand."""
    missing = [k for k in ("APP_PASSPHRASE", "GEMINI_API_KEY", "GROQ_API_KEY") if not secret(k)]
    if not missing:
        return
    if not is_local():
        # Online, only the owner sets keys (in the app's Secrets); strangers never see this form.
        st.error("This app isn't set up yet. The owner needs to add the keys in the app's Secrets settings.")
        st.stop()
    st.title("Set up Proposal Pipeline v2")
    st.write("This runs once. Paste your keys below; they're saved in the `.env` file on this computer only.")
    with st.form("setup"):
        invite = st.text_input("Passphrase", type="password", key="setup_invite", disabled="APP_PASSPHRASE" not in missing,
                               help="Any phrase you like. It's asked for each time the app opens.")
        gemini = st.text_input("Gemini API key", type="password", key="setup_gemini", disabled="GEMINI_API_KEY" not in missing,
                               help="Free from aistudio.google.com → Get API key. It starts with AIza.")
        groq = st.text_input("Groq API key", type="password", key="setup_groq", disabled="GROQ_API_KEY" not in missing,
                             help="Free from console.groq.com → API Keys. It starts with gsk_.")
        saved = st.form_submit_button("Save and continue", type="primary")
    if saved:
        values = {k: v.strip() for k, v in [("APP_PASSPHRASE", invite), ("GEMINI_API_KEY", gemini), ("GROQ_API_KEY", groq)]
                  if k in missing}
        empty = [k for k, v in values.items() if not v]
        if empty:
            st.error("Fill in every field.")
        else:
            save_env(values)
            st.rerun()
    st.stop()


def gate() -> None:
    """One passphrase box. Nothing loads, and no LLM call runs, until it's entered."""
    if st.session_state.get("authed"):
        return
    st.title("Proposal Pipeline v2")
    with st.form("gate"):
        pw = st.text_input("Passphrase", type="password", key="gate_pw")
        ok = st.form_submit_button("Open", type="primary")
    if ok:
        if hmac.compare_digest(pw.encode(), (secret("APP_PASSPHRASE") or "").encode()):
            st.session_state.authed = True
            st.rerun()
        st.error("That passphrase isn't right.")
    st.stop()


setup()
gate()

# Everything below runs only after the passphrase.
from proposal_v2.contracts import (Budget, ClientProfile, Profile, Project, ProposalRecord,  # noqa: E402
                                   ProposedProject)
from proposal_v2.integrations import FetchError, fetch_by_link, pdf_text, search_jobs  # noqa: E402
from proposal_v2.links import LINK_WARNING, LinkError  # noqa: E402
from proposal_v2.llm import LLMError, make_llm  # noqa: E402
from proposal_v2.pipeline import DuplicateJob, Pipeline, PipelineError  # noqa: E402
from proposal_v2.sample import load_sample, sample_jobs  # noqa: E402
from proposal_v2.storage import make_storage  # noqa: E402

USER_ERRORS = (LinkError, PipelineError, LLMError, FetchError)
DECISION_LABEL = {"apply": "Apply", "apply_with_questions": "Apply with questions", "skip": "Skip"}


def decision_label(d) -> str:
    return "Not checked" if d.code == "unchecked" else DECISION_LABEL[d.decision]


@st.cache_resource
def storage():
    return make_storage()


def llm():
    if "llm" not in st.session_state:
        st.session_state.llm = make_llm()
    return st.session_state.llm


ss = st.session_state
ss.setdefault("screen", "new")
ss.setdefault("job_key", None)
ss.setdefault("pending", None)

# =========================================================================== sidebar
with st.sidebar:
    st.header("Proposal Pipeline v2")
    ws = st.radio("Workspace", ["My workspace", "Sample workspace"], key="workspace",
                  help="Your data and the sample data are kept apart.")
    is_sample = ws == "Sample workspace"
    uid = "sample" if is_sample else "me"
    if is_sample:
        if st.button("Load sample data", help="A sample automation freelancer with 3 projects, plus 12 test jobs to try."):
            load_sample(storage(), uid)
            ss.screen, ss.job_key, ss.pending = "new", None, None
            st.success("Sample data loaded.")
    opening = "nav_to" in ss  # "Open" on a job in My jobs: show that job, not a blank form
    if opening:
        ss.page = ss.pop("nav_to")
    page = st.radio("Go to", ["New job", "My jobs", "Projects", "Settings"], key="page")
    # Coming back to New job from another page starts a fresh form.
    if page == "New job" and ss.get("last_page", "New job") != "New job" and not opening:
        ss.screen, ss.pending, ss.duplicate = "new", None, None
    ss.last_page = page
    mode = llm().mode
    if mode != "live":
        st.caption(f"AI mode: {mode} (saved responses)")

pipe = Pipeline(storage(), llm(), uid)


def run(action, *args, **kwargs):
    """Runs a pipeline action and shows plain errors instead of stack traces."""
    try:
        with st.spinner("Working on it..."):
            return action(*args, **kwargs)
    except DuplicateJob:
        raise
    except USER_ERRORS as e:
        st.error(str(e))
    except Exception as e:  # never a stack trace
        st.error(f"Something went wrong ({type(e).__name__}). Try again; if it keeps happening, check the runbook in the README.")
    return None


def go(screen: str, job_key: str | None = None) -> None:
    ss.screen = screen
    if job_key is not None:
        ss.job_key = job_key
    st.rerun()


def current() -> ProposalRecord | None:
    return storage().get_proposal(uid, ss.job_key) if ss.job_key else None


def num(label: str, value, key: str, help: str | None = None):
    """A number field that can be left blank (blank = not shown)."""
    raw = st.text_input(label, "" if value is None else (f"{value:g}" if isinstance(value, float) else str(value)), key=key, help=help)
    raw = raw.replace("$", "").replace(",", "").replace("%", "").strip()
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        st.caption(f":red[{label}: enter a number or leave it blank]")
        return value


def open_job_button(rec: ProposalRecord) -> None:
    st.link_button("Open job ↗", rec.job.link)


# =========================================================================== onboarding
profile = pipe.profile()
# Only the job pages need minimum rates; Projects and Settings open any time.
if not is_sample and (profile.min_hourly_usd is None or profile.min_fixed_usd is None) and page in ("New job", "My jobs"):
    st.title("Welcome")
    st.write("Set your minimum rates first. v2 skips jobs below them. Adding past projects is optional and can wait until a proposal needs proof.")
    with st.form("onboard"):
        h = st.number_input("Minimum hourly rate (USD)", min_value=0.0, value=30.0, step=5.0)
        f = st.number_input("Minimum fixed price (USD)", min_value=0.0, value=200.0, step=50.0)
        wt = st.text_input("Kinds of work you do (comma-separated)", placeholder="e.g. logo design, brand identity")
        sk = st.text_input("Your skills (comma-separated)", placeholder="e.g. Figma, Illustrator")
        if st.form_submit_button("Save and start"):
            profile.min_hourly_usd, profile.min_fixed_usd = h, f
            profile.work_types = [x.strip() for x in wt.split(",") if x.strip()]
            profile.skills = [x.strip() for x in sk.split(",") if x.strip()]
            storage().put_profile(uid, profile)
            st.rerun()
    st.stop()
if is_sample and not storage().get_profile(uid):
    st.info("The sample workspace is empty. Click **Load sample data** in the sidebar.")
    st.stop()


# =========================================================================== screens
def screen_new() -> None:
    st.title("New job")
    if ss.get("duplicate"):
        st.warning("You already have a draft for this job: open it, or regenerate as a new version.")
        c1, c2, c3 = st.columns(3)
        if c1.button("Open"):
            k, ss.duplicate = ss.duplicate, None
            rec = storage().get_proposal(uid, k)
            go("draft" if rec and rec.versions else "card", k)
        if c2.button("Regenerate as a new version"):
            k, ss.duplicate = ss.duplicate, None
            rec = storage().get_proposal(uid, k)
            if rec and rec.decision:
                if rec.decision.decision == "skip" and not rec.decision.overridden:
                    go("card", k)
                if run(pipe.write, rec):
                    go("draft", k)
        if c3.button("Dismiss"):
            ss.duplicate = None
            st.rerun()
    # Stored outside the widget, because Streamlit drops a widget's value once it leaves the page.
    ss.fit_choice = st.checkbox("Check if this job is a good fit first", value=ss.get("fit_choice", True), key="check_fit",
                help="Checks the client, the budget and the fit, then recommends Apply, Apply with questions or Skip. "
                     "Untick it to go straight to the draft; red flags and a low budget still show as warnings.")
    tab_paste, tab_link, tab_kw = st.tabs(["Paste a job", "Freelancer.com link", "Keyword search"])

    with tab_paste:
        if is_sample:
            jobs = sample_jobs()
            pick = st.selectbox("Try a sample job", ["—"] + [f"{j['id']}: {j['title']}" for j in jobs])
            if pick != "—" and st.button("Fill the form"):
                j = next(x for x in jobs if pick.startswith(x["id"]))
                ss.f_link, ss.f_details, ss.f_client = j["link"], j["job_details"], ""
                st.rerun()
        link = st.text_input("Job link *", key="f_link", placeholder="https://www.upwork.com/jobs/...")
        details = st.text_area("Job details *", key="f_details", height=220,
                               help="The whole job post. If you copy the whole page, v2 keeps only the main post and its own client box.")
        client = st.text_area("Client history (optional)", key="f_client", height=90,
                              help="The 'About the client' box, if it isn't in the job details. Without it, trust shows Unknown and you can still go ahead.")
        if st.button("Check job", type="primary"):
            try:
                rec = run(pipe.extract, link, details, client)
            except DuplicateJob as e:
                ss.duplicate = e.record.job_key
                st.rerun()
            if rec:
                ss.pending = rec.model_dump(mode="json")
                ss.duplicate = None
                go("confirm")

    with tab_link:
        st.caption("Only Freelancer.com links can be fetched; Upwork and others come in by paste.")
        flink = st.text_input("Freelancer.com project link")
        if st.button("Fetch job"):
            try:
                job = run(fetch_by_link, flink)
                rec = pipe.from_fetched(job) if job else None
            except DuplicateJob as e:
                ss.duplicate = e.record.job_key
                st.rerun()
            if rec:
                ss.pending = rec.model_dump(mode="json")
                go("confirm")

    with tab_kw:
        st.caption("Lists new matching Freelancer.com jobs. It filters and decides nothing; the decision runs once you pick a job.")
        kw = st.text_input("Keywords", ", ".join(profile.keywords))
        ex = st.text_input("Exclude terms", ", ".join(profile.exclude_terms))
        floor = num("Budget floor (USD, optional)", profile.budget_floor_usd, "kw_floor")
        if st.button("Search"):
            profile.keywords = [x.strip() for x in kw.split(",") if x.strip()]
            profile.exclude_terms = [x.strip() for x in ex.split(",") if x.strip()]
            profile.budget_floor_usd = floor
            storage().put_profile(uid, profile)
            jobs = run(search_jobs, profile.keywords, profile.exclude_terms, floor)
            if jobs is not None:
                seen = {r.job_key for r in storage().list_proposals(uid)}
                ss.results = [j.model_dump(mode="json") for j in jobs if j.job_key not in seen][: load_config()["feed"]["max_results"]]
        for i, jd in enumerate(ss.get("results") or []):
            from proposal_v2.contracts import JobPost

            j = JobPost.model_validate(jd)
            with st.container(border=True):
                st.markdown(f"**{j.title}**  \n{j.budget.raw_text} · Trust: Unknown, check the client manually")
                c1, c2 = st.columns([1, 1])
                c1.link_button("Open job ↗", j.link)
                if c2.button("Pick", key=f"pick{i}"):
                    try:
                        rec = pipe.from_fetched(j)
                        ss.pending = rec.model_dump(mode="json")
                        go("confirm")
                    except DuplicateJob:
                        st.warning("You already have this job.")
        if ss.get("results") == []:
            st.info("No new jobs match. Try broader keywords or fewer exclude terms.")


def screen_confirm() -> None:
    if not ss.pending:
        go("new")
    rec = ProposalRecord.model_validate(ss.pending)
    job, c = rec.job, rec.client
    st.title("Confirm the details")
    st.caption("Check what v2 took from the post. Fix anything wrong, then confirm. Fields marked * are required.")
    if job.link_status == "Warned":
        st.warning(LINK_WARNING)
        fix, proceed = st.columns(2)
        if fix.button("Fix the link or details"):
            go("new")
        proceed_ok = proceed.checkbox("Proceed anyway")
    else:
        proceed_ok = True
        st.caption(f"Link check: {job.link_status}")
    left_out = next((e["text"] for e in rec.events if e["type"] == "ignored_sections"), [])
    if left_out:
        st.caption("Left out of the paste: " + ", ".join(left_out))

    title = st.text_input("Title *", job.title)
    desc = st.text_area("Description *", job.description, height=200)
    st.subheader("Budget")
    kinds = ["hourly", "fixed", "fixed_range", "none"]
    kind = st.selectbox("Type", kinds, index=kinds.index(job.budget.kind),
                        format_func=lambda k: {"hourly": "Hourly", "fixed": "Fixed price", "fixed_range": "Fixed range", "none": "Not stated"}[k])
    b1, b2, b3 = st.columns(3)
    amount = b1.number_input("Amount / rate", value=float(job.budget.amount_usd or 0), min_value=0.0) if kind in ("fixed", "hourly") else None
    lo = b2.number_input("From", value=float(job.budget.min_usd or 0), min_value=0.0) if kind in ("hourly", "fixed_range") else None
    hi = b3.number_input("To", value=float(job.budget.max_usd or 0), min_value=0.0) if kind in ("hourly", "fixed_range") else None
    skills = st.text_input("Skills", ", ".join(job.skills))
    questions = st.text_area("Screening questions (one per line)", "\n".join(job.screening_questions))

    st.subheader("Client history")
    st.caption("Leave a field blank if the post doesn't show it.")
    k1, k2, k3 = st.columns(3)
    pv_opts = {"Not shown": None, "Verified": True, "Not verified": False}
    pv = k1.selectbox("Payment", list(pv_opts), index=list(pv_opts.values()).index(c.payment_verified))
    rating = num("Rating", c.rating, f"c_rating_{rec.job_key}")
    reviews = num("Reviews", c.reviews, f"c_reviews_{rec.job_key}")
    jobs_posted = num("Jobs posted", c.jobs_posted, f"c_jobs_{rec.job_key}")
    hire_rate = num("Hire rate %", c.hire_rate_pct, f"c_hr_{rec.job_key}")
    spent = num("Total spent (USD)", c.total_spent_usd, f"c_spent_{rec.job_key}")
    hires = num("Hires", c.hires, f"c_hires_{rec.job_key}")
    active = num("Active hires", c.active_hires, f"c_active_{rec.job_key}")

    if job.allowed_instructions or job.refused_instructions or job.ignored_instructions or job.red_flags:
        st.subheader("Instructions in the post")
        for i in job.allowed_instructions:
            st.markdown(f"✅ Will follow: _{i.text}_")
        for i in job.refused_instructions:
            st.markdown(f"🚫 Won't follow (asks you to claim something): _{i.text}_")
        for i in job.ignored_instructions:
            st.markdown(f"🙈 Ignored, aimed at an AI: _{i.text}_")
        for f in job.red_flags:
            st.markdown(f"🚩 Red flag: _{f.evidence}_")

    c_back, c_go = st.columns(2)
    if c_back.button("Back"):
        ss.pending = None
        go("new")
    checking = ss.get("fit_choice", True)
    if c_go.button("Confirm and check" if checking else "Confirm and write", type="primary", disabled=not proceed_ok):
        if not title.strip() or not desc.strip():
            st.error("Title and description are required.")
            return
        job.title, job.description = title.strip(), desc.strip()
        job.budget = Budget(kind=kind, amount_usd=amount or None, min_usd=lo or None, max_usd=hi or None,
                            approximate=job.budget.approximate, raw_text=job.budget.raw_text)
        job.skills = [s.strip() for s in skills.split(",") if s.strip()]
        job.screening_questions = [q.strip() for q in questions.splitlines() if q.strip()]
        rec.client = ClientProfile(payment_verified=pv_opts[pv], rating=rating, reviews=None if reviews is None else int(reviews),
                                   jobs_posted=None if jobs_posted is None else int(jobs_posted), hire_rate_pct=hire_rate,
                                   total_spent_usd=spent, total_spent_approximate=c.total_spent_approximate,
                                   hires=None if hires is None else int(hires), active_hires=None if active is None else int(active))
        if job.link_status == "Warned":
            rec.events.append({"type": "link_warning_proceeded"})
        try:
            done = run(pipe.decide, rec, checking)
        except DuplicateJob:
            done = None
        if done:
            ss.pending = None
            if not checking:
                ss.job_key = done.job_key
                if run(pipe.write, done):
                    go("draft", done.job_key)
                ss.flash = "The draft couldn't be written just now. Click Write proposal to try again."
            go("card", done.job_key)


def screen_card() -> None:
    rec = current()
    if not rec or not rec.decision:
        go("new")
    d = rec.decision
    st.title(rec.job.title)
    if ss.get("flash"):
        st.warning(ss.pop("flash"))
    box = st.info if d.code == "unchecked" else {"apply": st.success, "apply_with_questions": st.info, "skip": st.error}[d.decision]
    box(f"**{decision_label(d)}**  \n{d.reason}" + (" (overridden)" if d.overridden else ""))
    if d.card_note:
        st.warning(f"Note: {d.card_note}.")
    c1, c2 = st.columns(2)
    with c1:
        open_job_button(rec)
    with c2:
        if d.decision != "skip" or d.overridden:
            if st.button("Write proposal" if not rec.versions else "Open draft", type="primary"):
                if rec.versions or run(pipe.write, rec):
                    go("draft")
    if d.decision == "skip" and not d.overridden:
        with st.expander("Override this Skip"):
            why = st.text_input("Why? (optional, logged)")
            if st.button("Override and write anyway"):
                r = run(pipe.override, rec, why)
                if r and run(pipe.write, r):
                    go("draft")
    with st.expander("Details"):
        t = rec.trust
        st.markdown(f"**Client trust:** {t.score if t.score is not None else '—'} · {t.band} ({t.coverage})")
        for reason in t.reasons[:3]:
            st.markdown(f"- {reason}")
        st.markdown(f"**Budget:** {rec.job.budget.raw_text or 'not stated'} · gate: {d.budget_gate.replace('_', ' ')}")
        if d.fit:
            f = d.fit
            yn = lambda b: "Yes" if b else "No"  # noqa: E731
            st.markdown(f"**Fit:** {f.band}  \n- Skills: {yn(f.skills)}. {f.reasons.get('skills', '')}  \n"
                        f"- Kind of work you do: {yn(f.work_type)}. {f.reasons.get('work_type', '')}  \n"
                        f"- Proof in your projects: {yn(f.proof)}  \n- Realistic for the budget: {yn(f.realistic)}. {f.reasons.get('realistic', '')}  \n"
                        f"- Clear enough to plan: {yn(f.clear)}. {f.reasons.get('clear', '')}")
            st.markdown(f"**Skill overlap:** {f.skill_overlap}")
        st.markdown(f"**Link check:** {rec.job.link_status}")


def screen_draft() -> None:
    rec = current()
    if not rec:
        go("new")
    v = rec.latest()
    if not v:
        go("card")
    st.title(rec.job.title)
    if rec.decision.code == "unchecked" and rec.decision.card_note:
        st.warning(f"Fit check skipped. Heads-up: {rec.decision.card_note}.")
    st.caption(f"{decision_label(rec.decision)}{' (overridden)' if rec.decision.overridden else ''} · trust {rec.trust.band if rec.trust else '—'} · version {v.n}")

    projects = pipe.projects()
    labels = {l.project_id: l.label for l in (rec.assessment.project_labels if rec.assessment else [])}
    options = [None] + [p.id for p in projects]
    name = {None: "Plan only (no past project)"} | {p.id: f"{p.title} ({labels.get(p.id, 'not assessed').replace('_', '-')})" for p in projects}
    c1, c2 = st.columns([3, 1])
    choice = c1.selectbox("Proof", options, index=options.index(v.project_id) if v.project_id in options else 0, format_func=lambda x: name[x])
    if choice != v.project_id and c2.button("Rewrite with this proof"):
        if run(pipe.write, rec, choice):
            st.rerun()
    if st.button("+ Add project"):
        ss.nav_to = "Projects"
        st.rerun()

    if v.framing == "plan_only":
        asks = [r for r in rec.job.explicit_requirements
                if any(w in r.lower() for w in ("share", "portfolio", "example", "sample", "built", "past work", "previous work", "link"))]
        why = "Your Projects library is empty" if not projects else "No project was picked as proof"
        msg = f"**No past work is cited.** {why}, so this draft has no proof"
        msg += f" and doesn't answer the client's request: _{asks[0]}_" if asks else ""
        st.warning(msg + ". Add your work under **Projects** (+ Add project), then pick it in **Proof** above and click **Rewrite with this proof**.")
    val = v.validation
    if val.ok:
        st.success("Claim check passed: every number, tool and past-work claim traces to your project or the post.")
    else:
        st.warning("Needs review. The claim check still found problems after one retry:")
    for note in val.notes:
        st.markdown(f"- {note}")

    text = st.text_area("Proposal (edit freely)", v.text, height=300, key=f"edit_{rec.job_key}_{v.n}")
    st.caption(f"{len(text.split())} words · {len(text)} characters")
    st.code(text, language=None, wrap_lines=True)
    answers = []
    for i, a in enumerate(v.screening_answers):
        ans = st.text_area(a.question, a.answer, key=f"ans_{rec.job_key}_{v.n}_{i}")
        answers.append(ans)
        st.code(ans, language=None, wrap_lines=True)

    with st.expander("Revise with a comment"):
        comment = st.text_input("What should change?", placeholder="e.g. make the opening warmer; mention the deadline")
        if st.button("Revise") and comment.strip():
            if run(pipe.revise, rec, comment.strip(), text):
                st.rerun()
    with st.expander("Solution Brief (for the call)"):
        b = rec.brief
        if b:
            st.markdown(f"**Goal:** {b.goal}")
            st.markdown("**Plan:**\n" + "\n".join(f"{i}. {s.step}" + (f" (suggested: {', '.join(s.suggested_tools)})" if s.suggested_tools else "") for i, s in enumerate(b.plan, 1)))
            st.markdown("**Milestones:**\n" + "\n".join(f"- {m.name}: {m.deliverable} {m.budget_share}" for m in b.milestones))
            st.markdown("**Risks:**\n" + "\n".join(f"- {r.risk} → {r.mitigation}" for r in b.risks))
            st.markdown("**Questions:**\n" + "\n".join(f"- {q}" for q in b.questions))
            st.markdown("**Assumptions:**\n" + "\n".join(f"- {a}" for a in b.assumptions))
    if len(rec.versions) > 1:
        with st.expander(f"Earlier versions ({len(rec.versions) - 1})"):
            for old in rec.versions[:-1]:
                st.markdown(f"**v{old.n}** {('· ' + old.comment) if old.comment else ''}")
                st.text(old.text)

    st.divider()
    st.subheader("Send")
    st.caption("v2 never submits anything. Open the job, paste your proposal there, then mark it as sent.")
    c1, c2 = st.columns(2)
    with c1:
        open_job_button(rec)
    if rec.status != "sent":
        if c2.button("Mark as sent", type="primary"):
            r = run(pipe.mark_sent, rec, text)
            if r:
                (st.success if r[0].outcome.sheet_logged else st.warning)(f"Saved as sent. {r[1]}")
                st.rerun()
    else:
        o = rec.outcome
        st.success(f"Sent {o.sent_at[:10]} · {o.minutes_paste_to_sent} min from paste to sent"
                   + ("" if o.sheet_logged else f" · {o.sheet_error}"))
        if Pipeline.still_waiting(rec):
            st.info("Still waiting? Record what happened:")
        cols = st.columns(4)
        for col, (key, label) in zip(cols, [("replied", "Replied"), ("interview", "Interview"), ("hired", "Hired"), ("no_reply", "No reply")]):
            if col.button(label, type="primary" if o.result == key else "secondary"):
                pipe.set_outcome(rec, key)
                st.rerun()


def page_jobs() -> None:
    st.title("My jobs")
    recs = storage().list_proposals(uid)
    if not recs:
        st.info("No jobs yet. Add one under New job.")
        return
    sent = [r for r in recs if r.status == "sent"]
    mins = [r.outcome.minutes_paste_to_sent for r in sent if r.outcome.minutes_paste_to_sent is not None]
    m1, m2, m3 = st.columns(3)
    m1.metric("Sent", len(sent))
    m2.metric("Skipped", len([r for r in recs if r.status == "skipped"]))
    m3.metric("Median min, paste → sent", f"{statistics.median(mins):.0f}" if mins else "—")
    for r in recs:
        with st.container(border=True):
            dec = decision_label(r.decision) if r.decision else "—"
            badge = " · ⏳ Still waiting?" if Pipeline.still_waiting(r) else ""
            outcome = f" · {r.outcome.result.replace('_', ' ')}" if r.outcome.result else ""
            st.markdown(f"**{r.job.title}**  \n{dec} · {r.status}{outcome} · trust {r.trust.band if r.trust else '—'}{badge}")
            if st.button("Open", key=f"open_{r.job_key}"):
                ss.nav_to = "New job"
                go("draft" if r.versions else "card", r.job_key)


def page_projects() -> None:
    st.title("Projects")
    st.caption("Proof comes only from these. Leave out confidential client details and NDA work. Results: verifiable numbers only.")
    for p in pipe.projects():
        with st.expander(f"{p.title}"):
            project_form(p, key=p.id)
            if st.button("Delete", key=f"del_{p.id}"):
                storage().delete_project(uid, p.id)
                st.rerun()
    with st.expander("+ Add project"):
        project_form(None, key="new")
    st.subheader("Import from a CV or portfolio (optional)")
    up = st.file_uploader("Upload a PDF", type=["pdf"])
    pasted = st.text_area("…or paste the text")
    if st.button("Suggest projects"):
        text = pdf_text(up.getvalue()) if up else pasted
        res = run(pipe.propose_projects, text)
        if res:
            ss.proposed = [p.model_dump() for p in res.projects]
            if not res.projects:
                st.info("No projects found in that text.")
    for i, pd in enumerate(ss.get("proposed") or []):
        with st.container(border=True):
            st.caption("Suggested. Nothing is added until you confirm it.")
            p = ProposedProject.model_validate(pd)
            project_form(Project(id="new", **p.model_dump()), key=f"prop{i}", on_save=lambda i=i: ss.proposed.pop(i))
            if st.button("Discard", key=f"disc{i}"):
                ss.proposed.pop(i)
                st.rerun()


def next_project_id(ids: set[str]) -> str:
    return f"P{max([int(i[1:]) for i in ids if i[1:].isdigit()] + [0]) + 1}"


def project_form(p: Project | None, key: str, on_save=None) -> None:
    with st.form(f"proj_{key}"):
        title = st.text_input("Title *", p.title if p else "")
        problem = st.text_area("Problem", p.problem if p else "")
        did = st.text_area("What I did", p.what_i_did if p else "")
        skills = st.text_input("Skills (comma-separated)", ", ".join(p.skills) if p else "")
        result = st.text_input("Result (verifiable numbers only)", p.result if p else "")
        link = st.text_input("Link", (p.link or "") if p else "")
        roles = ["solo", "led", "contributed"]
        role = st.selectbox("Role", roles, index=roles.index(p.role) if p else 0)
        can_name = st.checkbox("I can name the client", p.can_name_client if p else False)
        if st.form_submit_button("Save"):
            if not title.strip():
                st.error("Add a title.")
                return
            ids = {x.id for x in pipe.projects()}
            pid = p.id if p and p.id in ids else next_project_id(ids)
            storage().put_project(uid, Project(id=pid, title=title.strip(), problem=problem, what_i_did=did,
                                               skills=[s.strip() for s in skills.split(",") if s.strip()], result=result,
                                               link=link or None, role=role, can_name_client=can_name))
            if on_save:
                on_save()
            st.rerun()


def page_settings() -> None:
    st.title("Settings")
    p = pipe.profile()
    cfg = load_config()["trust"]
    with st.form("settings"):
        st.subheader("Minimum rates")
        h = st.number_input("Minimum hourly rate (USD)", min_value=0.0, value=float(p.min_hourly_usd or 0))
        f = st.number_input("Minimum fixed price (USD)", min_value=0.0, value=float(p.min_fixed_usd or 0))
        st.subheader("Your work")
        wt = st.text_input("Kinds of work you do", ", ".join(p.work_types))
        sk = st.text_input("Skills", ", ".join(p.skills))
        st.subheader("Client score cut-offs")
        st.caption("A score at or above the number gets the band. Below Low is a red flag.")
        cut = p.trust_cutoffs or {}
        c1, c2, c3, c4 = st.columns(4)
        ex = c1.number_input("Excellent", value=float(cut.get("excellent", cfg["excellent"])))
        hi = c2.number_input("High", value=float(cut.get("high", cfg["high"])))
        me = c3.number_input("Medium", value=float(cut.get("medium", cfg["medium"])))
        lo = c4.number_input("Low", value=float(cut.get("low", cfg["low"])))
        st.subheader("Google Sheet")
        sheet = st.text_input("Sheet link", p.sheet_url, help="Every Mark as sent adds a row: date, job, link, decision, client trust, proof, minutes from paste to sent, and how much you edited the draft. Share the Sheet with the app's service-account email as an editor.")
        if st.form_submit_button("Save"):
            p.min_hourly_usd, p.min_fixed_usd = h, f
            p.work_types = [x.strip() for x in wt.split(",") if x.strip()]
            p.skills = [x.strip() for x in sk.split(",") if x.strip()]
            p.trust_cutoffs = {"excellent": ex, "high": hi, "medium": me, "low": lo}
            p.sheet_url = sheet.strip()
            storage().put_profile(uid, p)
            st.success("Saved. Every change is logged.")
    log = storage().settings_log(uid)
    if log:
        with st.expander(f"Change log ({len(log)})"):
            for e in reversed(log[-20:]):
                st.markdown(f"- {e['at']} · {e['by']}: " + ", ".join(e["changes"]))
    with st.expander("Delete all data in this workspace"):
        st.caption("Removes your jobs, drafts, projects and settings from this app. Rows already in your Google Sheet stay there.")
        if st.checkbox("I understand this can't be undone") and st.button("Delete everything"):
            storage().clear_user(uid)
            ss.screen, ss.job_key, ss.pending = "new", None, None
            st.rerun()


# =========================================================================== router
if page == "New job":
    {"new": screen_new, "confirm": screen_confirm, "card": screen_card, "draft": screen_draft}[ss.screen]()
    if ss.screen != "new" and st.sidebar.button("+ New job"):
        ss.pending = None
        go("new")
elif page == "My jobs":
    page_jobs()
elif page == "Projects":
    page_projects()
else:
    page_settings()
