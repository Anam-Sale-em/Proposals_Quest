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

/* Sidebar: a slim deep-harbor panel */
[data-testid="stSidebar"] { background: var(--harbor-deep); border-right: none; }
section[data-testid="stSidebar"] { width: 276px !important; min-width: 276px !important; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"], [data-testid="stSidebar"] [data-testid="stElementContainer"],
[data-testid="stSidebar"] [data-testid="stRadio"], [data-testid="stSidebar"] [data-testid="stRadio"] > div,
[data-testid="stSidebar"] .stButton { width: 100% !important; max-width: 100% !important; }
[data-testid="stSidebarHeader"] { height: 2.4rem; padding: .6rem 1rem 0; }
[data-testid="stSidebarUserContent"] { padding: .2rem 1.1rem 1.5rem !important; }
[data-testid="stSidebar"] * { color: #DCE7ED; }
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color: #8FA7B6 !important; font-size: .78rem; font-weight: 600; letter-spacing: .02em;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] { margin-bottom: .35rem; }
[data-testid="stSidebar"] svg { fill: #8FA7B6; }
.brand { display: flex; align-items: center; gap: .65rem; margin: 0 0 1.4rem; padding-bottom: 1.1rem;
         border-bottom: 1px solid rgba(255, 255, 255, .08); }
.brand .mark {
  width: 34px; height: 34px; border-radius: 10px; background: var(--mint); color: var(--harbor-deep) !important;
  display: grid; place-items: center; font-weight: 800; font-size: 1.05rem; flex: none;
}
.brand .name { font-weight: 800; font-size: 1rem; color: #FFFFFF !important; line-height: 1.2; white-space: nowrap; }
.brand .sub { font-size: .78rem; color: #8FA7B6 !important; white-space: nowrap; }

/* Workspace: a two-way switch */
.st-key-workspace [data-testid="stRadioGroup"] {
  display: grid !important; grid-template-columns: 1fr 1fr; gap: 3px; padding: 3px;
  background: rgba(0, 0, 0, .22); border-radius: 10px; width: 100%;
}
.st-key-workspace [data-testid="stRadioOption"] {
  justify-content: center; padding: .38rem .5rem !important; border-radius: 8px; margin: 0 !important; cursor: pointer;
}
.st-key-workspace [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display: none !important; }
.st-key-workspace [data-testid="stRadioOption"] p { font-size: .88rem; font-weight: 600; color: #A9BDC9 !important; }
.st-key-workspace [data-testid="stRadioOption"][data-selected="true"] { background: rgba(255, 255, 255, .14); }
.st-key-workspace [data-testid="stRadioOption"][data-selected="true"] p { color: #FFFFFF !important; }

/* Menu: full-width rows with icons, the current page highlighted */
.st-key-page { margin-top: .4rem; }
.st-key-page [data-testid="stRadioGroup"] { display: flex !important; flex-direction: column; align-items: stretch; gap: 2px; width: 100%; }
.st-key-page [data-testid="stRadioGroup"] > div, .st-key-page [data-testid="stRadioOption"] { width: 100% !important; }
.st-key-page [data-testid="stRadioOption"] {
  display: flex; box-sizing: border-box; padding: .5rem .7rem !important; border-radius: 9px; margin: 0 !important; cursor: pointer;
}
.st-key-page [data-testid="stRadioOption"] > div { width: 100%; }
.st-key-page [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display: none !important; }
.st-key-page [data-testid="stRadioOption"] p { font-size: .95rem; font-weight: 500; display: flex; align-items: center; }
.st-key-page [data-testid="stRadioOption"] [data-testid="stIconMaterial"] { font-size: 1.15rem; color: #8FA7B6 !important; }
.st-key-page [data-testid="stRadioOption"]:hover { background: rgba(255, 255, 255, .06); }
.st-key-page [data-testid="stRadioOption"][data-selected="true"] { background: rgba(127, 209, 185, .15); }
.st-key-page [data-testid="stRadioOption"][data-selected="true"] p { color: #FFFFFF !important; font-weight: 700; }
.st-key-page [data-testid="stRadioOption"][data-selected="true"] [data-testid="stIconMaterial"] { color: var(--mint) !important; }

[data-testid="stSidebar"] .stButton button {
  width: 100%; background: rgba(255, 255, 255, .07) !important; border: 1px solid rgba(255, 255, 255, .14) !important;
  color: #FFFFFF !important; border-radius: 9px !important; padding: .42rem .8rem !important; font-size: .9rem;
}
[data-testid="stSidebar"] .stButton button:hover { background: rgba(255, 255, 255, .13) !important; }
[data-testid="stSidebar"] [data-testid="stAlert"] { padding: .5rem .7rem; font-size: .88rem; }

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

.sample-banner {
  background: #FBF0D9; color: #6B4A0E; border: 1px solid #F0DDB2; border-radius: 12px;
  padding: .55rem .9rem; font-size: .92rem; margin: -0.6rem 0 1rem;
}
.sample-banner b { color: #6B4A0E; }

/* The "working" line: easy to spot while v2 calls the model */
[data-testid="stSpinner"] {
  background: #E9F2F6; border: 1px solid #CFE0E8; border-radius: 12px; padding: .7rem 1rem; margin: .4rem 0 .8rem;
  width: 100% !important;
}
[data-testid="stSpinner"] p, [data-testid="stSpinner"] div { color: var(--harbor-deep) !important; font-weight: 600; }

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
        return '<span class="chip">Client trust: can\'t rate, no details shared</span>'
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
