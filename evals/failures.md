# Failure analysis

Real failures found while running v2, each with its root cause, the fix and how the fix is checked. F1–F6 come from live use on Days 3–4, F7–F10 from the real jobs and eval runs on Day 5. The eval-run failures (E1–E3) are in [day4-results.md](day4-results.md).

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

**How it's checked:** two new tests. One simulates a 503 on both Gemini models and a 404 on the first Groq model, and asserts the exact order tried before the second Groq model answers. The other asserts the "busy" message when every model is busy. Since the fix, each final eval run absorbed 57 busy or rate-limit errors with no case lost, and all seven real jobs on Day 5 completed.

**Lesson:** fallbacks need their own check at startup, not just a name in config.

## F2 · A portfolio request was refused as a "claim" · 2026-10-22

**What happened:** on the same React Native job, the confirm screen listed "Please share 1–2 React Native applications you've built…" under **Won't follow (asks you to claim something)**.

**Root cause:** the extraction prompt defined a claim instruction as "asking the applicant to state something about their experience or identity". That's broad enough to cover an ordinary request for past work, so the model filed it with "say you have 10 years of experience". Refused instructions are left out of the draft, so the proposal would have ignored what the client asked for. That would fail rubric item 1 (covers every explicit requirement).

**Fix (prompt_version v2.0.0 → v2.0.1):** a claim instruction is now only an order to assert a specific fact whatever the truth. Requests to share, show, link or describe past work go to `explicit_requirements`, which the draft answers from the user's real projects.

**How it's checked:** T11 (the "10 years" instruction) must still be refused; this job's portfolio request must land in explicit requirements. T11 was refused in all four live eval runs. On Day 5, the Guru client's "include relevant project examples" landed as a requirement, and the draft screen named it.

**Lesson:** a safety rule written too broadly blocks legitimate asks. Policy definitions need a counter-example as well as an example.

## F3 · A plan-only draft ignored the client's request for past work · 2026-10-22

**What happened:** the React Native job asked applicants to "share 1–2 React Native applications you've built". The draft named no app and said the offline and API work was "new for me".

**Root cause:** the Projects library was empty, so v2 wrote a plan-only draft. That's correct, because it must never invent proof. But nothing told the user that the draft had no proof, or that it skipped an explicit request. The Solution Brief was fine; the gap was between the library and the draft, and it was silent.

**Fix:** the draft screen now warns when no project is cited, names any request for past work it couldn't answer, and says how to fix it (add the project, pick it under Proof, Rewrite with this proof).

**How it's checked:** an app test opens an empty workspace, writes a draft and asserts the warning. On Day 5's Guru job, no project was close enough, and the draft screen said so and named the client's request for examples. I picked the projects to cite and rewrote.

**Lesson:** a safe default (no invented proof) still needs to be visible. Silent safety reads as a weak draft.

## F4 · The claim check flagged "API" on a post that asks for REST APIs · 2026-10-22

**What happened:** the React Native draft was marked "needs review" with "the draft mentions API, which isn't in your skills, your project or the post", although the post says "Integrate the app with our existing REST APIs".

**Root cause:** two gaps in the names pass. It matched whole words only, so "API" didn't match "APIs". It also treated generic words as tools, so "API" was checked like "Salesforce" would be.

**Fix:** names now match singular or plural, and a list of generic words in `config.toml` (API, app, UI, backend, database and others) is skipped by the names pass. Specific tools are still checked.

**How it's checked:** a unit test asserts "API" matches "APIs", generic words pass, and "Salesforce" is still treated as a tool. Not seen again in the seven real jobs on Day 5.

**Lesson:** false alarms cost trust as much as misses. A "needs review" on an honest draft trains the user to ignore the check.

## F5 · The claim check flagged the draft's own honest "new for me" sentence · 2026-10-22

**What happened:** a plan-only draft said "This entire workflow setup is new for me, and here is how I would de-risk it: I will verify API access credentials…". The claim check marked it "doesn't match your chosen project or profile".

**Root cause:** v2's own plan-only framing asks the draft to say the work is new. The claim-list step then returned that sentence as a past-work claim with no project, and the experience pass flagged every such sentence without checking whether it claimed anything.

**Fix:** the experience pass now judges only sentences that claim past work (I've built, I used, experience with, in a past project and so on). Sentences that say the work is new, or only describe a plan, are skipped. The claim-list prompt says the same (prompt v2.0.2).

**How it's checked:** a unit test passes the honest sentence and a plan sentence, and asserts that only an invented "I've built this exact setup for three clients" is flagged. Not seen again in the seven real jobs on Day 5.

**Lesson:** a check has to agree with the writer's instructions. Here v2 told the draft to be honest, then punished the honesty.

## F6 · An hourly rate was judged as a total budget · 2026-10-23

**What happened:** on a real Upwork job ($40–$150 per hour, 30+ hours a week, 3–6 months) the fit check said "Realistic for the budget: No. The budget of $40 to $150 is unrealistically low for building a comprehensive … engine." The Details panel also showed the dollar amounts garbled.

**Root cause:** two gaps. The prompts gave the model the budget as the post wrote it ("$40.00 - $150.00"); the word "Hourly" sat on another line of the post, so the model read a $150 total. Separately, Streamlit reads text between two dollar signs as a maths formula, which garbled the Details panel.

**Fix:** the prompts now state the budget in plain words from the confirmed fields ("hourly rate of $40–$150 per hour (paid per hour worked, not a total)"), and the realistic check is told to judge an hourly rate as a rate (prompt v2.0.3). The Details panel keeps dollar signs literal and shows the same plain budget line. The skill line now reads "0 of 2 skill tags on the post are in your profile (missing: HubSpot, Lead Generation)", so it no longer looks like it contradicts "Skills: Yes".

**How it's checked:** a unit test asserts the plain budget wording for hourly, fixed-range and missing budgets. Not seen again in the seven real jobs on Day 5.

**Lesson:** give the model the fact in the form the decision needs, not the raw text it came from.

## F7 · "I did nearly this" from a project that only shares the tool · 2026-10-25

**What happened:** a real Freelancer.com job asked for SEO content on autopilot: n8n pulls keyword data, writes optimised pages and pushes them into Sanity CMS as drafts. v2 picked my AI chatbot agent (appointment booking over a CRM) and wrote "I did nearly this for a booking management workflow". I asked the revision to sound more professional, and it became "I completed a similar architecture". The claim check passed both, because the project is real.

**Root cause:** the proof label is "similar" when the work is the same kind and the platform or the records match. Both jobs are n8n automation, so "same kind of work" and "same platform" were yes. The evidence rule (#60) asks for a specific tool named in both texts, and n8n is one. So every rule held, and the label was still wrong: sharing the tool says nothing about the deliverable. A booking agent and a content pipeline have different inputs, outputs and records.

**Fix (prompt v2.0.7 and v2.0.8):**
- A tool the freelancer builds with (n8n, Python, Make, React Native and others, `build_tools` in config.toml) no longer counts as evidence for "similar". The shared tool has to be one of the client's own systems, like Shopify, Google Sheets or Airtable (#105).
- The "nearly this" line now says what the past project was, naming its own systems, and never invents a client type (#108). The old template asked for "[client type]", and the model filled it with "a sales team" (v2.0.7 judge, T05 and T07).

I first planned "records or deliverable must match too", but that rule would have flipped T03 and T05, whose frozen answer is "similar", so I didn't use it.

**How it's checked:** a unit test asserts n8n alone gives no evidence while Google Sheets still does (T01). On v2.0.8 the judge passed T05 and T07 on honest proof, which v2.0.7 had failed.

**Lesson:** a rule can hold on every test case and still be too loose. The real job found what the 12 cases didn't.

## F8 · Sentence slips that the claim check can't see · 2026-10-25

**What happened:** four drafts from the real jobs had wording a client would notice:
- "My goal is to build a 30-day MVP…" (it should be the client's goal);
- "I used React Native to shipped four apps";
- one sentence repeating the project's result phrase twice;
- an empty proof line: "I used Automation to build systems that operate reliably" (the only shared skill is "Automation", and the project never says "reliably").

**Root cause:** the proof sentence is filled from a template ("in [project] I used [skills] to [outcome]") with the project's own text, which is written as a past-tense sentence. The claim check confirms that every fact traces to a project, so it passes. Nothing checks grammar or repetition. "My goal" was already seen on two eval drafts (T04, T07).

**Fix (prompt v2.0.7):** the claim check now flags "My goal…" at the start, broken verbs ("to shipped") and a phrase of 5+ words repeated, and sends them to the automatic retry (#106). The prompt asks for the proof as one grammatical sentence of the freelancer's own.

The first live run showed the repeat check was too strict: it flagged T01 and T12 for repeating the client's own field list and workflow name. Now it skips phrases from the post (#107).

**How it's checked:** unit tests for each pattern, including the client's-own-words case. None of the three slips appeared in v2.0.8's eval drafts or its real-job drafts. What's left is F9.

**Lesson:** a fact check isn't a read-through. That's why v2 stops at a draft and the freelancer sends.

## F9 · Drafts restate the post and copy the project's wording · 2026-10-25

**What happened:** on v2.0.8, T11's draft repeats two long phrases ("summarize and extract sender, company, request type, a 2-sentence summary and a priority flag"), and the automatic retry didn't fix it. On a real n8n job the draft says "production-ready n8n workflow file (JSON) with clear node labels" twice. Both real n8n drafts copy the chatbot project's "What I did" almost word for word as the proof.

**Root cause:** v2.0.7 told the draft to state the goal, then every deliverable, then the steps, so the same requirement shows up two or three times. The repeat check skips the post's own phrases on purpose (#107), so it can't see this. Nothing in code compares the proof line with the project's text.

A real SEO job on v2.0.8 showed the worst case: the draft listed every deliverable, then repeated the first three word for word as the plan. That made it 1,558 characters against Freelancer.com's 1,500 limit, and the automatic retry didn't fix it.

**Fix (prompt v2.0.9, #111):**
- Each requirement is said once, inside the step that delivers it.
- The prompt states the platform's character limit.
- The proof is one short sentence of my own.
- The claim check now flags a requirement restated word for word (10+ words, even when the words come from the post), and a proof that copies 12+ words of a project's "What I did".

**How it's checked:** unit tests for both checks, and the v2.0.9 live run (11 of 12). No v2.0.9 draft repeats a requirement, and none exceeded a length limit. One draft (T05) still copied 12+ words of its project. The new check caught it, but the retry didn't fix it, so the draft page shows it as a warning. Still open: copying needs a stronger instruction or a rewrite step of its own.

**Lesson:** a fix for one rubric item (cover every requirement) can cost another (reads like a person wrote it). The judge measures the first, not the second.

## F10 · An override skipped the proof rules · 2026-10-25

**What happened:** a real Freelancer.com SEO job ($16–132) was a Skip for being below my minimum, so no fit check ran. I overrode it. The draft said "I did nearly this: built an AI chatbot agent with n8n…": the F7 overstatement, back on the job that first showed it.

**Root cause:** when the Skip comes before the fit check, the override runs one fit check itself. That path kept the model's own proof label and never applied the rules: the label decided from facts, the evidence rule, and the build-tool rule from F7. The main path had them; the override path didn't.

**Fix (#109):** the proof rules live in one function that the fit check and the override both call. Also new (#110): "similar" needs its key fact to hold in all three checks, not only the majority.

**How it's checked:** a unit test for the split-vote rule. Simulated on the saved facts from both live runs, it changes only T02, which is the case it should fix.

**Lesson:** a rule that only runs on the main path isn't a rule. Every way into "write a draft" has to pass through the same checks.
