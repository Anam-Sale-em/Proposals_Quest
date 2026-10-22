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

## F3 · A plan-only draft ignored the client's request for past work · 2026-10-22

**What happened:** the React Native job asked applicants to "share 1–2 React Native applications you've built". The draft named no app and said the offline and API work was "new for me".

**Root cause:** the Projects library was empty, so v2 wrote a plan-only draft. That's correct, because it must never invent proof. But nothing told the user that the draft had no proof, or that it skipped an explicit request. The Solution Brief was fine; the gap was between the library and the draft, and it was silent.

**Fix:** the draft screen now warns when no project is cited, names any request for past work it couldn't answer, and says how to fix it (add the project, pick it under Proof, Rewrite with this proof).

**How it's checked:** an app test opens an empty workspace, writes a draft and asserts the warning. Rerun on the live app with projects added: _to fill in_.

**Lesson:** a safe default (no invented proof) still needs to be visible. Silent safety reads as a weak draft.

## F4 · The claim check flagged "API" on a post that asks for REST APIs · 2026-10-22

**What happened:** the React Native draft was marked "needs review" with "the draft mentions API, which isn't in your skills, your project or the post", although the post says "Integrate the app with our existing REST APIs".

**Root cause:** two gaps in the names pass. It matched whole words only, so "API" didn't match "APIs". It also treated generic words as tools, so "API" was checked like "Salesforce" would be.

**Fix:** names now match singular or plural, and a list of generic words in `config.toml` (API, app, UI, backend, database and others) is skipped by the names pass. Specific tools are still checked.

**How it's checked:** a unit test asserts "API" matches "APIs", generic words pass, and "Salesforce" is still treated as a tool. Rerun on the live app: _to fill in_.

**Lesson:** false alarms cost trust as much as misses. A "needs review" on an honest draft trains the user to ignore the check.

## F5 · The claim check flagged the draft's own honest "new for me" sentence · 2026-10-22

**What happened:** a plan-only draft said "This entire workflow setup is new for me, and here is how I would de-risk it: I will verify API access credentials…". The claim check marked it "doesn't match your chosen project or profile".

**Root cause:** v2's own plan-only framing asks the draft to say the work is new. The claim-list step then returned that sentence as a past-work claim with no project, and the experience pass flagged every such sentence without checking whether it claimed anything.

**Fix:** the experience pass now judges only sentences that claim past work (I've built, I used, experience with, in a past project and so on). Sentences that say the work is new, or only describe a plan, are skipped. The claim-list prompt says the same (prompt v2.0.2).

**How it's checked:** a unit test passes the honest sentence and a plan sentence, and asserts that only an invented "I've built this exact setup for three clients" is flagged. Rerun on the live app: _to fill in_.

**Lesson:** a check has to agree with the writer's instructions. Here v2 told the draft to be honest, then punished the honesty.
