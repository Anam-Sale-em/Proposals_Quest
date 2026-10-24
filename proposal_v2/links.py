"""Link parser, job key and the two-step link check. Pure code; nothing fetches the page."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from .config import load_config

STOP_WORDS = {"a", "an", "and", "the", "for", "to", "of", "in", "on", "with", "by", "or", "my", "our", "your", "is", "be", "at"}


class LinkError(Exception):
    """A step-1 error: blocks the form. The message is shown to the user as written."""


@dataclass
class ParsedLink:
    url: str
    platform: str
    host: str
    path: str
    job_key: str
    title_tokens: list[str]


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _platform_for(host: str) -> Optional[str]:
    for domain in load_config()["link_check"]["supported_domains"]:
        if host == domain or host.endswith("." + domain):
            return domain.split(".")[0]
    return None


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP_WORDS and not t.isdigit()]


def normalized_url(url: str) -> str:
    p = urlparse(url.strip())
    host = (p.hostname or "").lower()
    path = p.path.rstrip("/")
    return f"{host}{path}"


NOT_A_JOB = ("This looks like a search or profile page, not a job posting. Open the job, then use its Share button "
             "(top right of the job) → Copy link, and paste that link here.")


def parse_link(url: str) -> ParsedLink:
    """Step 1 of the link check. Raises LinkError with a user-facing message."""
    url = (url or "").strip()
    if not url:
        raise LinkError("Add the job's link.")
    if not re.match(r"^https?://", url):
        url = "https://" + url
    host = _host(url)
    platform = _platform_for(host)
    if not platform:
        raise LinkError("Paste the job's own page from a supported platform (Upwork, Freelancer.com, Guru, Fiverr or PeoplePerHour).")
    path = urlparse(url).path
    lower = path.lower()

    if platform == "upwork":
        m = re.search(r"~0[0-9a-z]+", path, re.I)
        if not m:
            raise LinkError(NOT_A_JOB)
        job_id = m.group(0).lower()
        slug = ""
        sm = re.search(r"/([^/]+)_~0", path)
        if sm:
            slug = sm.group(1)
        if re.search(r"/(freelancers|o/profiles|agencies)/", lower):
            raise LinkError(NOT_A_JOB)
        return ParsedLink(url, platform, host, path, f"upwork:{job_id}", _tokens(slug))

    if platform == "freelancer":
        if re.search(r"/(u|search|jobs|freelancers)(/|$)", lower) and not lower.startswith("/projects/"):
            raise LinkError(NOT_A_JOB)
        if not lower.startswith("/projects/"):
            raise LinkError(NOT_A_JOB)
        parts = [p for p in path.split("/") if p]
        slug = parts[-1] if len(parts) >= 2 else ""
        num = re.search(r"(\d{5,})", slug)
        key = num.group(1) if num else slug.lower()
        if not key:
            raise LinkError(NOT_A_JOB)
        return ParsedLink(url, platform, host, path, f"freelancer:{key}", _tokens(re.sub(r"\d{5,}", "", slug)))

    if platform == "guru":
        m = re.search(r"/(\d{4,})(?:/|$|[^0-9])", path)
        if "/freelancers" in lower or "/d/jobs" in lower and not m:
            raise LinkError(NOT_A_JOB)
        if not m:
            raise LinkError(NOT_A_JOB)
        parts = [p for p in path.split("/") if p and not p.isdigit()]
        slug = parts[-1] if parts and parts[-1] not in {"work", "detail", "jobs"} else ""
        return ParsedLink(url, platform, host, path, f"guru:{m.group(1)}", _tokens(slug))

    if platform == "peopleperhour":
        if "/freelance-jobs" not in lower:
            raise LinkError(NOT_A_JOB)
        parts = [p for p in path.split("/") if p]
        last = parts[-1] if parts else ""
        m = re.search(r"-(\d{4,})$", last)
        if not m:
            raise LinkError(NOT_A_JOB)
        return ParsedLink(url, platform, host, path, f"peopleperhour:{m.group(1)}", _tokens(last[: m.start()]))

    # fiverr and anything else supported: normalized URL; no title words to check
    if re.search(r"/(search|categories)(/|$)", lower):
        raise LinkError(NOT_A_JOB)
    return ParsedLink(url, platform, host, path, f"{platform}:{normalized_url(url)}", [])


def title_match(parsed: ParsedLink, title: str) -> str:
    """Step 2, after extraction. Never blocks. Returns Matched, Warned or Unchecked."""
    if not parsed.title_tokens:
        return "Unchecked"
    title_tokens = set(_tokens(title))
    share = sum(t in title_tokens for t in parsed.title_tokens) / len(parsed.title_tokens)
    threshold = load_config()["link_check"]["title_match_threshold"]
    return "Matched" if share >= threshold else "Warned"


LINK_WARNING = "The link and the details may be different jobs."
