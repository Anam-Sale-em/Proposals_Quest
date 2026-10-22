# From v1 to v2

v1 was built for an agency's sales format: every job a person chose got a proposal built around a generated sample case study, plus visuals. v2 is built for a solo freelancer: it decides first, cites only the freelancer's real projects, and leaves every judgment call visible. These are planned changes; Day 4 measures each one.

| Area | v1 (previous way) | v2 (planned) | How it's checked |
| --- | --- | --- | --- |
| Getting the job in | 10 fields copied by hand | A link (official API), a keyword pick or one paste; the LLM extracts and I confirm | Manual input per job; T03, T07 |
| Choosing jobs | By a person, about 5 min per job; every job got a full draft | Four yes/no fit questions and a fit × trust table in code: Apply, Apply with questions or Skip | Skip accuracy on fresh Day 4 jobs; T04, T08, T09 |
| Client trust | Judged by a person before entry | A 0–100 score from hiring and payment history, plus red flags spotted in the post | 16 worked examples; agreement with my trust calls on fresh Day 4 jobs; T03, T10 |
| Duplicates | Checked by hand | One record per job, keyed on the job's ID | T12 |
| Proof | A sample case study generated for each job (agency sales format) | A Solution Brief for this job, plus real projects only, framed honestly (similar, same skills, or plan only) | Rubric item 3; T01, T02 |
| Claims | No check needed for the agency format | A three-part claim check (numbers, names, past-work sentences), one retry, then "needs review" | Hand-labeled claims on every draft |
| Instructions inside posts | Handled by the person reviewing | Format instructions followed; claim or identity requests refused and flagged; off-platform requests red-flagged; instructions aimed at the AI ignored and logged | T05, T10, T11 |
| Unclear posts | Handled by a person before entry | Apply with questions: a short draft that leads with scoping questions | T04 |
| Revisions | 2–3 rounds of 20+ min per job; a comment rewrote the whole proposal and all 36 frame prompts | Rewrites only what the comment asks | Checked by hand on a revised draft |
| Step contracts | Each prompt and parser defined separately, so they could drift apart | One Pydantic schema per step, shared by prompt, parser and validator, failing loudly | Schema-failure rate in the run log |
| Visuals | 36 frames, 120+ min and paid credits per approved proposal | None: text only | Non-goal |
| Secrets | Kept in n8n node settings; a signed token for each Firestore call | `.env` locally, `st.secrets` in the cloud, official SDKs | The example config holds no secrets |
| Length | No check | A length validator per platform | T06 |
| Outcomes | Not tracked | Mark as sent logs the time and adds a row to my Google Sheet; one-tap outcome; "Still waiting?" after 7 days | Two-week adoption metrics |
| Evaluation | Tested by hand on 100+ real jobs | 12 frozen test cases, a 5-item rubric, a plain-ChatGPT and v1 baseline, and run logs keyed by prompt version | This package |
| Model | Gemini 3.5 Flash | Gemini 3.8 Flash for the brief and draft; 3.5 Flash-Lite, still offered, for extraction and assessment; Groq as fallback | Model comparison on the 12 cases |

Kept from v1: comment-driven revision (now targeted) and structured output on every LLM step.
