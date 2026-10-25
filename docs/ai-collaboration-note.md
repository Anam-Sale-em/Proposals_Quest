# AI collaboration note

**Anam Saleem · Proposal Pipeline v2**

I used AI heavily to build this. The decisions, the checks on its output, and what stayed or went were mine. The decision log (`docs/decision-log.md`, 97 rows) records who proposed each change, me or the AI, and what I decided.

## 1. AI tools and the role of each

| Tool | Role |
| --- | --- |
| **Claude (chat)** | Reviewed my sprint plan. Drafted the Day 1 documents (problem, scope, workflow map, metrics, rubric). Designed the 12 test cases and recomputed every expected trust score and decision with a script |
| **Claude Code** | Wrote the v2 codebase from my plan and the decision log: contracts, rules, validators, the LLM client with retries and fallbacks, the pipeline, the Streamlit app, the eval runner and 112 tests. Diagnosed failures I found on the live app and in eval runs, and did the UI redesign |
| **ChatGPT** | The baseline itself: plain ChatGPT drafting T01–T03 from one fixed prompt, timed and scored |
| **Gemini 3.8 Flash** (in the product) | Writes the Solution Brief and the proposal |
| **Gemini 3.5 Flash-Lite** (in the product) | Extracts job fields, answers the fit and project facts, lists the claims in each draft |
| **Groq: gpt-oss-120b, gpt-oss-20b** (in the product) | Fallback when Gemini is busy or out of quota |
| **Groq: Qwen 3.8 27B** (evals) | The AI judge for the rubric. It's a different model family from the drafters, so no model grades its own work |

## 2. Work delegated to AI

- **Code:** almost all of it, written to my plan and to the rules I set (trust score, budget gate, fit × trust table, instruction policy, claim check).
- **Tests:** unit tests for every rule, a scripted stand-in model so the whole flow runs offline, and app tests that click through the UI.
- **Documents:** first drafts of the Day 1 docs, the failure write-ups and this package. I cut, corrected and approved each one.
- **Test design:** the 12 cases and their expected values, worked out from my rules by script.
- **Diagnosis:** reading eval output and code to find the root cause of each failure I reported.
- **First-pass rubric scoring** of the 9 live drafts. I checked every score against the draft and the post before using it.

## 3. How I verified AI-generated results

- **By using it on real jobs.** I ran v2 on real Upwork and Freelancer.com posts on the live app, and nearly every fix in the decision log from row 37 on started with something I spotted there.
- **Against the test set.** I ran `run_evals.py` on the real models: before (an old commit, opened with `git worktree`) and after each round of fixes. I read the failed checks rather than trusting the pass count.
- **With tests that run without a model.** 112 tests cover every rule. I ran them before every push. Once a push went through with a failing test; I traced it to leftover files from the removed login and deleted them.
- **By checking facts the AI stated.** Before relying on a model name, I ran `check_models.py`, which showed the AI's first Groq fallback wasn't available to my key (F1). I checked the Freelancer.com API's claims against the live job page (no client data, the budget shown).
- **By hand-scoring.** I scored ChatGPT's and v1's drafts against the rubric myself, and checked the AI's first-pass scores on v2's drafts. Unsupported claims are counted by hand, never by the claim check alone. That's how the two "I did nearly this" overstatements were found: the claim check passes them, because the project is real.
- **On seven real jobs, by stopwatch.** On Day 5 I ran fresh Upwork, Freelancer.com and Guru jobs and read every draft before calling it send-ready. That found two problems the tests passed: an overstated "I did nearly this" built on a shared tool (F7), and wording slips like "to shipped" (F8).
- **Against my own estimate.** My Day 1 baseline of about 57 minutes was a per-step estimate. On Day 5 I timed plain ChatGPT on three of the same real jobs. It was faster to a first draft than I'd estimated (7–12 minutes), so I rewrote the time claims to match. The case for v2 now rests on a send-ready draft and the Skip, not on a big time gap.
- **With a fully live rerun.** When a cached run said 12/12, I reran with fresh model calls instead of trusting it. It scored 10/12. After two more fixes, the final code scored 11/12 and then 12/12 in two live runs, and I report both, not just the best.

## 4. Important results I rejected or corrected

| AI proposal or output | What I did | Why |
| --- | --- | --- |
| Login and sign-up with accounts in a Google Sheet (my request, AI-built) | Removed the same day; one passphrase kept | Too much setup for everyone who runs it |
| Double-click start scripts for non-developers | Rejected | Windows shows "Unknown publisher"; a non-developer won't click past it. A live link instead |
| A Google Sheet as the sent log | Removed; an Excel download instead | It needed a Google service account set up by me and shared by every user |
| An "Approximate" budget checkbox | Removed | It changed nothing and only confused the screen |
| A mandatory fit check | Made optional | Sometimes I already want the job; red flags and low budgets stay as warnings |
| Keyword search showing "Native Turkish Translation" for "React Native" | Flagged; fixed with whole-phrase matching | The platform's search matches single words |
| Freelancer.com clients always scoring "Unknown" | Asked for my own rule; scored on reviews, rating and payment verified | That's all Freelancer.com shows |
| Claim check flagging my honest "this is new for me" (F5), and "API" on a REST API post (F4) | Spotted on live drafts; the check was narrowed | False alarms teach the user to ignore the check |
| "Realistic for the budget: No" on a $40–150/hour job (F6) | Spotted; the budget now goes to the model in plain words | It had read an hourly rate as a total |
| The AI's first fix for a failing eval case (stricter wording for "similar") | It broke another case; I pushed for a fix that holds | Rewording moved the failure each time. What held: four yes/no facts, the label decided in code, a vote over three checks, and "similar" only with a tool named in both texts |
| Expected values in the AI-designed test set ("0 reviews" where the page shows none) | Corrected, and logged as an amendment to the frozen set | They contradicted the extraction rule itself |
| Re-running v1 for the baseline (Day 1 suggestion) | Rejected; plain ChatGPT as the main baseline, v1's numbers as reference | I no longer have access to v1 |
| Labelling a real-job set on Day 1 | Moved to Day 4, my call written before v2's | Same proof with less prep |
| UI wording: "Claim check passed…", "Not checked", "Left out of the paste", "Skill overlap: 0 of 2" | Rewritten in plain words; the green banner on every passing draft cut to one quiet line | Jargon, and a banner on every draft read as v2 doubting itself |
| The first UI | Asked for a friendlier, more trustworthy design, twice | It looked like a default template |
| Sample data that confused (client box inside job details, dead "Open job" links, "4 jobs" showing 3) | Flagged each; fixed | A non-developer's first minutes happen in the sample workspace |
| Empty client fields on Upwork jobs, and no way to fix the client after the check | Removed the empty fields; asked for an Edit client details box | Upwork's client box comes with the paste; a forgotten detail shouldn't mean starting over |
| "Client trust: unknown", then "not rated yet" | Rejected both; it now says "can't rate, no details shared" | It should say why, in words a client-facing freelancer would use |
| A sent log in CSV | Switched to Excel | Dates showed as ###### and "Share edited before send" meant nothing to me |

## 5. Core decisions I owned

- **Which workflow to change:** my own proposal workflow, the one I built and ran as v1.
- **Target user and baseline:** me first, plain ChatGPT as the main baseline, quality target "hold", time target "beat".
- **What stays private:** no former employer's name, prompts, volumes or raw drafts in the repo; v1 described by design, not judged.
- **Code decides, the human sends:** the decision rules, the two approval points, and that v2 never submits anything.
- **What to cut:** login, the Google Sheet, start scripts, Firestore. Each was simpler for me as the builder and harder for anyone else.
- **When to stop tuning:** I rejected fixes that passed one case and broke another, and stopped once each live run failed on a different single fact. Past that point I'd be fitting the 12 cases, not real work. I also kept the test set honest when the test itself was wrong.
- **Optional fit check, Freelancer.com and Guru trust rules, sample data in every tab, "Check again" for old jobs, editing the client later, timings on the draft page:** all from using the app as its user.
- **What counts as proof of value:** stopwatch time on real jobs, and not shipping the wording fixes (F8) without a fresh eval run.
