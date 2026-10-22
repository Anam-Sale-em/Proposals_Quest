"""Skill names: normalization, aliases and overlap."""
from __future__ import annotations

import re
from typing import Iterable

from .config import load_config


def norm(name: str) -> str:
    n = re.sub(r"\s+", " ", (name or "").strip().lower())
    n = n.replace("’", "'")
    aliases = load_config()["skills"]["aliases"]
    return aliases.get(n, n)


def norm_set(names: Iterable[str]) -> set[str]:
    return {norm(n) for n in names if n and n.strip()}


def overlap(required: Iterable[str], have: Iterable[str]) -> tuple[int, int, list[str]]:
    req = norm_set(required)
    got = norm_set(have)
    matched = sorted(r for r in req if r in got or any(r in g or g in r for g in got if len(g) > 2))
    return len(matched), len(req), matched


def overlap_text(required: Iterable[str], have: Iterable[str]) -> str:
    n, total, _ = overlap(required, have)
    if total == 0:
        return "The post lists no skills"
    return f"{n} of {total} required skills"


def mentioned_in(name: str, text: str) -> bool:
    """True when the tool name appears in the text as whole words."""
    n = norm(name)
    t = text.lower()
    if re.search(r"(?<![a-z0-9])" + re.escape(n) + r"(?![a-z0-9])", t):
        return True
    raw = (name or "").strip().lower()
    return bool(raw) and re.search(r"(?<![a-z0-9])" + re.escape(raw) + r"(?![a-z0-9])", t) is not None
