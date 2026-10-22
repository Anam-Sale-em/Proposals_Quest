# Decision log

Source for the AI collaboration note. "From" records who proposed what, AI included; "My call" and "Why" record what I decided.

## AI tools so far

| Tool | Role |
| --- | --- |
| Claude (chat) | Reviewed the sprint plan, drafted the Day 1 files, designed the test cases and recomputed every expected trust score and decision with a script |
| ChatGPT | The baseline itself: plain ChatGPT drafting T01–T03 from one fixed prompt |
| Claude (coding) | Wrote the v2 codebase from the plan and this log: contracts, rules, validators, LLM client, pipeline, Streamlit app, eval runner and 75 tests |

Add each tool as it's used: the coding assistant, Gemini and Groq inside the product, and the eval judge.

## Day 1 · 2026-10-21

| # | Decision | From | My call | Why |
| --- | --- | --- | --- | --- |
| 1 | Use my own previous workflow (v1) as the workflow being changed | Me | Yes | The brief recommends a real workflow from your own work, and I have v1's export |
| 2 | Keep the employer's name, prompts and usage figures out; describe v1's design and pains only | Claude flagged my plan's own rule | Yes | Confidentiality; the export holds the employer's prompts and credentials |
| 3 | Re-run v1 on T01–T03 for the baseline | Claude, after reviewing my estimates | No, replaced by #13 | I no longer have access to v1 or an n8n subscription to run it |
| 4 | Run the 12 test cases on a synthetic sample profile | Claude | Yes | Reviewers can rerun it, and no employer work goes in the repo |
| 5 | Swap the plan's 4 user-field jobs for a duplicate, a red-flag client, a messy paste and a no-client-box case | Claude | Yes | Every Day 1 pain gets a case; real jobs are covered on Day 4 |
| 6 | Target user: me first, with v2 built so a non-developer can run it | Me, after Claude's review | Yes | It's my workflow; non-developer use is still checked with a proxy on Day 3 |
| 7 | The clock starts when the job is opened and stops at send-ready | Claude | Yes | It counts the reading and judging that v1 also cost |
| 8 | Success: v2's median below the plain-ChatGPT baseline (about 57 min) and v1 (65–85+) on T01–T03, every draft passing the rubric, zero unsupported claims | Claude, replacing "under 40 minutes" | Yes | A bar set by the baseline instead of a fixed one v2 couldn't miss |
| 9 | Red-flag clients skip the assessment and drafting calls. The plan says the history check runs "before any LLM call", but extraction is itself an LLM call | Claude, found while writing T09 and T10 | Yes | Keeps the cost claim accurate |
| 10 | Fixed-price ranges (common on Freelancer.com): compare the top end against my minimum, same as hourly | Claude | Yes | One rule for every range; skip only when even the top is below my minimum |
| 11 | Watch rubric item 1 ("covers every explicit requirement") on the 2,000-word spec in T06, where the length limit pulls the other way | Claude | Yes | One of the two items may need rewording on Day 4 |
| 12 | Set B recorded on Day 1 | Claude | No, replaced by #21 | My calls can be recorded on Day 4 instead, as long as each comes before v2's answer |
| 13 | Main baseline: plain ChatGPT on T01–T03 with one fixed prompt; v1's numbers from my 100+ test jobs as a reference | Me and Claude | Yes | The brief names "simple ChatGPT use", and v1 can't be re-run |
| 14 | ChatGPT times are my per-step estimates (about 57 min per job); one stopwatch ChatGPT run on a fresh Upwork job on Day 4 checks them | Me; the stopwatch check from Claude | Yes | Keeps one baseline number measured the same way as v2's |
| 15 | Keep v1's 120+ min of visuals out of the time comparison, as a design fact only | Claude | Yes | So v2 doesn't look faster just because it dropped visuals |
| 16 | Quality target is "hold", not "beat": plain ChatGPT's raw drafts passed the rubric 3 of 3 with 0 unsupported claims | My scoring, Claude's reading | Yes | v2's gains are time, judgment and fewer revision rounds; I report that honestly |
| 17 | Models: 3.5 Flash-Lite is still offered (15 per min, 500 per day), so the plan's split holds. 3.8 Flash allows only 20 calls a day on the free tier | AI Studio check | Yes | Cache every response from Day 2, use Groq as fallback, and turn on billing if that isn't enough |
| 18 | Score five real v1 drafts (real Upwork jobs, July–August 2026) against v2's rubric, framed as the gap between v1's agency format and a solo freelancer's needs; raw texts stay private, scores go in the repo | Me; scoring by Claude | Yes | Measured quality instead of "by design"; the texts are my former employer's output |
| 19 | Check the rubric against those eight real drafts; keep all five items, widen item 3 to cover who does the work, availability and attachments | Claude | Yes | v1 wrote in an agency's voice and mentioned a video walkthrough, and one post asked who personally does the work |
| 20 | The keyword feed lists new jobs with a trust label and makes no decision; the Apply / Apply with questions / Skip recommendation runs after I pick a job, and I can override any Skip | Me | Yes | I choose what to open; v2's judgment helps once I've chosen |
| 21 | Real-job check on Day 4: 6–10 fresh Upwork jobs, with my glance, considered and trust calls written down before v2 runs on each; no Day 1 label sets, and trust thresholds stay at the plan's values | Me | Yes | Same proof with less prep: my call always comes before v2's answer |
| 22 | The paste form gets its own client-history field. If it's empty, trust shows Unknown and I can still generate | Me | Yes | Trust only works with the client box; the choice to go ahead stays mine |

## Build · 2026-10-21

| # | Decision | From | My call | Why |
| --- | --- | --- | --- | --- |
| 23 | Every judging rule (link check, trust, budget, fit × trust, instruction policy, claim check) is plain Python, unit-tested with no LLM | Plan; code by Claude | Pending | Decisions stay explainable and testable |
| 24 | A regex backstop for instructions and red flags runs alongside the LLM's list | Claude | Pending | The policy holds even if extraction misses one (blue whale, WhatsApp, "ignore your instructions") |
| 25 | The claim check also flags "our team" and video or attachment mentions, and any years-of-experience claim | Claude, from rubric item 3 (#19) | Pending | These were the gaps the v1 drafts showed |
| 26 | Offline tests use a scripted stand-in for the LLM; real quality comes only from `run_evals.py` on the real models | Claude | Pending | Tests the plumbing without keys; never reported as model results |
| 27 | Red-flag or below-minimum Skips that are overridden run the assessment then, so proof can still be suggested | Claude | Pending | Keeps the no-LLM-call promise for Skips that aren't overridden |
| 28 | The keyword feed and link fetch use Freelancer.com's public API, built but not yet checked against the live API | Plan; code by Claude | Pending | Day 2 API check; if it fails, those jobs come in by paste |
| 29 | Add login: username + password saved in a Google Sheet, with duplicate prevention by user id. Moves "multi-user login" out of the non-goals | Me | No, replaced by #34 | Each user gets their own data and duplicate checks; accounts survive app restarts in the Sheet |
| 30 | Passwords stored only as a salted PBKDF2-SHA256 hash; the old passphrase becomes the invite code needed to create an account; 5 wrong sign-ins lock the form for 30 seconds; generic "wrong username or password" | Claude; invite code chosen by me | No, replaced by #34 | Strangers on the live link can't sign up or spend the Gemini quota; no plain-text passwords anywhere |
| 31 | Accounts fall back to a local file (data/accounts.json, gitignored) until USERS_SHEET_URL is set; each user's sample workspace is separate | Claude | No, replaced by #34 | The app runs before the Google service account is set up |
| 32 | Double-click starters (`start.bat` / `start.command`) for non-developers | Claude | No, replaced by #33 | Windows warns on any downloaded script, so non-developers use the live link instead; the in-app key setup screen stays for local runs |
| 33 | Non-developers use a live link on Streamlit Community Cloud instead of installing; the local starter stays for developers. Online, the key setup screen is hidden from visitors | Me (no install warnings for non-developers); Claude (setup guard) | Yes | Windows warns on any downloaded script, and a non-developer won't run past that warning |
| 34 | Remove login and sign-up; keep one passphrase box | Me (remove login); Claude (keep the passphrase) | Yes | Accounts were more setup than a five-day quest needs; the passphrase still stops strangers on the live link from spending the Gemini quota |
| 35 | On a busy Gemini model, retry after 3 s and 8 s, then the other Gemini model, then a list of Groq models; add `check_models.py` | Claude, after the first live run failed (F1 in `evals/failures.md`) | Pending | One fallback model name was a single point of failure |

## To verify by hand

- Spot-check three trust scores in [test_cases.md](../evals/test_cases.md) against the plan's rules.
