# Failure analysis

Real failures found while running v2, each with its root cause, the fix and how the fix is checked. Day 4 needs at least three.

## F1 · First live run: every model failed · 2026-10-22

**What happened:** the first real Upwork job pasted into the live app (a React Native B2B SaaS app, hourly $25–$40) stopped at extraction with "The AI service didn't respond properly after retrying both providers".

**Evidence (the error shown in the app):**
- Gemini 3.5 Flash-Lite: `503 UNAVAILABLE`, "This model is currently experiencing high demand".
- Groq fallback `llama-3.3-70b-versatile`: `404`, "does not exist or you do not have access to it".

**Root cause:** two faults stacked.
1. A Gemini 503 is temporary, but v2 treated it like a hard failure and gave up on Gemini after one try.
2. The fallback was a single Groq model name, which wasn't available to this key even though Groq's model page lists it as a production model. One unchecked name was a single point of failure.

**Fix (prompt_version unchanged; code only):**
- Busy or rate-limited Gemini calls (429, 500, 502, 503, 504) are retried after 3 s and 8 s, then the other Gemini model is tried, then each Groq model in `fallbacks`, in order. A model that doesn't exist is skipped, not retried.
- When everything is busy, the message now says so in plain words ("The AI models are busy right now…"), separately from key or model problems.
- `scripts/check_models.py` lists which configured models each key can use, without spending generation quota.

**How it's checked:** two new tests. One simulates a 503 on both Gemini models and a 404 on the first Groq model, and asserts the exact order tried before the second Groq model answers. The other asserts the "busy" message when every model is busy. Rerun of the same job on the live app: _to fill in_.

**Lesson:** fallbacks need their own check at startup, not just a name in config.

## F2 · A portfolio request was refused as a "claim" · 2026-10-22

**What happened:** on the same React Native job, the confirm screen listed "Please share 1–2 React Native applications you've built…" under **Won't follow (asks you to claim something)**.

**Root cause:** the extraction prompt defined a claim instruction as "asking the applicant to state something about their experience or identity". That's broad enough to cover an ordinary request for past work, so the model filed it with "say you have 10 years of experience". Refused instructions are left out of the draft, so the proposal would have ignored what the client asked for. That would fail rubric item 1 (covers every explicit requirement).

**Fix (prompt_version v2.0.0 → v2.0.1):** a claim instruction is now only an order to assert a specific fact whatever the truth. Requests to share, show, link or describe past work go to `explicit_requirements`, which the draft answers from the user's real projects.

**How it's checked:** T11 (the "10 years" instruction) must still be refused; this job's portfolio request must land in explicit requirements. Rerun on the live app and the eval set: _to fill in_.

**Lesson:** a safety rule written too broadly blocks legitimate asks. Policy definitions need a counter-example as well as an example.
