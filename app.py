"""Proposal Pipeline v2: Streamlit app.  Run:  python -m streamlit run app.py

Screens: Passphrase → New job → Confirm details → Decision → Draft → Send. Plus My jobs, Projects, Settings.
Nothing loads, and no LLM call runs, until the passphrase is entered.
"""
from __future__ import annotations

import hmac
import re
import statistics

import streamlit as st

from proposal_v2.config import load_config, save_env, secret

st.set_page_config(page_title="Proposal Pipeline v2", page_icon="📝", layout="centered")
from proposal_v2.prompts import budget_words  # noqa: E402
from proposal_v2.ui_style import BRAND, CSS, chip, trust_chip, verdict_html  # noqa: E402

st.markdown(CSS, unsafe_allow_html=True)


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
from proposal_v2.skills import norm  # noqa: E402
from proposal_v2.integrations import FetchError, fetch_by_link, match_places, match_snippet, pdf_text, search_jobs  # noqa: E402
from proposal_v2.links import LINK_WARNING, LinkError  # noqa: E402
from proposal_v2.llm import LLMError, make_llm  # noqa: E402
from proposal_v2.pipeline import DuplicateJob, Pipeline, PipelineError  # noqa: E402
from proposal_v2.sample import WHOLE_PAGE_CASES, is_sample_link, sample_client, sample_fetched_job, sample_search, split_client_box, load_sample, sample_jobs  # noqa: E402
from proposal_v2.storage import make_storage  # noqa: E402

USER_ERRORS = (LinkError, PipelineError, LLMError, FetchError)
DECISION_LABEL = {"apply": "Apply", "apply_with_questions": "Apply with questions", "skip": "Skip"}


def decision_label(d) -> str:
    return "Fit check skipped" if d.code == "unchecked" else DECISION_LABEL[d.decision]


def summary_line(rec) -> str:
    """e.g. "Decision: Apply · Client trust: High (64/100)" or "Fit check skipped · Client trust: Unknown"."""
    d = rec.decision
    if d is None:
        first = "Not decided yet"
    elif d.code == "unchecked":
        first = "Fit check skipped"
    else:
        first = f"Decision: {DECISION_LABEL[d.decision]}{' (your override)' if d.overridden else ''}"
    t = rec.trust
    trust = "—" if t is None else (t.band if t.score is None else f"{t.band} ({t.score}/100)")
    return f"{first} · Client trust: {trust}"


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
    st.markdown(BRAND, unsafe_allow_html=True)
    ws = st.radio("Workspace", ["My workspace", "Sample workspace"], key="workspace", horizontal=True,
                  format_func=lambda w: "Mine" if w == "My workspace" else "Sample",
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
    NAV_ICONS = {"New job": ":material/add_circle:", "My jobs": ":material/work_history:",
                 "Projects": ":material/folder_open:", "Settings": ":material/tune:"}
    page = st.radio("Menu", ["New job", "My jobs", "Projects", "Settings"], key="page",
                    format_func=lambda p: f"{NAV_ICONS[p]}&nbsp;&nbsp;{p}")
    # Coming back to New job from another page starts a fresh form.
    if page == "New job" and ss.get("last_page", "New job") != "New job" and not opening:
        ss.screen, ss.pending, ss.duplicate = "new", None, None
    ss.last_page = page
    mode = llm().mode
    if mode != "live":
        st.caption(f"AI mode: {mode} (saved responses)")

pipe = Pipeline(storage(), llm(), uid)


WORKING = {"recheck": "Checking the fit again…", "decide": "Checking the fit…", "extract": "Reading the job…",
           "write": "Writing your proposal… this takes about a minute", "revise": "Revising the draft…",
           "override": "Getting the job ready to write…", "fetch_by_link": "Fetching the job from Freelancer.com…",
           "search_jobs": "Searching Freelancer.com…", "sample_search": "Searching the sample jobs…",
           "propose_projects": "Reading your CV…", "mark_sent": "Saving…"}


def run(action, *args, **kwargs):
    """Runs a pipeline action with a visible "working" line and a timer, and shows plain errors instead of stack traces."""
    try:
        with st.spinner(WORKING.get(getattr(action, "__name__", ""), "Working on it…"), show_time=True):
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
    v = parse_number(raw)
    if v == "blank":
        return None
    if v is None:
        st.caption(f":red[{label}: enter one number, like 300, or leave it blank]")
        return value
    return v


def parse_number(raw: str):
    """Reads one number from loose input: "USD, 300", "$1,500", "1.5k", "80%". Returns "blank",
    the number, or None when there's no number or more than one."""
    import re

    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", raw or "").strip()
    if not s:
        return "blank"
    found = re.findall(r"\d+(?:\.\d+)?\s*[kK]?\b", s)
    if len(found) != 1:
        return None
    n = found[0].strip()
    return float(n[:-1]) * 1000 if n[-1] in "kK" else float(n)


def open_job_button(rec: ProposalRecord, where=st) -> None:
    link_or_note(rec.job.link, where)


LINK_STATUS = {
    "Matched": "Matched: the link's title matches the post",
    "Warned": "Warned: the link's title doesn't match the post",
    "Unchecked": "Not checked: this link has no job title in it to compare (normal for Upwork ID links)",
    "Fetched": "Fetched straight from Freelancer.com",
}


def recheck_button(rec: ProposalRecord, label: str) -> None:
    """Runs the fit check again with today's settings and projects. Not offered once a job is sent."""
    if rec.status == "sent":
        return
    if st.button(label, key=f"recheck_{rec.job_key}",
                 help="Uses your current skills, work types, rates and projects. Your drafts stay."):
        r = run(pipe.recheck, rec)
        if r:  # stay on this screen and show the new result here
            ss.rechecked = r.job_key
            st.rerun()


def recheck_result(rec: ProposalRecord) -> None:
    """After "Check the fit again", the new decision and its reason, shown on the screen the user is on."""
    if ss.get("rechecked") != rec.job_key or not rec.decision:
        return
    ss.rechecked = None
    d = rec.decision
    msg = f"**Checked again: {decision_label(d)}.** {d.reason}"
    (st.warning if d.decision == "skip" else st.success)(msg.replace("$", "\\$"))


def md(text: str, where=st) -> None:
    """Markdown with dollar signs kept literal (Streamlit reads $...$ as maths)."""
    where.markdown(text.replace("$", "\\$"))


def link_or_note(link: str, where=st) -> None:
    """Open job, or a note for sample jobs, whose made-up links lead nowhere."""
    if is_sample_link(link):
        where.caption("Sample job: there's no live page to open.")
    else:
        where.link_button("Open job ↗", link)


# =========================================================================== onboarding
profile = pipe.profile()
# Only the job pages need minimum rates; Projects and Settings open any time.
if not is_sample and (profile.min_hourly_usd is None or profile.min_fixed_usd is None) and page in ("New job", "My jobs"):
    st.title("Welcome")
    st.write("Set your minimum rates first. v2 skips jobs below them. Adding past projects is optional and can wait until a proposal needs proof.")
    with st.form("onboard", enter_to_submit=False):
        h = st.number_input("Minimum hourly rate (USD)", min_value=0.0, value=30.0, step=5.0)
        f = st.number_input("Minimum fixed price (USD)", min_value=0.0, value=200.0, step=50.0)
        wt = st.text_input("Kinds of work you do (comma-separated)", placeholder="e.g. workflow automation, AI chatbots, mobile apps", help="What you deliver, not the tools: v2 skips jobs that aren't one of these. Tools go under skills.")
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
        st.warning("You already have this job. Open it, write a new version of the proposal, or check it again "
                   "from scratch with the latest rules.")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("Open"):
            k, ss.duplicate = ss.duplicate, None
            rec = storage().get_proposal(uid, k)
            go("draft" if rec and rec.versions else "card", k)
        if c2.button("New version"):
            k, ss.duplicate = ss.duplicate, None
            rec = storage().get_proposal(uid, k)
            if rec and rec.decision:
                if rec.decision.decision == "skip" and not rec.decision.overridden:
                    go("card", k)
                if run(pipe.write, rec):
                    go("draft", k)
        existing = storage().get_proposal(uid, ss.duplicate)
        if existing and existing.status != "sent" and c3.button("Check again"):
            storage().delete_proposal(uid, ss.duplicate)
            ss.duplicate = None
            ss.flash_new = "Removed the old check. Click Check job (or Fetch job) again to check it with the latest rules."
            st.rerun()
        if c4.button("Dismiss"):
            ss.duplicate = None
            st.rerun()
    if ss.get("flash_new"):
        st.info(ss.pop("flash_new"))
    # Stored outside the widget, because Streamlit drops a widget's value once it leaves the page.
    ss.fit_choice = st.checkbox("Check if this job is a good fit first", value=ss.get("fit_choice", True), key="check_fit",
                help="Checks the client, the budget and the fit, then recommends **Apply**, **Apply with questions** "
                     "(worth applying, but the post is vague or the budget looks unreal, so the proposal leads with questions) "
                     "or **Skip**. Untick it to go straight to the draft; red flags and a low budget still show as warnings. "
                     "You can run the check later from the job.")
    tab_paste, tab_link, tab_kw = st.tabs(["Paste a job (any platform)", "Freelancer.com link", "Freelancer.com search"])

    with tab_paste:
        st.caption("Works with jobs from **Upwork, Freelancer.com and Guru**. "
                   "Paste the job's link, then copy the job page's text into Job details.")
        if is_sample:
            jobs = sample_jobs()
            pick = st.selectbox("Try a sample job", ["—"] + [f"{j['id']}: {j['title']}" + (" (whole page pasted as is)" if j["id"] in WHOLE_PAGE_CASES else "") for j in jobs])
            if pick != "—" and st.button("Fill the form"):
                j = next(x for x in jobs if pick.startswith(x["id"]))
                post, box = split_client_box(j["id"], j["job_details"])
                ss.f_link, ss.f_details, ss.f_client = j["link"], post, box
                st.rerun()
        link = st.text_input("Job link *", key="f_link", placeholder="Link to the job post on Upwork, Freelancer.com or Guru")
        st.caption("Use the job's own page. On **Freelancer.com**, copy it from the project's **Share** button "
                   "(top right) → **Copy link**, since the address bar of a search page won't work.")
        details = st.text_area("Job details *", key="f_details", height=220,
                               help="The whole job post. If you copy the whole page, v2 keeps only the main post and its own client box.")
        client = st.text_area("Client history (optional)", key="f_client", height=90,
                              help="Without it, client trust shows Unknown and you can still go ahead.")
        st.caption("Where to find it: the **About the client** section of the job's page. On Upwork it's below the skills "
                   "and \"Activity on this job\"; on Freelancer.com it's on the right side. Copy it here if your paste above doesn't include it.")
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
        st.caption("Open the project on Freelancer.com, click **Share** (top right) → **Copy link**, and paste it here. "
                   "Upwork and other platforms: use Paste a job.")
        use_sample = False
        if is_sample:
            st.info("Sample workspace: try a saved sample Freelancer.com job, or paste a real link to fetch it live.")
            use_sample = st.button("Use the sample Freelancer.com job")
        flink = st.text_input("Freelancer.com project link",
                              placeholder="https://www.freelancer.com/projects/automation/...")
        if st.button("Fetch job") or use_sample:
            try:
                job = sample_fetched_job() if use_sample else run(fetch_by_link, flink)
                rec = pipe.from_fetched(job, sample_client(job)) if job else None
            except DuplicateJob as e:
                ss.duplicate = e.record.job_key
                st.rerun()
            if rec:
                ss.pending = rec.model_dump(mode="json")
                go("confirm")

    with tab_kw:
        st.caption("Find new Freelancer.com jobs by keyword. Pick one, and v2 checks it and writes the proposal.")
        if is_sample:
            st.info("Sample workspace: this searches 4 saved sample Freelancer.com jobs, not the live site, "
                    "and shows the ones that match your keywords and budget floor. Switch to My workspace to search live.")
        # Search terms live in this browser's session only: the live link has one shared workspace,
        # so saving them would show one person's search on everyone's device.
        kw = st.text_input("Keywords", ", ".join(profile.keywords) if is_sample else "",
                           key=f"kw_{uid}", placeholder="React Native, n8n, Flutter", help="Separate keywords with commas.")
        floor = num("Budget floor (USD, optional)", None, f"kw_floor_{uid}")
        ss.kw_list = [x.strip() for x in kw.split(",") if x.strip()]
        rkey = f"results_{uid}"  # each workspace keeps its own results: a live search never shows in Sample
        if st.button("Search"):
            jobs = run(sample_search if is_sample else search_jobs, ss.kw_list, [], floor)
            if jobs is not None:
                seen = {r.job_key for r in storage().list_proposals(uid)}
                ss[rkey] = [j.model_dump(mode="json") for j in jobs if j.job_key not in seen][: load_config()["feed"]["max_results"]]
        if ss.get(rkey):
            n = len(ss[rkey])
            tail = ("Sample jobs come with their client details." if is_sample else
                    "Freelancer.com doesn't share client history, so check the client on the job page before you pick.")
            st.markdown(f"**{n} job{'s' if n != 1 else ''} match.** {tail}")
        for i, jd in enumerate(ss.get(rkey) or []):
            from proposal_v2.contracts import JobPost

            j = JobPost.model_validate(jd)
            with st.container(border=True, key=f"card_feed_{i}"):
                places = match_places(j, ss.get("kw_list", []))
                hits = {norm(k) for k, _ in places}
                tags = ", ".join(f"**{s}**" if norm(s) in hits else s for s in j.skills) or "None listed"
                found = ", ".join(f"**{k}** ({where})" for k, where in places)
                md(f"**{j.title}**  \n💰 {j.budget.raw_text or 'Budget not stated'}  \n🛠 {tags}  \n🔎 Matches {found}")
                for k, where in places:
                    if where == "description":  # show the words around it, so a mention deep in the post is visible
                        st.caption(f"\"{match_snippet(k, j.description)}\"")
                c1, c2 = st.columns([1, 1])
                link_or_note(j.link, c1)
                if c2.button("Pick", key=f"pick{i}"):
                    try:
                        rec = pipe.from_fetched(j, sample_client(j))
                        ss.pending = rec.model_dump(mode="json")
                        go("confirm")
                    except DuplicateJob:
                        st.warning("You already have this job.")
        if ss.get(rkey) == []:
            st.info("No new jobs match. Try broader keywords or a lower budget floor.")


def screen_confirm() -> None:
    if not ss.pending:
        go("new")
    rec = ProposalRecord.model_validate(ss.pending)
    job, c = rec.job, rec.client
    st.title("Confirm the details")
    if job.link_status == "Warned":
        st.warning(LINK_WARNING)
        fix, proceed = st.columns(2)
        if fix.button("Fix the link or details"):
            go("new")
        proceed_ok = proceed.checkbox("Proceed anyway")
    else:
        proceed_ok = True

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
    questions = "\n".join(job.screening_questions)
    if job.screening_questions:
        questions = st.text_area("Questions the client asks applicants (v2 answers each one)", questions,
                                 help="Taken from the post. Edit or remove any that aren't real questions; one per line.")
    notes = st.text_area("Anything you want in the proposal? (optional)", job.user_notes,
                         placeholder="e.g. I can start Monday · mention I've built 3 Shopify apps · ask about their CRM",
                         help="Your own words. v2 works them into the proposal and treats them as true, so only write what is.")

    st.subheader("Proof")
    my_projects = pipe.projects()
    proof_modes = {"auto": "Let v2 pick the best match", "manual": "I'll choose", "none": "No past project for this job"}
    if not my_projects:
        st.caption("You have no projects yet, so this draft will be a plan without past work. "
                   "Add your work under **Projects** to cite it.")
        proof_mode, proof_pick = "none", []
    else:
        proof_mode = st.radio("Which past work should the proposal cite?", list(proof_modes), horizontal=True,
                              index=list(proof_modes).index(rec.proof_choice), format_func=proof_modes.get,
                              key=f"proofmode_{rec.job_key}")
        proof_pick = []
        if proof_mode == "manual":
            names = {p.id: p.title for p in my_projects}
            proof_pick = st.multiselect("Projects to cite (up to 3; the first is the main one)", list(names),
                                        default=[i for i in rec.manual_proof if i in names], format_func=names.get,
                                        max_selections=3, key=f"proofpick_{rec.job_key}")
        elif proof_mode == "auto":
            st.caption("v2 picks the closest project after the fit check, or the one sharing the most skills if you skip it.")

    st.subheader("Client history")
    on_freelancer = job.platform == "freelancer"
    where = {"upwork": "below the skills and \"Activity on this job\"", "freelancer": "on the right side"}.get(job.platform, "")
    box = "**Posted By**" if job.platform == "guru" else "**About the client**"
    if is_sample_link(job.link):
        st.caption("Sample job: the client details are filled in from its sample page.")
    else:
        st.caption(f"Find it in the {box} section of the job's page{(', ' + where) if where else ''}. "
                   "Copy what it shows into the fields below; leave the rest blank.")
        link_or_note(job.link)
    pv_opts = {"Not shown": None, "Verified": True, "Not verified": False}
    on_guru = job.platform == "guru"
    # (key, label, current value), per platform: each one shows a different client box.
    if on_freelancer:
        fields = [("rating", "Rating", c.rating), ("reviews", "Reviews", c.reviews)]
    elif on_guru:
        fields = [("feedback_pct", "Feedback %", c.feedback_pct), ("total_spent_usd", "Total spend (USD)", c.total_spent_usd),
                  ("jobs_posted", "Jobs posted", c.jobs_posted), ("jobs_paid", "Jobs paid", c.jobs_paid),
                  ("paid_invoices_pct", "Paid invoices %", c.paid_invoices_pct),
                  ("outstanding_invoices", "Outstanding invoices", c.outstanding_invoices)]
    else:
        fields = [("rating", "Rating", c.rating), ("reviews", "Reviews", c.reviews),
                  ("jobs_posted", "Jobs posted", c.jobs_posted), ("hire_rate_pct", "Hire rate %", c.hire_rate_pct),
                  ("total_spent_usd", "Total spent (USD)", c.total_spent_usd), ("hires", "Hires", c.hires),
                  ("active_hires", "Active hires", c.active_hires)]
    shown = [f for f in fields if f[2] is not None]
    hidden = [f for f in fields if f[2] is None]
    vals = {}
    pv = "Not shown"
    asks_payment = not on_guru  # Guru shows paid invoices instead of a payment-verified badge
    if not shown and (c.payment_verified is None or not asks_payment):
        st.caption("Nothing from that box came through with the post, so client trust will be Unknown unless you add it below.")
    if asks_payment and c.payment_verified is not None:
        pv = st.selectbox("Payment", list(pv_opts), index=list(pv_opts.values()).index(c.payment_verified))
    for key, label, value in shown:
        vals[key] = num(label, value, f"c_{key}_{rec.job_key}")
    if hidden or (asks_payment and c.payment_verified is None):
        title_more = ("Add client details from the job page" if (on_freelancer or on_guru)
                      else "Add client details the post didn't show")
        with st.expander(title_more):
            if on_freelancer:
                st.caption("Freelancer.com's \"About the Client\" box shows the star rating, the number next to it (reviews) "
                           "and Payment verified. Those three are all v2 needs.")
            if on_guru:
                st.caption("Guru's \"Posted By\" box shows Feedback, Total Spend, Jobs Posted, Jobs Paid, "
                           "Paid Invoices and Outstanding Invoices.")
            if asks_payment and c.payment_verified is None:
                pv = st.selectbox("Payment", list(pv_opts), index=0)
            for key, label, value in hidden:
                vals[key] = num(label, value, f"c_{key}_{rec.job_key}")

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
        job.user_notes = notes.strip()
        if proof_mode == "manual" and not proof_pick:
            st.error("Pick at least one project, or choose another option under Proof.")
            return
        rec.proof_choice, rec.manual_proof = proof_mode, proof_pick
        as_int = lambda k: None if vals.get(k) is None else int(vals[k])  # noqa: E731
        rec.client = ClientProfile(payment_verified=pv_opts[pv], rating=vals.get("rating"), reviews=as_int("reviews"),
                                   jobs_posted=as_int("jobs_posted"), hire_rate_pct=vals.get("hire_rate_pct"),
                                   total_spent_usd=vals.get("total_spent_usd"), total_spent_approximate=c.total_spent_approximate,
                                   hires=as_int("hires"), active_hires=as_int("active_hires"),
                                   feedback_pct=vals.get("feedback_pct"), jobs_paid=as_int("jobs_paid"),
                                   paid_invoices_pct=vals.get("paid_invoices_pct"), outstanding_invoices=as_int("outstanding_invoices"))
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
    recheck_result(rec)
    tone = "unchecked" if d.code == "unchecked" else d.decision
    word = decision_label(d) + (" (your override)" if d.overridden else "")
    chips = [trust_chip(rec.trust), chip(f"Budget: {rec.job.budget.raw_text or 'not stated'}")]
    if d.fit:
        chips.append(chip(f"Fit: {d.fit.band}"))
    note = f"{d.card_note[0].upper()}{d.card_note[1:]}." if d.card_note else ""
    st.markdown(verdict_html(word, tone, d.reason, chips, note), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        open_job_button(rec)
    with c2:
        if d.decision != "skip" or d.overridden:
            if st.button("Write proposal" if not rec.versions else "Open draft", type="primary"):
                if rec.versions or run(pipe.write, rec):
                    go("draft")
    recheck_button(rec, "Check the fit now" if d.code == "unchecked" else "Check the fit again")
    if d.decision == "skip" and not d.overridden:
        with st.expander("Override this Skip"):
            why = st.text_input("Why? (optional, logged)")
            if st.button("Override and write anyway"):
                r = run(pipe.override, rec, why)
                if r and run(pipe.write, r):
                    go("draft")
    with st.expander("Details"):
        t = rec.trust
        md(f"**Client trust:** {t.score if t.score is not None else '—'} · {t.band} ({t.coverage})")
        for reason in t.reasons[:3]:
            md(f"- {reason}")
        md(f"**Budget:** {budget_words(rec.job.budget)} · against your minimum: {d.budget_gate.replace('_', ' ')}")
        if d.fit:
            f = d.fit
            yn = lambda b: "Yes" if b else "No"  # noqa: E731
            md(f"**Fit:** {f.band}  \n- Skills: {yn(f.skills)}. {f.reasons.get('skills', '')}  \n"
                        f"- Kind of work you do: {yn(f.work_type)}. {f.reasons.get('work_type', '')}  \n"
                        f"- Proof in your projects: {yn(f.proof)}  \n- Realistic for the budget: {yn(f.realistic)}. {f.reasons.get('realistic', '')}  \n"
                        f"- Clear enough to plan: {yn(f.clear)}. {f.reasons.get('clear', '')}")
            md(f"**Skill tags:** {f.skill_overlap}")
            asm = rec.assessment
            if asm and asm.votes > 1:
                md(f"**Confidence:** all {asm.votes} checks agreed" if not asm.split_facts else
                   f"**Confidence:** the {asm.votes} checks split on {', '.join(asm.split_facts)}; the majority answer is used")
        st.markdown(f"**Link check:** {LINK_STATUS.get(rec.job.link_status, rec.job.link_status)}")


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
    st.caption(f"{summary_line(rec)} · Draft {v.n}")
    recheck_result(rec)
    recheck_button(rec, "Check the fit now" if rec.decision.code == "unchecked" else "Check the fit again")

    projects = pipe.projects()
    labels = {l.project_id: l.label for l in (rec.assessment.project_labels if rec.assessment else [])}
    nice = {"similar": " · close match", "same_skills": " · same skills", "not_relevant": " · different work"}
    pname = {p.id: f"{p.title}{nice.get(labels.get(p.id), '')}" for p in projects}
    cited = [i for i in [v.project_id, *v.extra_project_ids] if i in pname]
    picked = st.multiselect("Proof: past projects to cite (up to 3; the first is the main one)", list(pname), default=cited,
                            format_func=lambda x: pname[x], max_selections=3, placeholder="None: plan only (no past project)",
                            key=f"proof_{rec.job_key}_{v.n}")
    if projects and any(p.id not in labels for p in projects):
        st.caption("Projects added after the fit check aren't rated yet. **Check the fit again** rates them.")
    if picked != cited and st.button("Rewrite with this proof", type="primary"):
        if run(pipe.write, rec, picked[0] if picked else None, "", picked[1:]):
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
    if val.ok and v.framing != "plan_only":
        st.markdown('<div class="quiet-ok">✓ Checked against your projects and the post</div>', unsafe_allow_html=True)
    else:
        st.warning("⚠️ Check before sending. These lines may claim something your Projects or the post don't back up:")
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
            md(f"**Goal:** {b.goal}")
            md("**Plan:**\n" + "\n".join(f"{i}. {s.step}" + (f" (suggested: {', '.join(s.suggested_tools)})" if s.suggested_tools else "") for i, s in enumerate(b.plan, 1)))
            md("**Milestones:**\n" + "\n".join(f"- {m.name}: {m.deliverable} {m.budget_share}" for m in b.milestones))
            md("**Risks:**\n" + "\n".join(f"- {r.risk} → {r.mitigation}" for r in b.risks))
            md("**Questions:**\n" + "\n".join(f"- {q}" for q in b.questions))
            md("**Assumptions:**\n" + "\n".join(f"- {a}" for a in b.assumptions))
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
                st.success(r[1])
                st.rerun()
    else:
        o = rec.outcome
        st.success(f"Sent {o.sent_at[:10]} · {o.minutes_paste_to_sent} min from paste to sent")
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
    if sent:
        st.download_button("Download sent log (CSV)", pipe.sent_log_csv(), file_name="sent-log.csv", mime="text/csv",
                           help="Every sent proposal with its decision, client trust, minutes and outcome. Opens in Excel or Google Sheets. "
                                "The live app's files reset when it restarts, so download it now and then.")
    for r in recs:
        with st.container(border=True, key="card_job_" + re.sub(r"\W", "_", r.job_key)):
            badge = " · ⏳ Still waiting?" if Pipeline.still_waiting(r) else ""
            outcome = f" · {r.outcome.result.replace('_', ' ')}" if r.outcome.result else ""
            st.markdown(f"**{r.job.title}**  \n{summary_line(r)} · {r.status.capitalize()}{outcome}{badge}")
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
        with st.container(border=True, key=f"card_proj_{i}"):
            st.caption("Suggested. Nothing is added until you confirm it.")
            p = ProposedProject.model_validate(pd)
            project_form(Project(id="new", **p.model_dump()), key=f"prop{i}", on_save=lambda i=i: ss.proposed.pop(i))
            if st.button("Discard", key=f"disc{i}"):
                ss.proposed.pop(i)
                st.rerun()


def next_project_id(ids: set[str]) -> str:
    return f"P{max([int(i[1:]) for i in ids if i[1:].isdigit()] + [0]) + 1}"


def project_form(p: Project | None, key: str, on_save=None) -> None:
    with st.form(f"proj_{key}", enter_to_submit=False):
        title = st.text_input("Title *", p.title if p else "")
        problem = st.text_area("Problem *", p.problem if p else "", placeholder="What was going wrong for the client, in one or two lines")
        did = st.text_area("What I did *", p.what_i_did if p else "", placeholder="What you built or changed, and with what")
        skills = st.text_input("Skills *", ", ".join(p.skills) if p else "", placeholder="Comma-separated, e.g. n8n, Python, Slack API")
        result = st.text_input("Result (optional)", p.result if p else "",
                               placeholder="e.g. cut manual entry from 2 hours a week to 10 minutes",
                               help="Only numbers and outcomes you can back up. Leave it empty rather than guess.")
        link = st.text_input("Link (optional)", (p.link or "") if p else "")
        roles = {"solo": "I did it on my own", "led": "I led it", "contributed": "I was part of a team"}
        role = st.selectbox("Your role *", list(roles), index=list(roles).index(p.role) if p else None,
                            format_func=roles.get, placeholder="Choose your role",
                            help="Sent to the draft with the project, so it can describe your part accurately.")
        if st.form_submit_button("Save"):
            missing = [n for n, v in (("Title", title), ("Problem", problem), ("What I did", did), ("Skills", skills),
                                      ("Your role", role or "")) if not v.strip()]
            if missing:
                st.error("Fill in " + ", ".join(missing) + ". v2 uses them to match this project to jobs and to write honest proof.")
                return
            ids = {x.id for x in pipe.projects()}
            pid = p.id if p and p.id in ids else next_project_id(ids)
            storage().put_project(uid, Project(id=pid, title=title.strip(), problem=problem, what_i_did=did,
                                               skills=[s.strip() for s in skills.split(",") if s.strip()], result=result,
                                               link=link or None, role=role, can_name_client=False))
            if on_save:
                on_save()
            st.rerun()


def page_settings() -> None:
    st.title("Settings")
    p = pipe.profile()
    cfg = load_config()["trust"]
    with st.form("settings", enter_to_submit=False):
        st.subheader("Minimum rates")
        h = st.number_input("Minimum hourly rate (USD)", min_value=0.0, value=float(p.min_hourly_usd or 0))
        f = st.number_input("Minimum fixed price (USD)", min_value=0.0, value=float(p.min_fixed_usd or 0))
        st.subheader("Your work")
        wt = st.text_input("Kinds of work you do", ", ".join(p.work_types), placeholder="e.g. workflow automation, AI chatbots, mobile apps", help="What you deliver, not the tools: v2 skips jobs that aren't one of these. Tools go under skills.")
        sk = st.text_input("Skills", ", ".join(p.skills))
        st.subheader("Client score cut-offs")
        st.caption("A score at or above the number gets the band. Below Low is a red flag.")
        cut = p.trust_cutoffs or {}
        c1, c2, c3, c4 = st.columns(4)
        ex = c1.number_input("Excellent", value=float(cut.get("excellent", cfg["excellent"])))
        hi = c2.number_input("High", value=float(cut.get("high", cfg["high"])))
        me = c3.number_input("Medium", value=float(cut.get("medium", cfg["medium"])))
        lo = c4.number_input("Low", value=float(cut.get("low", cfg["low"])))
        if st.form_submit_button("Save"):
            p.min_hourly_usd, p.min_fixed_usd = h, f
            p.work_types = [x.strip() for x in wt.split(",") if x.strip()]
            p.skills = [x.strip() for x in sk.split(",") if x.strip()]
            p.trust_cutoffs = {"excellent": ex, "high": hi, "medium": me, "low": lo}
            storage().put_profile(uid, p)
            st.success("Saved.")
    with st.expander("Delete all data in this workspace"):
        st.caption("Removes your jobs, drafts, projects and settings from this app. Download your sent log from My jobs first if you want to keep it.")
        if st.checkbox("I understand this can't be undone") and st.button("Delete everything"):
            storage().clear_user(uid)
            ss.screen, ss.job_key, ss.pending = "new", None, None
            st.rerun()


# =========================================================================== router
if is_sample:
    what = {"Settings": "These settings belong to a made-up sample freelancer, not you.",
            "Projects": "These projects belong to a made-up sample freelancer, not you.",
            "My jobs": "These are the sample freelancer's jobs, not yours."}.get(page, "You're trying v2 with sample data.")
    st.markdown(f'<div class="sample-banner"><b>Sample workspace.</b> {what} '
                f'Switch to <b>Mine</b> in the sidebar for your own.</div>', unsafe_allow_html=True)
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
