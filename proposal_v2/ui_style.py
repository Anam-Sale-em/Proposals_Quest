"""The app's look: one font (Figtree), a calm slate-and-harbor palette, and the verdict card,
the one bold element on screen. Everything else stays quiet."""
from __future__ import annotations

from html import escape

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&display=swap');

:root {
  --ink: #1B2B38;
  --ink-soft: #566876;
  --paper: #EEF3F5;
  --sheet: #FFFFFF;
  --tint: #F6F9FA;
  --line: #DDE6EA;
  --harbor: #22577A;
  --harbor-deep: #173A50;
  --mint: #7FD1B9;
  --apply: #2F7D6B;      --apply-bg: #E3F2EC;
  --ask: #A86F12;        --ask-bg: #FBF0D9;
  --skip: #A8434E;       --skip-bg: #F8E5E7;
  --neutral: #5A6B78;    --neutral-bg: #EBF0F3;
  --lift: 0 1px 2px rgba(23, 58, 80, .06), 0 10px 30px rgba(23, 58, 80, .07);
}

/* One friendly font everywhere (icons keep their own font) */
.stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stHeading"] * , .stApp [data-baseweb="tab"] {
  font-family: 'Figtree', system-ui, -apple-system, sans-serif !important;
}
.stApp { background: var(--paper); color: var(--ink); }

/* Streamlit chrome off: no Deploy button, menu or footer */
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer { display: none !important; }
/* No link icon next to headings */
[data-testid="stHeaderActionElements"], .stApp h1 a, .stApp h2 a, .stApp h3 a { display: none !important; }

/* The page sits on one white sheet */
.block-container {
  max-width: 820px; background: var(--sheet); border-radius: 22px; box-shadow: var(--lift);
  padding: 2.2rem 3rem 3rem !important; margin: 1.6rem auto 3rem;
}
@media (max-width: 760px) { .block-container { padding: 1.6rem 1.1rem 2rem !important; margin: .8rem .5rem; border-radius: 16px; } }

.stApp h1 { font-weight: 800; letter-spacing: -0.025em; line-height: 1.15; font-size: 2rem; color: var(--ink); padding-bottom: .2rem; }
.stApp h2, .stApp h3 { font-weight: 700; letter-spacing: -0.012em; color: var(--ink); }
.stApp h3 { font-size: 1.2rem; margin-top: .6rem; }
.stApp p, .stApp li { line-height: 1.6; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--ink-soft) !important; }
hr { border-color: var(--line) !important; }

/* Sidebar: a calm deep-harbor panel */
[data-testid="stSidebar"] { background: var(--harbor-deep); border-right: none; }
[data-testid="stSidebar"] * { color: #DCE7ED; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: #93ABBA !important; font-size: .82rem; font-weight: 600; letter-spacing: .01em;
}
[data-testid="stSidebar"] svg { fill: #93ABBA; }
.brand { display: flex; align-items: center; gap: .7rem; margin: .2rem 0 1.6rem; }
.brand .mark {
  width: 38px; height: 38px; border-radius: 11px; background: var(--mint); color: var(--harbor-deep) !important;
  display: grid; place-items: center; font-weight: 800; font-size: 1.15rem;
}
.brand .name { font-weight: 800; font-size: 1.08rem; color: #FFFFFF !important; line-height: 1.15; }
.brand .sub { font-size: .82rem; color: #93ABBA !important; }

/* Sidebar radios become a menu: full-width rows, the chosen one highlighted */
[data-testid="stSidebar"] [data-testid="stRadioGroup"] { gap: 2px; width: 100%; align-items: stretch; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div { width: 100%; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] {
  display: flex; width: 100%; box-sizing: border-box; padding: .55rem .8rem; border-radius: 10px; margin: 0; cursor: pointer;
}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display: none !important; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background: rgba(255, 255, 255, .06); }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
  background: rgba(127, 209, 185, .16); box-shadow: inset 3px 0 0 var(--mint);
}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p { color: #FFFFFF !important; font-weight: 700; }
[data-testid="stSidebar"] .stButton button {
  background: rgba(255, 255, 255, .08) !important; border: 1px solid rgba(255, 255, 255, .16) !important; color: #FFFFFF !important;
}
[data-testid="stSidebar"] .stButton button:hover { background: rgba(255, 255, 255, .14) !important; }

/* Tabs as a soft segmented control */
.stTabs [role="tablist"] { background: var(--paper); padding: 4px; border-radius: 12px; gap: 4px; border: none; }
.stTabs [role="tab"] { border-radius: 9px !important; padding: .45rem .95rem !important; height: auto !important; border: none !important; }
.stTabs [role="tab"] p { font-weight: 600; color: var(--ink-soft); }
.stTabs [role="tab"][aria-selected="true"] { background: var(--sheet) !important; box-shadow: 0 1px 3px rgba(23, 58, 80, .14); }
.stTabs [role="tab"][aria-selected="true"] p { color: var(--harbor-deep); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none !important; }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input, [data-baseweb="select"] > div {
  background: var(--tint) !important; border-radius: 12px !important; color: var(--ink);
}
.stTextInput > div > div, .stTextArea > div > div, .stNumberInput > div > div, [data-baseweb="select"] > div {
  border: 1px solid var(--line) !important; border-radius: 12px !important;
}
.stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {
  border-color: var(--harbor) !important; box-shadow: 0 0 0 3px rgba(34, 87, 122, .14);
}

/* Buttons */
.stButton button, .stLinkButton a, .stDownloadButton button, .stFormSubmitButton button {
  border-radius: 999px; font-weight: 600; padding: .5rem 1.2rem;
  border: 1px solid var(--line); background: var(--sheet); color: var(--ink);
}
.stButton button:hover, .stLinkButton a:hover, .stDownloadButton button:hover { border-color: var(--harbor); color: var(--harbor); }
.stButton button[kind="primary"], .stFormSubmitButton button[kind="primaryFormSubmit"] {
  background: var(--harbor); border-color: var(--harbor); color: #fff;
}
.stButton button[kind="primary"]:hover { background: var(--harbor-deep); color: #fff; }
.stButton button:focus-visible, .stLinkButton a:focus-visible { outline: 3px solid rgba(34, 87, 122, .35); outline-offset: 2px; }

/* Bordered blocks, expanders, metrics: tinted panels inside the white sheet */
[class*="st-key-card_"] {
  background: var(--tint); border: 1px solid var(--line) !important; border-radius: 16px; padding: 1.1rem 1.2rem !important;
}
[data-testid="stExpander"] details { background: var(--tint); border: 1px solid var(--line); border-radius: 14px; }
[data-testid="stExpander"] summary p { font-weight: 600; }
[data-testid="stMetric"] { background: var(--tint); border: 1px solid var(--line); border-radius: 14px; padding: .8rem 1rem; }
[data-testid="stMetricValue"] { font-weight: 800; color: var(--harbor-deep); }
[data-testid="stAlert"] { border-radius: 14px; }
[data-testid="stCheckbox"] label p { font-weight: 500; }

/* The verdict card: the one bold thing on the page */
.verdict {
  background: var(--sheet); border: 1px solid var(--line); border-left: 8px solid var(--tone);
  border-radius: 18px; padding: 1.4rem 1.6rem 1.25rem; margin: .5rem 0 1.2rem; box-shadow: var(--lift);
}
.verdict .word { font-size: 2.1rem; font-weight: 800; letter-spacing: -0.025em; color: var(--tone); line-height: 1.1; }
.verdict .why { margin: .45rem 0 .95rem; color: var(--ink); font-size: 1.06rem; line-height: 1.55; }
.verdict .facts { display: flex; flex-wrap: wrap; gap: .5rem; }
.chip {
  display: inline-flex; align-items: center; gap: .45rem; font-size: .9rem; font-weight: 600;
  padding: .32rem .8rem; border-radius: 999px; background: var(--tone-bg); color: var(--ink);
}
.meter { display: inline-flex; gap: 3px; }
.meter i { width: 9px; height: 9px; border-radius: 50%; background: #CBD5DB; display: inline-block; }
.meter i.on { background: var(--tone); }
.note { margin-top: .9rem; color: var(--ink-soft); font-size: .95rem; }

.quiet-ok { color: var(--apply); font-weight: 600; font-size: .92rem; margin: .2rem 0 .6rem; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""

BRAND = """<div class="brand"><div class="mark">P</div>
<div><div class="name">Proposal Pipeline</div><div class="sub">Check the job, then write</div></div></div>"""


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
