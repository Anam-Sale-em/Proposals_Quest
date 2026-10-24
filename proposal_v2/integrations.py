"""External integrations besides the LLMs: Freelancer.com's public API and PDF text for CV import.
Each failure becomes a plain message for the user."""
from __future__ import annotations

import io
import re
import time
from typing import Optional

from .config import load_config
from .contracts import Budget, JobPost

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
        raise FetchError("Freelancer.com didn't return this job. Copy the link from the project's Share button (top right) → Copy link and try again, or use Paste a job instead.")
    data = r.json()
    if data.get("status") != "success":
        raise FetchError("Freelancer.com didn't return this job. Copy the link from the project's Share button (top right) → Copy link and try again, or use Paste a job instead.")
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


def match_snippet(keyword: str, text: str, width: int = 60) -> str:
    """The words around the first whole-phrase mention of the keyword, e.g. "…maintain workflows in n8n (lead pulls…"."""
    m = re.search(r"(?<![A-Za-z0-9])" + re.escape(keyword.strip()) + r"s?(?![A-Za-z0-9])", text or "", re.I)
    if not m:
        return ""
    a, b = max(0, m.start() - width), min(len(text), m.end() + width)
    snip = " ".join(text[a:b].split())
    return ("…" if a > 0 else "") + snip + ("…" if b < len(text) else "")


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
        raise FetchError("This isn't a Freelancer.com project link. Open the project, click Share (top right), then Copy link and paste it here. For other platforms, use Paste a job.")
    seo = re.sub(r"/(details|proposals|overview|payments|files|reviews)$", "", m.group(1).strip("/"), flags=re.I)
    num = re.search(r"(\d{5,})$", seo)
    if num:
        res = _get(f"/projects/{num.group(1)}/", {"full_description": "true", "job_details": "true"})
        projects = [res] if res else []
    else:
        res = _get("/projects/", {"seo_urls[]": seo, "full_description": "true", "job_details": "true"})
        projects = res.get("projects") or []
    if not projects:
        raise FetchError("Freelancer.com didn't return this job. Copy the link from the project's Share button (top right) → Copy link and try again, or use Paste a job instead.")
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
    return filter_projects(res.get("projects") or [], keywords, exclude, budget_floor)


def filter_projects(projects: list[dict], keywords: list[str], exclude: list[str], budget_floor: Optional[float]) -> list[JobPost]:
    """Newest first; keeps jobs that mention a keyword, drops excluded terms and budgets under the floor."""
    jobs = []
    for p in sorted(projects, key=lambda x: x.get("time_submitted", 0), reverse=True):
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
