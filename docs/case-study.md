# Case study: Proposal Pipeline v2

**Anam Saleem · AI Automation Engineer · MUST Company 5-Day AI OS Sprint**

I rebuilt my own freelance proposal workflow as a small AI OS. You paste a job; it checks the link and duplicates, scores the client, decides **Apply**, **Apply with questions** or **Skip** with one plain reason, and drafts a proposal that only claims work you've actually done. You confirm the details, review the draft and send it yourself.

**Results in brief:**
- Every decision and trust score was right in all seven fully live eval runs (84 of 84).
- The submitted version, v2.0.9, passes 11 of 12 test cases live, with the proof framed right on all 12.
- An AI judge from a different model family, checked against my own scores, passes 6–7 of v2's 9 test drafts. Plain ChatGPT's 3 drafts pass 3 of 3.
- On the final round of real jobs, v2 got to a draft I'd send in 6–10 minutes. The judge passed 3 of its 4 drafts and 0 of ChatGPT's 2.
- It runs from a live link with nothing to install.

## 1. User and problem

**User:** a freelancer who applies to posted jobs several times a week. I'm the first user: I freelance on Upwork, and before this I built and ran an n8n proposal pipeline (v1) at my previous job. The rules live in code, not in prompts, so someone with no prompting skill gets the same result.

**Job to be done:** "When a job catches my eye, tell me quickly if it's worth applying to, and give me a proposal I'd actually send: specific to the post, and claiming only work I've done."

**Why it matters:**
- **Time:** finding a job takes 5–7 minutes, then plain ChatGPT needs 7–12 more for a first draft (measured on 3 real jobs), and that draft still isn't one I'd send. My Day 1 estimate, with the revision rounds to make it sound like me, was about 57 minutes. v1 took 65–85+ (from testing it on 100+ jobs).
- **Money:** every Upwork proposal costs Connects. Skipping a bad job saves the Connects and the hour.
- **Trust:** a freelancer is hired on their own work, so every claim has to be real.

## 2. Existing workflow and bottleneck

**Plain ChatGPT (main baseline), my Day 1 estimate.** The Day 5 stopwatch runs are in section 6.

| Step | Minutes |
| --- | --- |
| Find and read the job | 5 |
| Pick which past projects fit | 5 |
| Write my background for this job | 5 |
| Generate, read and fix the first answer | 10.5 |
| 3+ revision rounds to make it sound like me | 31.5 |
| **Total** | **~57** |

**v1, my previous pipeline:**
- A person picks the job and types it into a 10-field form (about 15 minutes, including judging the client).
- A chain of LLM steps writes a sample case study, a storyboard and a proposal.
- Review takes 7 minutes, then 2–3 revision rounds of 20+ minutes each.
- v1 was built for an agency's sales format, so each proposal was built around a generated sample case study, plus 36 visual frames that took another 120+ minutes.

**The bottleneck isn't the writing. It's everything around it:**
- getting the job and my background into the tool
- deciding whether the job and the client are worth it, done by hand
- spotting duplicates by hand
- revision rounds to strip generic or unsupported lines

Neither way had a skip step, so every job got a full draft.

## 3. Scope decisions and non-goals

| Decision | Why |
| --- | --- |
| Decide first, then write | The most expensive mistake is a good proposal for a bad job |
| Code decides; the LLM extracts and writes | My judgment becomes rules I can test and change, not prompt luck |
| Text only | Visuals were v1's slowest, paid step and not the bottleneck |
| Paste first; official APIs only | No Upwork API access, and scraping breaks its terms. Freelancer.com's public API handles fetch and search |
| The human always sends | Platforms treat scripts acting in your session as bots |
| Live link for non-developers | A downloaded start script triggers Windows' "Unknown publisher" warning, and a non-developer won't click past it |
| Local JSON, no database | Five days; storage sits behind one interface, so a database is a one-class swap later |

**Non-goals:** images and video, auto-submitting, scraping, scheduled fetching, pricing and win-chance, non-English drafts, multi-user login. I built login on Day 2 and removed it the same day: too much setup for every user, and one passphrase already protects the API quota.

## 4. Architecture and trade-offs

```
Paste / Freelancer.com link / Freelancer.com search
 → link + duplicate check (code)           a repeat stops here, no LLM call
 → extract fields (LLM + schema)           I confirm or fix them
 → trust score + budget gate (code)        red flag or below my minimum → Skip, no more LLM calls
 → fit and project facts (LLM, asked 3×)   majority per fact → rules → decision (code)
 → Solution Brief → proposal (LLM)
 → claim check: LLM lists claims, code checks each against my projects and the post
     → one automatic retry → still failing: the doubtful lines are shown
 → I edit, copy and send → Mark as sent → outcome → Excel sent log
```

| Layer | What's in it |
| --- | --- |
| Interface | Streamlit app on a live link, passphrase gate; CLI for one job |
| Workflow | `pipeline.py`: step order, retry, overrides, revisions, send, outcomes |
| Rules | `trust.py`, `decision.py`, `links.py`, `policy.py`, `skills.py`: plain Python, unit-tested, no LLM |
| Models | Gemini 3.8 Flash (brief, proposal), Gemini 3.5 Flash-Lite (extraction, facts, claim lists), Groq fallbacks |
| Contracts | One Pydantic schema per LLM step, shared by prompt, parser and validator |
| Data | Local JSON per workspace; a separate sample workspace |
| Tools | Freelancer.com public API, PDF text for CV import |
| Evaluation | 12 frozen cases, one-command runner, response cache and replay |

**Trade-offs:**
- **Rules in code.** Every decision is explainable and testable, but the rules are heuristics I tune by hand. The trust score started as 16 worked examples, which are now unit tests.
- **Facts from the model, labels from code.** The model answers small yes/no questions three times; code takes the majority and applies the rule. That's 2 extra cheap calls per job for answers that hold from run to run.
- **Half-LLM claim check.** The model lists the claims and code decides what's allowed. It misses what the model doesn't list, so I also count unsupported claims by hand.
- **Free tiers.** Gemini 3.8 Flash allows about 20 calls a day. Every response is cached, and busy or out-of-quota calls move down the fallback chain. The logs record which model answered.
- **Streamlit Cloud forgets on restart.** So the sent log downloads as an Excel file. I picked that over a database, a Google Sheet or login, because each of those pushed setup onto the user.

**Input variation handled:**
- search, profile and duplicate links
- whole-page pastes with other jobs and footers
- a 2,000-word spec
- two-line vague posts and $5 placeholder budgets
- hourly, fixed and non-USD budgets
- instructions inside posts (followed, refused, ignored or red-flagged)
- busy or failing models
- a different client box per platform: Upwork's history, Freelancer.com's rating and reviews (its API shares no client data), Guru's paid jobs and invoices
- checking an old job again

## 5. What the AI does, what the human decides

| AI in v2 | Me (the human) |
| --- | --- |
| Reads a messy page and pulls out the fields | Confirms or fixes the fields before anything is judged |
| Answers yes/no facts about the job and each project | Sets the rules that turn facts into decisions |
| Writes the Solution Brief and the proposal | Adds anything the proposal must say, in their own words; picks or switches the proof project; edits the draft |
| Lists every claim in the draft | Fixes anything the claim check flags |
| | Overrides any Skip (logged with a reason) |
| | Fixes the client's details at any point; trust and the call update |
| | Sends. v2 never submits anything |

Every screen shows why: the reason for the decision, the trust score and how many fields it rests on, whether the three checks agreed, and the exact lines the claim check doubts.

## 6. Failures, changes and results

**Live failures, each traced to a root cause** (full write-ups in `evals/failures.md`):

| # | What happened | Root cause | Change |
| --- | --- | --- | --- |
| F1 | First live run: every model failed | Gemini busy; the only fallback wasn't available to my key | Busy retries, other Gemini model, then a Groq list; `check_models.py` |
| F2 | A portfolio request was refused as a "claim" | "Claim" defined too broadly | Narrowed to orders to assert facts |
| F3 | A no-proof draft skipped a request for past work, silently | Empty project library, no warning | A warning that names the unanswered request |
| F4 | "API" flagged on a post asking for REST APIs | No plurals; generic words treated as tools | Plural matching, generic-word list |
| F5 | My honest "this is new for me" was flagged | v2 asked for honesty, then flagged it | Only past-work sentences are checked |
| F6 | $40–150/hour judged as a $150 total | The model saw "$40 – $150" without "Hourly" | Budget sent in plain words |
| F7 | Real job: "I did nearly this" from a booking chatbot on an SEO content job | Sharing a build tool (n8n) counted as evidence | Fixed: build tools aren't evidence; the line names the real project |
| F8 | Real jobs: "My goal…", "to shipped", a repeated phrase | The claim check checks facts, not wording | Fixed: checked in code and retried |
| F9 | v2.0.8: drafts restate the post and copy the project's wording | v2.0.7's "cover every deliverable" order | v2.0.9: no repeated requirements; copied proof is flagged, but still happens (T05) |
| F10 | Real SEO job: "nearly this" for the chatbot again, after an override | The override path skipped the proof rules | Fixed: one labelling function for both paths |
| E1–E3 | Eval decisions and proof wording flipped between runs | Judgments left to the model | Rules in code, a vote over three checks, an evidence rule |

**Evaluation (12 frozen test cases):**

| Run | Passed |
| --- | --- |
| Before (v2.0.0) | 9 / 12 |
| After the F2–F6 fixes | **7 / 12** (worse) |
| Test-set fix, stricter "similar" | 10 / 12 |
| Placeholder rule moved into code | 9 / 12 |
| Proof label decided in code from four facts | 11 / 12 |
| Tie-break on the post's own tools (saved answers) | 12 / 12 |
| Same code, fully live | 10 / 12 |
| Vote over three checks, fully live | 10 / 12 |
| Evidence rule for "similar", fully live | 11 / 12 |
| Same code, fully live again | **12 / 12** |

**What I learned from the dip:** two judgments were still left to the model, whether a $5 budget is "realistic" and whether a past project is "similar". It answered differently every run, and every rewording just moved the failure to another case.

**What fixed it:**
1. The model now only reports plain facts, and code makes the call.
2. Live reruns showed that even a fact can flip, so each fact is asked three times and the majority wins.
3. "Similar" now needs a specific tool named in both the post and the project. That fixed the vague-post case for good.

**Day 5: an outside score.** My rubric scores were an AI first pass that I checked, so they weren't blind. An AI judge from a different model family scored the same drafts. It agreed with me 83–100% per item but was stricter: 6 of 9, where I had 8. I used its written reasons to pick the next fixes:

| Version | Change | Checks, live | Judge |
| --- | --- | --- | --- |
| v2.0.6 | Day 4 final | 12 / 12, then 11 / 12 | 6 of 9 |
| v2.0.7 | Concrete plans, every deliverable, one closing question, wording checks, build tools aren't evidence | 10 / 12 (a new check's false alarm), 12 / 12 once fixed | 5 of 9 |
| v2.0.8 | The "nearly this" line names the real project, never an invented client | 10 / 12 | 7 of 9 |
| **v2.0.9** | Each requirement said once; "similar" needs every check to agree; the override uses the proof rules | **11 / 12** | 6 of 9 |

v2.0.7 fixed everything it targeted and still scored worse. The reasons showed why: the old template asked for a client type, so the model invented "a sales team". v2.0.8 fixed that, and v2.0.9 fixed the repetition and a real override bug (F10).

**Where I stopped:** I checked the judge too. Re-scoring the same old drafts changed one verdict in four, so 6 versus 7 of 9 is noise. I stopped at v2.0.9 instead of tuning toward 9 of 9 on twelve cases, and I never edited the frozen test set to get there. The one correction to it was on Day 4: two cases expected "0 reviews" where the page shows none, against the extraction rule, and I logged the fix openly.

**Measured in the fully live runs:**

| | Plain ChatGPT | v1 | v2 |
| --- | --- | --- | --- |
| Decisions and trust scores right | No decision step | No decision step | 84 / 84 over 7 runs |
| Rubric pass | 3 / 3 (T01–T03), me and the judge | 0 / 5 (agency format) | AI judge: 6–7 / 9 on v2.0.8–v2.0.9 (6 / 9 on v2.0.6, where I scored 8 / 9) |
| Unsupported or overstated claims | 0 | 5–7 per draft | 0 in 9 drafts on v2.0.6's last run, by hand (2, then 1, before) |
| Pipeline time per drafted job | ~30 s per answer | ~3 min per generation | ~1.5–2 min on the free tier, mostly rate-limit waits; a Skip takes seconds |
| LLM calls | 1 + 3 revisions | Full chain + images | Drafted: 7. Red-flag or below-minimum Skip: 1 |
| Errors absorbed | — | — | 57 per run, by retries and fallbacks; no case lost |
| Minutes from the open job to a draft | 7–12 on 3 real jobs, measured; none I'd send | 65–85+ (estimate) | **6–10, median 8** on the v2.0.8 round, to a draft I'd send (10 median on the earlier v2.0.6 round) |
| Same jobs side by side | Laravel audit 12 · marketplace MVP 10 | — | Laravel audit 10 · marketplace MVP 7 (v2.0.6 round) |
| Revision rounds | 3+ | 2–3 | 0–1 |

**Real jobs.** Two rounds, each job timed by stopwatch from adding it in v2 to a draft I'd send. Finding the job is timed on its own.

- **Final round (v2.0.8), 6 jobs:** 6–10 minutes per draft, plus 3–5 minutes to find the job. Both work-type Skips (a Laravel code audit, a design-only job) held, and I agreed with them. The marketplace job turned into a Skip because $131–395 can't cover the scope, the same warning ChatGPT gave. The judge passed 3 of 4 drafts. The one fail was the SEO job, the override bug (F10) that v2.0.9 fixes.
- **Earlier round (v2.0.6), 7 jobs:** 10 minutes median. Asked to "exaggerate my project", the revision added adjectives but no new facts. On a Guru job that asked for a quote, the draft left the price for me to fill in.
- **Against plain ChatGPT, on 3 of the same jobs:** ChatGPT got to a first draft in 7–12 minutes. It said Apply on both jobs I asked it about, including a healthcare build I'd skip, and I wouldn't have sent any of its three drafts. The judge passed 0 of 2.

The honest reading: v2 is only a little faster to a first draft. The difference is that v2's draft is the one I send, and the Skip comes before any writing.

**Limitations:**
- **The biggest one:** "how close is my past project to this job?" is still the weakest call. The claim check can't catch an overstated "I did nearly this", because the project behind it is real. The vote and the evidence rules brought it to 12 of 12 on v2.0.9, but it took four live versions, and the facts under it still split between checks.
- Vague posts get honest but generic "questions first" drafts (T04 fails the rubric).
- The model sometimes copies a project's own sentence as the proof (T05 on v2.0.9). The check flags it, but the retry didn't fix it. Drafts also read alike: each opens "Your goal is to…".
- The judge fails the same 2 of 9 test drafts in every version: the vague post (T04) and the 2,000-word spec (T06).
- The free tier sets the speed, and sometimes which model answers.
- Freelancer.com shares no client history through its API, so trust there rests on what the user copies in.
- The live app forgets on restart, so the sent log has to be downloaded.
- 12 synthetic test cases on one sample profile, and 7 real jobs: enough to time it, not enough to measure skip accuracy.

## 7. Non-developer handoff

- **Running it:** open the live link, enter the passphrase. Nothing to install.
- **Trying it:** the Sample workspace loads a sample freelancer with 3 projects, the 12 test jobs, and sample Freelancer.com jobs for the link and search tabs.
- **Handing it over:** the README has the 3-step local setup, the operator runbook (what each error means and what to do) and the eval commands.
- **Reproducing it without me:** `python -m pytest -q` runs all 121 tests with no API keys. `python scripts/run_evals.py --replay` reruns the 12 cases offline from the saved model answers. The README also says exactly what the live link keeps and loses on a restart.
- **Proxy user:** a computer science student learning Django, with no freelance experience and no project library, ran two real jobs on the live link: an Upwork paste and a Freelancer.com link. It took him about 10 minutes to open the app, pick a job and get a proposal. He needed me twice: to ask what "exclude terms" and "client history" mean. With no projects, both drafts said honestly that the work was new to him. His session led to five changes:
  - "Exclude terms" removed, because it confused him.
  - The search tab explained in plain words.
  - Price and timeline are never confirmed for you (one draft had confirmed "$400–$600, 5–7 days" on his behalf).
  - Dollar amounts in the Solution Brief fixed.
  - Both input screens now say where client history comes from (the **About the client** section of the job's page), with an Open job button beside it.

## 8. First two weeks after launch

| Metric | Why | Where it comes from |
| --- | --- | --- |
| Proposals sent through v2 vs outside it | Adoption | Sent log vs my Upwork history |
| Median minutes from adding a job to sending it | The time claim | Logged at Mark as sent |
| How much of each draft I change before sending (%) | Draft quality and voice | Logged at Mark as sent |
| Skips I overrode, and why | Are the rules right? | Override log |
| Reply rate by decision and trust band | Does the triage pick better jobs? | One-tap outcomes |
| Unsupported claims per draft | The guardrail stays at zero | Hand count, weekly sample |

## 9. Next two weeks

**Week 1: steadier calls, measured on real work**
- A steadier "same records" fact. A plain word match would flip T05's frozen answer, so it needs a better test.
- A rewrite step for a proof that copies its project (T05), since the retry alone doesn't fix it.
- A better draft for very long specs (T06), which leans on the screening answers today.
- Move the four fit questions to facts plus rules, the way the proof label already works.
- A better "questions first" draft for vague posts (T04).
- Grow the real-job set to 30 jobs, with my call recorded before v2's.
- A blind score from a second person on the same drafts (`scripts/blind_pack.py` is ready), next to the AI judge's.

**Week 2: close the loop with outcomes**
- Persistent storage, so the live app keeps jobs across restarts, with a workspace per user.
- Use the logged outcomes to see which decisions and proof framings win, before changing any rule.
- Learn my voice from my edits; how much of each draft I change is already logged.
