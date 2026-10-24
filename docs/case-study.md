# Case study: Proposal Pipeline v2

**Anam Saleem · AI Automation Engineer · MUST Company 5-Day AI OS Sprint**

I rebuilt my own freelance proposal workflow as a small AI OS. You paste a job; it checks the link and duplicates, scores the client, decides **Apply**, **Apply with questions** or **Skip** with one plain reason, and drafts a proposal that only claims work you've actually done. You confirm the details, review the draft and send it yourself.

**Results in brief:**
- In four fully live eval runs, it got every decision and trust score right (48 of 48).
- The final code passed 12 of 12 and 11 of 12 in two live runs.
- In the last run, 8 of 9 drafts passed the rubric, with zero unsupported claims.
- It runs from a live link with nothing to install.

## 1. User and problem

**User:** a freelancer who applies to posted jobs several times a week. I'm the first user: I freelance on Upwork, and before this I built and ran an n8n proposal pipeline (v1) at my previous job. The rules live in code, not in prompts, so someone with no prompting skill gets the same result.

**Job to be done:** "When a job catches my eye, tell me quickly if it's worth applying to, and give me a proposal I'd actually send: specific to the post, and claiming only work I've done."

**Why it matters:**
- **Time:** about 57 minutes per proposal with plain ChatGPT, and 65–85+ with v1. These are my per-step estimates; v1's come from testing it on 100+ jobs.
- **Money:** every Upwork proposal costs Connects. Skipping a bad job saves the Connects and the hour.
- **Trust:** a freelancer is hired on their own work, so every claim has to be real.

## 2. Existing workflow and bottleneck

**Plain ChatGPT (main baseline):**

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
 → I edit, copy and send → Mark as sent → outcome → CSV sent log
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
- **Streamlit Cloud forgets on restart.** So the sent log downloads as CSV. I picked that over a database, a Google Sheet or login, because each of those pushed setup onto the user.

**Input variation handled:**
- search, profile and duplicate links
- whole-page pastes with other jobs and footers
- a 2,000-word spec
- two-line vague posts and $5 placeholder budgets
- hourly, fixed and non-USD budgets
- instructions inside posts (followed, refused, ignored or red-flagged)
- busy or failing models
- Freelancer.com jobs with no client data
- checking an old job again

## 5. What the AI does, what the human decides

| AI in v2 | Me (the human) |
| --- | --- |
| Reads a messy page and pulls out the fields | Confirms or fixes the fields before anything is judged |
| Answers yes/no facts about the job and each project | Sets the rules that turn facts into decisions |
| Writes the Solution Brief and the proposal | Adds anything the proposal must say, in their own words; picks or switches the proof project; edits the draft |
| Lists every claim in the draft | Fixes anything the claim check flags |
| | Overrides any Skip (logged with a reason) |
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

**Where I stopped:** one fact, "same records", still flips now and then. I stopped there on purpose. Each live run was failing on a different single fact, so more tuning would only fit the 12 cases. Two failures were the test set's own fault ("0 reviews" expected where the page shows none), and I corrected them openly.

**Measured in the fully live runs:**

| | Plain ChatGPT | v1 | v2 |
| --- | --- | --- | --- |
| Decisions and trust scores right | No decision step | No decision step | 48 / 48 over 4 runs |
| Rubric pass | 3 / 3 (T01–T03) | 0 / 5 (agency format) | 8 / 9 last run (7 / 9 the two before) |
| Unsupported or overstated claims | 0 | 5–7 per draft | 0 in 9 drafts last run (2, then 1, before) |
| Pipeline time per drafted job | ~30 s per answer | ~3 min per generation | ~1.5–2 min on the free tier, mostly rate-limit waits; a Skip takes seconds |
| LLM calls | 1 + 3 revisions | Full chain + images | Drafted: 7. Red-flag or below-minimum Skip: 1 |
| Errors absorbed | — | — | 57 per run, by retries and fallbacks; no case lost |
| Minutes per proposal, open → send-ready | ~57 | 65–85+ | _from the real-job check_ |

**Limitations:**
- **The biggest one:** "how close is my past project to this job?" is still the weakest call. The claim check can't catch an overstated "I did nearly this", because the project behind it is real. The vote and the evidence rule bring it down to 0–1 misses per run.
- Vague posts get honest but generic "questions first" drafts (T04 fails the rubric).
- Small style slips in passing drafts, such as "My goal" instead of "Your goal".
- The free tier sets the speed, and sometimes which model answers.
- Freelancer.com shares no client history through its API, so trust there rests on what the user copies in.
- The live app forgets on restart, so the sent log has to be downloaded.
- 12 synthetic test cases on one sample profile.

## 7. Non-developer handoff

- **Running it:** open the live link, enter the passphrase. Nothing to install.
- **Trying it:** the Sample workspace loads a sample freelancer with 3 projects, the 12 test jobs, and sample Freelancer.com jobs for the link and search tabs.
- **Handing it over:** the README has the 3-step local setup, the operator runbook (what each error means and what to do) and the eval commands.
- **Proxy user:** a computer science student learning Django, with no freelance experience and no project library, ran two real jobs on the live link: an Upwork paste and a Freelancer.com link. It took him about 10 minutes to open the app, pick a job and get a proposal. He needed me twice: to ask what "exclude terms" and "client history" mean. With no projects, both drafts said honestly that the work was new to him. His session led to five changes:
  - "Exclude terms" removed, because it confused him.
  - The search tab explained in plain words.
  - Price and timeline are never confirmed for you (one draft had confirmed "$400–$600, 5–7 days" on his behalf).
  - Dollar amounts in the Solution Brief fixed.
  - Both input screens now say where client history comes from (the **About the client** box on the right of the job's page), with an Open job button beside it.

## 8. First two weeks after launch

| Metric | Why | Where it comes from |
| --- | --- | --- |
| Proposals sent through v2 vs outside it | Adoption | Sent log vs my Upwork history |
| Median minutes, paste → sent | The time claim | Logged at Mark as sent |
| Share of each draft edited before sending | Draft quality and voice | Logged at Mark as sent |
| Skips I overrode, and why | Are the rules right? | Override log |
| Reply rate by decision and trust band | Does the triage pick better jobs? | One-tap outcomes |
| Unsupported claims per draft | The guardrail stays at zero | Hand count, weekly sample |

## 9. Next two weeks

**Week 1: steadier calls, measured on real work**
- Apply the evidence rule to "same records": the record type has to appear in both the post and the project.
- Move the four fit questions to facts plus rules, the way the proof label already works.
- A better "questions first" draft for vague posts.
- Grow the real-job set to 30 jobs, with my call recorded before v2's.
- Calibrate the AI judge against my hand scores, and use it only on the items where it agrees with me.

**Week 2: close the loop with outcomes**
- Persistent storage, so the live app keeps jobs across restarts, with a workspace per user.
- Use the logged outcomes to see which decisions and proof framings win, before changing any rule.
- Learn my voice from my edits; the edit share is already logged per draft.
