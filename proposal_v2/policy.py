"""Instruction policy. Job posts are untrusted input.

Format instructions are followed and checked; claim or identity requests are refused and
flagged; off-platform requests are trust red flags; instructions aimed at the AI are ignored
and logged. The LLM classifies instructions during extraction; these code rules back it up,
so the policy holds even when the model misses one.
"""
from __future__ import annotations

import re

from .contracts import PostInstruction, RedFlag

AI_DIRECTED = re.compile(
    r"(ignore (all |any |your |the )?(previous |prior |above )?(instructions|prompts?)|"
    r"(note|message|instruction)s? (to|for) (any |the )?(ai|chatgpt|assistant|llm|language model)|"
    r"\bas an ai\b|system prompt)",
    re.I,
)
OFF_PLATFORM = re.compile(
    r"(whats\s?app|telegram|signal app|skype|wechat|discord|text me at|e-?mail me at|call me at|"
    r"\+\d[\d\s-]{7,}|pay (outside|off) (of )?(upwork|the platform)|crypto|usdt|bitcoin)",
    re.I,
)
PAY_TO_APPLY = re.compile(r"(registration fee|application fee|pay a (small )?(fee|deposit)|deposit (of|to) )", re.I)
CLAIM_REQUEST = re.compile(
    r"(say|state|claim|mention|tell (us|me)) (that )?you (have|are|were|'ve)\b.*?(years?|experience|expert|certified|used|worked)",
    re.I,
)
STARTS_WITH = re.compile(
    r"(?:start|begin) your (?:proposal|application|cover letter|reply|bid|message) with (?:the (?:word|words|phrase) )?[\"“'‘](.+?)[\"”'’]",
    re.I,
)


def code_instructions(text: str) -> list[PostInstruction]:
    """Instructions found by regex, as a backstop for the LLM's list."""
    found: list[PostInstruction] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = sentence.strip()
        if not s:
            continue
        if AI_DIRECTED.search(s):
            found.append(PostInstruction(text=s, kind="ai_directed"))
        elif CLAIM_REQUEST.search(s):
            found.append(PostInstruction(text=s, kind="claim"))
        elif OFF_PLATFORM.search(s) and re.search(r"(message|contact|reach|chat|move|talk|send|add|pay)", s, re.I):
            found.append(PostInstruction(text=s, kind="off_platform"))
        m = STARTS_WITH.search(s)
        if m:
            found.append(PostInstruction(text=s, kind="format", check="starts_with", value=m.group(1).strip()))
    return found


def code_red_flags(text: str) -> list[RedFlag]:
    flags: list[RedFlag] = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        s = sentence.strip()
        if OFF_PLATFORM.search(s) and re.search(r"(message|contact|reach|chat|move|talk|send|add|pay)", s, re.I):
            flags.append(RedFlag(kind="off_platform", evidence=s))
        if PAY_TO_APPLY.search(s):
            flags.append(RedFlag(kind="pay_to_apply", evidence=s))
    return flags


def _same(a: PostInstruction, b: PostInstruction) -> bool:
    return a.kind == b.kind and (a.text.strip().lower() in b.text.strip().lower() or b.text.strip().lower() in a.text.strip().lower())


def apply_policy(llm_instructions: list[PostInstruction], llm_flags: list[RedFlag], description: str):
    """Merge LLM and code findings. Returns (allowed, refused, ignored, red_flags)."""
    merged: list[PostInstruction] = list(llm_instructions)
    for ins in code_instructions(description):
        if not any(_same(ins, m) for m in merged):
            # A code-found starts_with check upgrades an LLM format instruction that lacked one.
            upgraded = False
            for i, m in enumerate(merged):
                if ins.kind == "format" and m.kind == "format" and m.check == "other" and ins.value.lower() in m.text.lower():
                    merged[i] = m.model_copy(update={"check": "starts_with", "value": ins.value})
                    upgraded = True
            if not upgraded:
                merged.append(ins)
    allowed = [i for i in merged if i.kind == "format"]
    refused = [i for i in merged if i.kind == "claim"]
    ignored = [i for i in merged if i.kind == "ai_directed"]
    flags = list(llm_flags)
    for i in merged:
        if i.kind == "off_platform" and not any(f.kind == "off_platform" for f in flags):
            flags.append(RedFlag(kind="off_platform", evidence=i.text))
    for f in code_red_flags(description):
        if not any(x.kind == f.kind for x in flags):
            flags.append(f)
    return allowed, refused, ignored, flags
