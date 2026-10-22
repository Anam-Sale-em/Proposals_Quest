"""External integrations besides the LLMs: the user's Google Sheet, Freelancer.com's public
API and PDF text for CV import. Each failure returns a plain message instead of raising."""
from __future__ import annotations

import io
import json
import re
import time
from typing import Optional

from .config import load_config, secret
from .contracts import Budget, JobPost

# --------------------------------------------------------------------------- Google Sheet


class NoServiceAccount(Exception):
    pass


def gspread_client():
    """A gspread client from the service account in .env or st.secrets. Raises NoServiceAccount."""
    import gspread

    info = secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    path = secret("GOOGLE_SERVICE_ACCOUNT_FILE")
    if info:
        return gspread.service_account_from_dict(json.loads(info))
    if path:
        return gspread.service_account(filename=path)
    try:
        import streamlit as st

        return gspread.service_account_from_dict(dict(st.secrets["gcp_service_account"]))
    except Exception:
        raise NoServiceAccount("No Google service account is set.")


def append_sheet_row(sheet_url: str, row: list, header: Optional[list] = None) -> tuple[bool, str]:
    """Adds one row to the first tab of the user's own Sheet, writing the header first if the
    tab is empty. Returns (ok, message). Never raises."""
    if not sheet_url:
        return False, "No Google Sheet is set in Settings, so this send wasn't added to a Sheet."
    try:
        try:
            gc = gspread_client()
        except NoServiceAccount:
            return False, "The Google Sheet isn't connected (no service account set). The send is saved here."
        ws = gc.open_by_url(sheet_url).sheet1
        if header and not ws.acell("A1").value:
            ws.append_row(header)
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, "Added to your Google Sheet."
    except Exception as e:
        hint = "Share the Sheet with the app's service-account email as an editor." if "403" in str(e) or "PERMISSION" in str(e).upper() else "Check the Sheet link in Settings."
        return False, f"Couldn't reach your Google Sheet, so the send is saved here only. {hint}"


# --------------------------------------------------------------------------- Freelancer.com
API = "https://www.freelancer.com/api/projects/0.1"
_last_call = [0.0]


class FetchError(Exception):
    """Shown to the user as written."""


def _get(path: str, params: dict) -> dict:
    import requests

    per_min = load_config()["rate_limits"]["freelancer_api_per_minute"]
    wait = _last_call[0] + 60.0 / per_min - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=20)
    except Exception:
        raise FetchError("Couldn't reach Freelancer.com. Check your connection, or paste the job text instead.")
    if r.status_code == 429:
        raise FetchError("Freelancer.com is rate-limiting requests. Wait a minute and try again.")
    if r.status_code >= 400:
        raise FetchError("Freelancer.com didn't return this job. Paste the job text instead.")
    data = r.json()
    if data.get("status") != "success":
        raise FetchError("Freelancer.com didn't return this job. Paste the job text instead.")
    return data["result"]


def _money(v: float) -> str:
    return f"{v:,.0f}" if v == int(v) else f"{v:,.2f}"


def _to_jobpost(p: dict) -> JobPost:
    """Freelancer.com project -> JobPost. Non-USD budgets are converted with the API's own exchange rate."""
    budget = p.get("budget") or {}
    currency = p.get("currency") or {}
    cur = (currency.get("code") or "USD").upper()
    rate = 1.0 if cur == "USD" else currency.get("exchange_rate")
    lo, hi = budget.get("minimum"), budget.get("maximum")
    hourly = p.get("type") == "hourly"
    per = " per hour" if hourly else ""
    shown = " – ".join(_money(v) for v in (lo, hi) if v is not None)
    raw = f"{cur} {shown}{per}"
    if cur != "USD" and not rate:
        b = Budget(kind="none", raw_text=raw)
    else:
        lo_usd = round(lo * rate, 2) if lo is not None else None
        hi_usd = round(hi * rate, 2) if hi is not None else None
        if cur != "USD":
            raw += " (about $" + " – ".join(_money(round(v)) for v in (lo_usd, hi_usd) if v is not None) + ")"
        if hourly:
            b = Budget(kind="hourly", min_usd=lo_usd, max_usd=hi_usd or lo_usd, raw_text=raw)
        elif hi_usd and lo_usd and hi_usd != lo_usd:
            b = Budget(kind="fixed_range", min_usd=lo_usd, max_usd=hi_usd, raw_text=raw)
        else:
            b = Budget(kind="fixed", amount_usd=hi_usd or lo_usd, raw_text=raw)
    seo = p.get("seo_url") or str(p["id"])
    return JobPost(
        job_key=f"freelancer:{p['id']}", platform="freelancer", link=f"https://www.freelancer.com/projects/{seo}",
        source="fetch", title=p.get("title", ""), description=p.get("description") or p.get("preview_description", ""),
        budget=b, skills=[j.get("name", "") for j in (p.get("jobs") or [])], link_status="Fetched",
    )


def match_places(job: JobPost, keywords: list[str]) -> list[tuple[str, str]]:
    """(keyword, where) for each keyword the job mentions: "skills", "title" or "description"."""
    from .skills import mentioned_in

    out = []
    for k in (k.strip() for k in keywords):
        if not k:
            continue
        for where, text in (("skills", " | ".join(job.skills)), ("title", job.title), ("description", job.description)):
            if mentioned_in(k, text):
                out.append((k, where))
                break
    return out


def matched_keywords(job: JobPost, keywords: list[str]) -> list[str]:
    """Keywords found as a whole phrase in the job's skills, title or description."""
    from .skills import mentioned_in

    text = "\n".join([job.title, job.description, " | ".join(job.skills)])
    return [k for k in keywords if k.strip() and mentioned_in(k.strip(), text)]


def fetch_by_link(url: str) -> JobPost:
    m = re.search(r"freelancer\.[a-z.]+/projects/([^?#]+)", url)
    if not m:
        raise FetchError("v2 can only fetch Freelancer.com project links. For other platforms, paste the job text with its link.")
    seo = m.group(1).strip("/")
    num = re.search(r"(\d{5,})$", seo)
    if num:
        res = _get(f"/projects/{num.group(1)}/", {"full_description": "true", "job_details": "true"})
        projects = [res] if res else []
    else:
        res = _get("/projects/", {"seo_urls[]": seo, "full_description": "true", "job_details": "true"})
        projects = res.get("projects") or []
    if not projects:
        raise FetchError("Freelancer.com didn't return this job. Paste the job text instead.")
    p = projects[0]
    if (p.get("status") or "active") != "active" and (p.get("frontend_project_status") or "open") != "open":
        raise FetchError("This job is closed on Freelancer.com.")
    return _to_jobpost(p)


def search_jobs(keywords: list[str], exclude: list[str], budget_floor: Optional[float]) -> list[JobPost]:
    if not keywords:
        raise FetchError("Add at least one keyword.")
    # Freelancer.com's search matches single words loosely ("React Native" returns "Native Turkish
    # Translation"), so every result is re-checked here: a keyword must appear as a whole phrase.
    res = _get("/projects/active/", {"query": " ".join(keywords), "limit": 100, "full_description": "true",
                                     "job_details": "true", "sort_field": "time_updated"})
    jobs = []
    for p in sorted(res.get("projects") or [], key=lambda x: x.get("time_submitted", 0), reverse=True):
        j = _to_jobpost(p)
        if not matched_keywords(j, keywords):
            continue
        text = (j.title + " " + j.description).lower()
        if any(x.lower() in text for x in exclude if x.strip()):
            continue
        top = j.budget.max_usd or j.budget.amount_usd
        if budget_floor and top is not None and top < budget_floor:
            continue
        jobs.append(j)
    return jobs


# --------------------------------------------------------------------------- PDF text
def pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""
