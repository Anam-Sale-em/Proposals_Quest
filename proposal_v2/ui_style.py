"""The app's look: one font (Figtree), a calm slate-and-harbor palette, and the verdict card,
the one bold element on screen. Everything else stays quiet."""
from __future__ import annotations

from html import escape

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&display=swap');

:root {
  --ink: #1D2B36;
  --ink-soft: #4F5F6B;
  --paper: #F5F7F6;
  --card: #FFFFFF;
  --line: #DCE4E8;
  --harbor: #22577A;
  --harbor-deep: #183F59;
  --apply: #2F7D6B;      --apply-bg: #E3F2EC;
  --ask: #A86F12;        --ask-bg: #FBF0D9;
  --skip: #A8434E;       --skip-bg: #F8E5E7;
  --neutral: #5A6B78;    --neutral-bg: #EBF0F3;
}

html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button, h1, h2, h3, h4 {
  font-family: 'Figtree', system-ui, sans-serif;
}
.stApp { background: var(--paper); color: var(--ink); }
.block-container { max-width: 760px; padding-top: 2.5rem; }

.stApp h1 { font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; font-size: 1.85rem; }
h2, h3 { font-weight: 700; letter-spacing: -0.01em; color: var(--ink); }
p, li { line-height: 1.6; }
[data-testid="stCaptionContainer"] { color: var(--ink-soft); }

/* Sidebar: a quiet tinted panel */
[data-testid="stSidebar"] { background: #E9EFF2; border-right: 1px solid var(--line); }

/* Inputs: white fields with a clear edge, harbor focus ring */
.stTextInput input, .stTextArea textarea, .stNumberInput input, [data-baseweb="select"] > div {
  background: var(--card) !important; border-radius: 10px !important;
}
.stTextInput > div > div, .stTextArea > div > div, .stNumberInput > div > div {
  border: 1px solid var(--line); border-radius: 10px;
}
.stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {
  border-color: var(--harbor); box-shadow: 0 0 0 3px rgba(34, 87, 122, .15);
}

/* Buttons: primary is solid harbor, secondary is a calm outline */
.stButton button, .stLinkButton a, .stDownloadButton button, [data-testid="stSidebar"] .stButton button {
  border-radius: 999px; font-weight: 600; padding: .45rem 1.15rem;
  border: 1px solid var(--line); background: var(--card); color: var(--ink);
}
.stButton button:hover, .stLinkButton a:hover { border-color: var(--harbor); color: var(--harbor); }
.stButton button[kind="primary"] { background: var(--harbor); border-color: var(--harbor); color: #fff; }
.stButton button[kind="primary"]:hover { background: var(--harbor-deep); color: #fff; }
.stButton button:focus-visible, .stLinkButton a:focus-visible { outline: 3px solid rgba(34, 87, 122, .35); outline-offset: 2px; }

/* Bordered containers (job cards, My jobs rows) */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--card); border-color: var(--line) !important; border-radius: 14px;
}
[data-testid="stExpander"] details { background: var(--card); border-color: var(--line); border-radius: 12px; }

/* Alerts: softer, rounded, no heavy fills */
[data-testid="stAlert"] { border-radius: 12px; }

/* The verdict card: the one bold thing */
.verdict {
  background: var(--card); border: 1px solid var(--line); border-left: 8px solid var(--tone);
  border-radius: 16px; padding: 1.35rem 1.5rem 1.2rem; margin: .4rem 0 1.1rem;
}
.verdict .word { font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; color: var(--tone); line-height: 1.1; }
.verdict .why { margin: .45rem 0 .9rem; color: var(--ink); font-size: 1.05rem; line-height: 1.55; }
.verdict .facts { display: flex; flex-wrap: wrap; gap: .5rem; }
.chip {
  display: inline-flex; align-items: center; gap: .4rem; font-size: .9rem; font-weight: 600;
  padding: .3rem .75rem; border-radius: 999px; background: var(--tone-bg); color: var(--ink);
}
.meter { display: inline-flex; gap: 3px; }
.meter i { width: 9px; height: 9px; border-radius: 50%; background: #CBD5DB; display: inline-block; }
.meter i.on { background: var(--tone); }
.note { margin-top: .85rem; color: var(--ink-soft); font-size: .95rem; }

.quiet-ok { color: var(--apply); font-weight: 600; font-size: .92rem; margin: .2rem 0 .6rem; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""

TONES = {
    "apply": ("var(--apply)", "var(--apply-bg)"),
    "apply_with_questions": ("var(--ask)", "var(--ask-bg)"),
    "skip": ("var(--skip)", "var(--skip-bg)"),
    "unchecked": ("var(--neutral)", "var(--neutral-bg)"),
}
BAND_DOTS = {"Red flag": 0, "Low": 1, "Medium": 2, "High": 3, "Excellent": 4}


def trust_chip(trust) -> str:
    if trust is None or trust.score is None:
        return '<span class="chip">Client trust: unknown</span>'
    on = BAND_DOTS.get(trust.band, 0)
    dots = "".join(f'<i class="{"on" if i < on else ""}"></i>' for i in range(4))
    return f'<span class="chip">Client trust: {escape(trust.band)} <span class="meter">{dots}</span> {trust.score}/100</span>'


def verdict_html(word: str, tone_key: str, why: str, chips: list[str], note: str = "") -> str:
    # The reason often repeats the decision ("Apply: high fit..."); the big word already says it.
    head = word.split(" (")[0].lower()
    if why.lower().startswith(head + ":"):
        why = why[len(head) + 1:].strip()
        why = why[:1].upper() + why[1:]
    tone, bg = TONES.get(tone_key, TONES["unchecked"])
    facts = "".join(chips)
    note_html = f'<div class="note">{escape(note)}</div>' if note else ""
    return (f'<div class="verdict" style="--tone:{tone};--tone-bg:{bg}">'
            f'<div class="word">{escape(word)}</div><div class="why">{escape(why)}</div>'
            f'<div class="facts">{facts}</div>{note_html}</div>')


def chip(text: str) -> str:
    return f'<span class="chip">{escape(text)}</span>'
