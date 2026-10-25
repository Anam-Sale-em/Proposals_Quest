# Results: evaluate, break, harden (Days 4–5)

**Short answer:**
- **Decisions:** every decision and every trust score was right in all seven fully live runs (84 of 84).
- **Proof framing ("I did nearly this" or "same skills"):** this was the unstable part. Facts plus rules in code, a vote over three checks and evidence rules got it right on all 12 cases in v2.0.9.
- **Drafts:** an independent AI judge passes 6–7 of v2's 9 test drafts, against 3 of 3 for plain ChatGPT's.
- **Real jobs (final round, v2.0.8):** 6–10 minutes to a draft I'd send, and the judge passed 3 of 4 v2 drafts against 0 of 2 ChatGPT ones.
- **Failures:** ten from real use (F1–F10) and three from eval runs (E1–E3), each with its root cause.

**Versions.** Day 4 ended on v2.0.6. On Day 5 the AI judge's written reasons drove three more:

| Version | What changed | Checks, live | Judge: v2 drafts passing |
| --- | --- | --- | --- |
| v2.0.6 | (Day 4 final) | 12/12, then 11/12 | 6 of 9 |
| v2.0.7 | Concrete plans, every deliverable, one question at the end, wording checks (F8), build tools aren't evidence (F7) | 10/12, both on a new check's false alarm; 12/12 after fixing the check | 5 of 9 |
| v2.0.8 | The "nearly this" line names the real project, never an invented client type | 10/12 (T02 "same records" flip, T11 repeated phrases) | 7 of 9 |
| **v2.0.9** | Each requirement said once; the platform's character limit; checks for restated requirements and copied proof (F9); "similar" needs every check to agree; the override path uses the proof rules (F10) | **11/12** (T05: the proof still copies the project's text, flagged and shown to the user) | **6 of 9** |

Plain ChatGPT's three test drafts passed the judge 3 of 3 every time. **v2.0.9 is the submitted version.** It has the most checks passing, it fixes a real bug (F10), and its judge score is within the judge's own noise of v2.0.8's.

**How much to trust a one-draft difference:** the judge isn't fully repeatable. The cache keys on the prompt version, so the v2.0.9 judge run re-scored the old v2.0.6 real-job drafts from scratch. Same drafts, same judge, and one of four changed its verdict (the marketplace draft, pass to fail). So 6 versus 7 of 9 is noise. The changes that held across runs are the ones I trust: no invented client types from v2.0.8 on, and no wording slips from v2.0.7 on.

**Against plain ChatGPT on real jobs:** timed on 3 of the same jobs, ChatGPT gave a first draft in 7–12 minutes. I wouldn't have sent any of the three, and it said Apply on a job v2 skipped and I'd skip too. So v2 is only a little faster to a first draft. The gain is that its draft is the one I send, and the Skip comes before any writing. Details in section 7.

## 1. Test-set results

Every run's raw output is in `evals/results/<version>_<time>/` (`summary.md`, `results.csv`, `drafts/`).

| Case | Type | What it tests | Expected | Live 22:14 (one check) | Live 22:40 (vote) | Live 23:29 (final code) | **Live 00:05 (final code, again)** |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | representative | n8n build matching a sample project | Apply · 71 High · P1 similar | PASS | PASS | PASS | **PASS** |
| T02 | representative | HubSpot ↔ PostgreSQL sync, no HubSpot project | Apply · 58 Medium · P2 same skills | FAIL: similar | PASS | FAIL: similar | **PASS** |
| T03 | representative | Freelancer.com job, payment flag only | Apply · Unknown · P2 similar | PASS | PASS | PASS | **PASS** |
| T04 | edge | Two-line vague post, $5 fixed | Apply with questions · P1 same skills | FAIL: similar | FAIL: similar | PASS | **PASS** |
| T05 | edge | Post says start with "blue whale" | Apply · 76 High · P1 similar | PASS | FAIL: P3 picked | PASS | **PASS** |
| T06 | edge | ~2,000-word spec, 3 screening questions | Apply · 94 Excellent | PASS | PASS | PASS | **PASS** |
| T07 | edge | Whole-page paste with other jobs and footer | Apply · 71 High | PASS | PASS | PASS | **PASS (after one retry)** |
| T08 | failure | Logo job | Skip: work type | PASS | PASS | PASS | **PASS** |
| T09 | failure | Full CRM for $80 | Skip: below minimum | PASS | PASS | PASS | **PASS** |
| T10 | failure | Top client who asks to move to WhatsApp | Skip: red flag | PASS | PASS | PASS | **PASS** |
| T11 | failure | Post tells the AI to claim 10 years | Apply, claim refused | PASS | PASS | PASS | **PASS** |
| T12 | failure | Same job pasted twice | Apply, second paste blocked | PASS | PASS | PASS | **PASS** |
| | | | **Cases** | 10/12 | 10/12 | 11/12 (199/200) | **12/12** (200/200) |

In all four live runs: every decision and trust score right, every red flag, refused instruction and duplicate handled, and no draft left "needs review".

**What still flips:** the eval CSV now records each project's four facts and where the three checks split. In the 23:29 run, the three checks split on "same records" in 6 of the 9 drafted jobs, and the model said P2's inventory records match T02's contacts, so the label became "similar". "Same records" is the least reliable fact; T01 depends on it legitimately (leads and leads), so it can't simply be dropped. The next step is the evidence rule for records too: the record type must appear in both texts.

**How live each run was:** the runner reuses a saved answer for an identical prompt (cache-first). Each new prompt version's first run was live; `--record` forces every call live. The 22:14, 22:40, 23:29 and 00:05 runs were fully live. 23:29 and 00:05 ran the same code, so together they show the final system's variance: one framing miss in 24 cases.

## 2. Before and after

| Run | Prompt | Mode | Cases | Failed |
| --- | --- | --- | --- | --- |
| Before (`7b1a3b8`) | v2.0.0 | live | **9/12** | T02 framing · T04 decision, placeholder, proof, framing, draft, reviews · T09 reviews |
| After F2–F6 fixes | v2.0.3 | live | 7/12 | T01 validators · T02 framing · T03 proof · T04 reviews, framing · T09 reviews |
| Test-set fix, stricter "similar" | v2.0.4 | live | 10/12 | T03 framing · T04 decision, placeholder, proof, framing, draft |
| Placeholder rule in code, "similar" reworded | v2.0.5 | live | 9/12 | T03 framing · T04 proof, framing · T07 proof, framing |
| Proof label from 4 facts | v2.0.6 | live | 11/12 | T04 proof |
| Tie-break on the post's own tags | v2.0.6 | saved answers | 12/12 | none |
| Same code, fully live | v2.0.6 | live | 10/12 | T02 framing · T04 framing |
| Majority vote over 3 checks (#59) | v2.0.6 | live | 10/12 | T04 framing · T05 proof |
| Evidence rule for "similar", tie-break on the post's tools (#60) | v2.0.6 | live | 11/12 | T02 framing |
| Same code, live again | v2.0.6 | live | **12/12** | none |
| Concrete plans, deliverables, one question, wording checks, F7 rule (#104–#106) | v2.0.7 | live | 10/12 | T01, T12 validators: the new repeated-phrase check flagged the client's own field list and workflow name |
| Repeated-phrase check skips the post's own phrases (#107) | v2.0.7 | same live answers, re-checked | 12/12 | none |
| "Nearly this" names the real project (#108) | v2.0.8 | live | 10/12 | T02 framing ("same records" flipped, E3) · T11 validators (the draft repeats long phrases, F9) |
| Say each requirement once, copy checks, unanimous "similar", override uses the rules (#109–#111) | v2.0.9 | live | **11/12** | T05 validators (the proof copies 12+ words of the project; the retry didn't fix it) |

**What the swings show:**
- **T04's decision flipped between runs** on the same rules, because the placeholder rule lived only in the prompt. Enforced in code (#55), it has been right in every run since.
- **Each rewording of "similar" moved the failure** between T02, T03 and T07. The label is now decided in code from four yes/no facts (#57, #58).
- **Fully live runs showed that the facts themselves flip.** The vote (#59) fixed T02 once; the evidence rule (#60) fixed T04 for good, because a post that names no tool can't be "nearly this", whatever the model says. What's left is the "same records" fact.
- **Two failures were the test set's fault.** T04 and T09 expected "0 reviews" on client boxes with no reviews line, against v2's rule; corrected and logged (#53).
- **T01 validators (v2.0.3 only)** failed once and passed in every later run; the draft wasn't kept, so the cause isn't confirmed.

- **v2.0.7 didn't improve the drafts by the judge's count** (6 → 5 of 9), even though every targeted fix landed. Its reasons named the real cause: the old template asked for a client type, so the model invented one ("for a sales team"). v2.0.8 fixed that and moved to 7 of 9.

**Lesson:** a judgment left to the model changes with every run and every rewording. Facts plus rules in code make it explainable. Voting makes it steadier. A check against the text makes it hold.

## 3. Draft quality: rubric scores

Scored against the [rubric](rubric.md): pass = 4 of 5 with item 3 (honest proof) required. Per-item scores and notes for all three runs: [rubric_scores_live_v2.0.6.csv](rubric_scores_live_v2.0.6.csv).

| Case | 22:14 (one check) | 23:29 (final code) | **00:05 (final code)** | Notes on the 00:05 draft |
| --- | --- | --- | --- | --- |
| T01 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | Every requirement, five concrete steps |
| T02 | ❌ 3/5 | ❌ 4/5, item 3 failed | ✅ 5/5 | Honest now: "Different domain, same core work"; README covered |
| T03 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | "for a warehouse database" is odd wording |
| T04 | ❌ 0/5 | ❌ 2/5 | ❌ 1/5 | Honest proof, but generic, no plan, opens "My goal is…" and ends on the proof |
| T05 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | "blue whale" first; asks for the exact Airtable fields |
| T06 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | All three screening questions answered |
| T07 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | Opening sentence repeats itself |
| T11 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | No "10 years" claim |
| T12 | ✅ 5/5 | ✅ 5/5 | ✅ 5/5 | Names all six workflows |
| **Pass** | 7 of 9 | 7 of 9 | **8 of 9** | |
| **Unsupported or overstated claims** | 2 | 1 | **0** | |

- **Honest proof improved run by run:** overstated claims went 2 → 1 → 0. In the 00:05 run every draft frames its proof correctly, including T02 ("Different domain, same core work") and T04.
- **The claim check can't catch an overstated "nearly this"**, because it checks that a claim traces to a real project, not how close it is. The facts-plus-rules approach (#57–#60) is what fixed it.
- **T04 still fails:** a "questions first" draft for a post with no details can't be specific or name concrete steps, so the rubric fits it badly. But the draft is also weak: it should open with the client's goal and end on the question.
- **Style issues on passing drafts:** a repeated opening (T07), "My goal" where it should be "Your goal" (T04, T07), and odd client wording ("for a warehouse database"). Small, but a freelancer would fix them before sending; the edit share logged at send time measures this.
- **Against the baseline:** plain ChatGPT's raw drafts passed 3 of 3 on T01–T03 with 0 unsupported claims. v2 passed 3 of 3 with 0 in the 00:05 run, but 2 of 3 in the two runs before it. Quality now holds, but not every run.

**Checked by an AI judge.** My scores above were a first pass by AI that I checked, not blind. So the same 12 drafts (9 from v2 in the 00:05 run, 3 from ChatGPT) were scored by the judge in `scripts/judge.py`: a Groq model from a different family than the drafting models, with no labels.

| | Me | AI judge |
| --- | --- | --- |
| v2 drafts passing | 8 of 9 | **6 of 9** |
| ChatGPT drafts passing | 3 of 3 | 3 of 3 |

**Judge on v2.0.7 and v2.0.8 (same judge, same rubric):**

| Case | v2.0.7 | v2.0.8 | v2.0.9 | Why it failed |
| --- | --- | --- | --- | --- |
| T01, T02, T03, T12 | pass | pass | pass | |
| T11 | pass | pass | fail | v2.0.9: the draft uses the Gemini API (from my project) where the post lists OpenAI, without saying so |
| T05, T07 | fail | **pass** | **pass** | v2.0.7: "I did nearly this for a sales team / sales operations client" on a lead-intake project, which the judge called misleading |
| T04 | fail | fail | fail | Two-line post: nothing specific to quote, a generic first step, two questions at the end |
| T06 | fail | fail | fail | The 2,000-word spec: the draft leans on the three screening answers and names no first step |
| **Passing** | **5 of 9** | **7 of 9** | **6 of 9** | v2.0.6 was 6 of 9 |

Agreement per rubric item (v2.0.6 run, against my scores): goal 92%, specific 100%, honest proof 92%, plan 83%, ask 83%. The pass/fail call matched on 10 of 12 drafts. Every item clears the 80% bar the rubric set for trusting the judge. The two disagreements are both v2 drafts I passed and the judge failed, so the judge is the stricter scorer. On v2.0.6, the fair reading of draft quality was **6–8 of 9**, not 8 of 9.

## 4. Metrics

| Category | Metric | Plain ChatGPT | v1 | v2 (final code, live) |
| --- | --- | --- | --- | --- |
| Quality | Decisions right on the 12 cases | No decision step | No decision step | **12 of 12** in all seven live runs (84 of 84), v2.0.6 to v2.0.9 |
| Quality | Trust scores right | No client check | No client check | **12 of 12** in all seven live runs |
| Quality | Proof framing right | — | — | 23 of 24 over v2.0.6's two final runs; 11 of 12 on v2.0.8 (T02's "same records" flip); **12 of 12 on v2.0.9** |
| Quality | Rubric pass rate | 3 of 3 (T01–T03), me and the AI judge | 0 of 5 (agency format) | AI judge: **6 of 9 on v2.0.9**, 7 on v2.0.8, 5 on v2.0.7, 6 on v2.0.6 (8 of 9 by my scoring on v2.0.6); about ±1 is judge noise |
| Quality | Unsupported or overstated claims | 0 (+1 borderline) | 5–7 per draft | **0 in 9 drafts** in v2.0.6's last run, counted by hand (2, then 1, in the two before) |
| Quality | Claim check | None | None | v2.0.6: 9 of 9 pass. v2.0.9: 8 of 9 pass, 1 left "needs review" (T05's proof copies the project, shown to the user as a warning) |
| Speed | Minutes from the open job to a draft | **7–12, median 10** (3 real jobs, measured); none send-ready | 65–85+ (estimate) | **6–10, median 8** to send-ready on the v2.0.8 round, revision included (10 median, 7–14, on the earlier v2.0.6 round) |
| Speed | Same jobs, side by side | Laravel audit 12 · marketplace MVP 10 | — | Laravel audit 10 · marketplace MVP 7 |
| Quality | Fit call on the same 3 real jobs | Apply on both it was asked about, incl. the healthcare build I'd skip | No fit check | Skip, Skip, Apply: I agreed on the healthcare Skip and overrode the Laravel one |
| Speed | Pipeline time per job | ~30 s per answer | ~3 min per generation | **Drafted job: p50 ~100–116 s** across the two final runs (87–153 s; outliers of 247 s and 343 s under rate limits). **Skip: 7–35 s** |
| Cost | LLM calls per job | 1 chat + 3+ revisions | Full chain + images | Drafted: 7 (9 with the claim retry). Work-type Skip: 4. Red-flag or below-minimum Skip: 1 |
| Cost | Tokens per drafted job | Subscription | No figure | ~6,500–10,200 in and ~2,300–3,300 out; the 2,000-word spec ~24,000 in / 6,600 out. The vote adds about 40%. **$0 on the free tier** |
| Reliability | Model errors absorbed | — | Token expiry under load | 57 busy or rate-limit errors in each final run, every one retried or sent to the fallback; 0 cases lost |
| Human input | Before the first draft | Job + background written per job | 10 fields | One paste or link, then confirm |
| Human input | Approvals | — | 1 | 2 (confirm details, then the draft); v2 never sends |
| Human input | Revision rounds per draft | 3+ | 2–3 | 0 or 1 on the real jobs (v2.0.8 round: 1 on 2 of 3) |

Most of the ~2 minutes is waiting on the free tier: Gemini 3.8 Flash allows 5 calls a minute and about 20 a day, so the client throttles itself, and busy or quota errors move calls down the chain.

## 5. Failures and root causes

Full write-ups in [failures.md](failures.md).

| # | Failure | Root cause | Fix |
| --- | --- | --- | --- |
| F1 | First live run: every model failed | Gemini busy (503), and the only fallback model wasn't available to the key | Busy retries (3 s, 8 s), then the other Gemini model, then a list of Groq models; `check_models.py`. The final live run absorbed 57 such errors |
| F2 | A portfolio request was refused as a "claim" | The extraction prompt's "claim" definition was too broad | Narrowed to orders to assert a fact; portfolio requests become requirements |
| F3 | A plan-only draft ignored a request for past work, silently | Empty project library; nothing told the user | Warning on plan-only drafts, naming the unanswered request |
| F4 | "API" flagged on a post asking for REST APIs | Names check: no plurals, generic words treated as tools | Plural matching, generic-word list |
| F5 | The draft's honest "new for me" was flagged | v2 told the draft to be honest, then the claim check flagged it | Claim check judges only past-work sentences |
| F6 | $40–150/hour judged as a $150 total | The model saw the raw budget text without "Hourly" | Budget given in plain words; hourly judged as a rate |
| F7 | Real job: "I did nearly this" from a booking chatbot on an SEO content job | Same tool (n8n) counted as evidence; the deliverable never compared | **Fixed** (v2.0.7–v2.0.8): a shared build tool isn't evidence (#105), and the line names the real project (#108). The judge's honest-proof fails on T05 and T07 went away |
| F8 | Real jobs: "My goal…", "to shipped", a repeated phrase | Proof line pasted from project text; the claim check checks facts, not wording | **Partly fixed** (v2.0.7): "My goal", broken verbs and pasted repeats are checked in code and retried (#106, #107); none appeared in v2.0.8's drafts. Still open: the proof line copies the project's own wording (F9) |
| F9 | v2.0.8: drafts restate the post (T11 repeats two long phrases; a real n8n draft says "production-ready n8n workflow file (JSON) with clear node labels" twice) and copy the project's own sentence as the proof | v2.0.7's draft order (goal, every deliverable, then steps) invites repeats; the repeat check skips the post's own phrases (#107), and nothing checks copying from the project | Mostly fixed in v2.0.9 (#111): no repeated requirements in any v2.0.9 draft. Still open: the model sometimes copies the project's text (T05), which the new check flags and the retry didn't fix |
| F10 | Real SEO job: after an override, "I did nearly this" for the booking chatbot again | The override path kept the model's own label and skipped every proof rule | Fixed (#109): one labelling function for both paths |
| E1 | T04's decision flipped between runs | The placeholder rule lived only in the prompt | Enforced in code (#55) |
| E2 | Proof framing flipped with every rewording | One holistic label from a small model | Four facts plus a rule in code (#57, #58) |
| E3 | Fully live runs: single facts flipped ("same platform", "same records") | One guess per fact, with nothing to check it against | Majority of three checks, confidence shown (#59); "similar" needs a specific tool named in both texts (#60). Still open: "same records" (T02) |

## 6. Reliability measures in place

| Measure | Where |
| --- | --- |
| Retries | Busy model: 3 s and 8 s waits, then fallback; a schema failure gets one repair attempt |
| Fallbacks | Gemini 3.8 Flash ↔ 3.5 Flash-Lite, then Groq gpt-oss-120b, then gpt-oss-20b |
| Structured outputs | One Pydantic schema per LLM step |
| Validation | Claim check (numbers, names, past work, voice, years, instructions, screening, length), with one automatic retry |
| Rules in code | Trust score, budget gate, fit × trust table, placeholder rule, proof label, red flags |
| Confidence shown | Trust coverage ("2 of 6 fields"), Unknown when hires or spend are missing, the three fit checks' agreement, link check in words |
| Human approval | Confirm the extracted details; review the draft; override any Skip (logged); v2 never sends |
| Logs | Per-job events, settings change log, run logs with model and prompt version, eval CSV with each project's facts |

## 7. Real-job check (fresh jobs)

Seven jobs open on Day 5: two from Upwork (pasted), four from Freelancer.com (three by link, one from keyword search) and one from Guru (pasted). All run on the live link with my own projects. Minutes are by stopwatch, from opening the job to a draft I'd send, including any revision.

| # | Job | Platform | Client trust | v2's call | What I did | Proof cited | Revisions | Minutes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Senior Laravel & AI Engineer, code audit ($500–1k fixed) | Guru | Medium (45) | Skip: not the kind of work I do | Overrode, wrote the draft | Chosen by me, led with my AI chatbot agent: "Different domain, same core work" | 0 | 10 |
| 2 | SEO autopilot on n8n + Sanity CMS | Freelancer.com, link | High (5.0, 14 reviews) | Apply | Wrote the draft | v2's pick, AI chatbot agent: "I did nearly this" | 1 ("more professionally") | 7 |
| 3 | Full-stack AI developer, healthcare SaaS ($25–30/hr) | Upwork | — | Skip | Agreed, no draft | — | — | — |
| 4 | AI agent & n8n automation specialist ($20–35/hr) | Upwork | $1.9K spent, 5 hires | Apply | Wrote the draft | v2's pick, my proposal-generation app: "Different domain, same core work" | 1 (more detail, "exaggerate") | 11 |
| 5 | Mobile booking app UX/UI designer ($25–50/hr) | Freelancer.com, link | Can't rate (0 reviews) | Skip | Overrode, wrote the draft | v2's pick, React Native apps: "Different domain, same core work" | 1 ("warmer and friendly") | 14 |
| 6 | AI marketplace MVP (₹12,500–37,500) | Freelancer.com, search | Can't rate (0 reviews) | Apply: medium fit | Wrote the draft | v2's pick, React Native apps: "Different domain, same core work" | 0 | 7 |
| 7 | Complete n8n workflow automation ($750–1,500) | Freelancer.com, link | Payment verified, 0 reviews | Apply | Wrote the draft | Diu, my content automation project: "Different domain, same core work" | 0 | 10 |

**Time:** 10 minutes median over the 6 drafted jobs (7, 7, 10, 10, 11, 14), from the open job to a draft I'd send. Finding the job isn't included: 5–7 minutes on the platform either way, about 3 through v2's Freelancer.com search. The proxy user also got his first proposal in about 10 minutes.

**Against plain ChatGPT on the same jobs** (stopwatch, full steps in [baseline.md](baseline.md#measured-on-real-jobs-day-5)):

| Job | ChatGPT | v2 |
| --- | --- | --- |
| Laravel code audit (Guru) | 12 min, one revision, still not one I'd send; no fit check because I forgot to ask | 10 min to a draft I'd send (after overriding the Skip) |
| Healthcare SaaS build (Upwork) | 7 min: "Apply, 6.5/10" and a draft | Skip in one line, which I agreed with |
| AI marketplace MVP (Freelancer.com) | 10 min, reads AI-written, not like me | 7 min to a draft I'd send |

My Day 1 estimate of about 57 minutes was too high for a first draft: ChatGPT gets one in 7–12. It assumed 3+ revision rounds to reach send-ready, and in the measured runs I stopped before that because the drafts still didn't sound like me. v2 is a little faster to a draft, and its draft is the one I'd send.

**What held up:**
- **The Skips match the posts.** A healthcare SaaS build, a Figma-only design job and a Laravel code audit are not the work I do, and v2 said so in one line each. I overrode two of them to get a draft; both drafts could only offer "different domain" proof, which is the honest framing.
- **No invented facts, even when asked.** On job 4 I asked the revision to "exaggerate my project". It added adjectives ("expertly", "meticulous") but no new numbers, tools or clients.
- **No price set for me.** The Guru client asked for a fixed-price quote; the draft left "[your price and timeline]" for me to fill in.
- **The client box per platform worked:** Guru's paid jobs and invoices gave Medium (45), Freelancer.com's 5.0 and 14 reviews gave High, and the two Freelancer.com clients with no reviews read "can't rate" instead of a guess.
- **Revisions changed only what I asked.** Each revised draft kept the plan and the project and changed the tone.

**Draft quality on the real jobs, scored by the AI judge.** Same judge and rubric as the test set, run with `python scripts/judge.py --real private/real_jobs.json`. The posts and my projects stay in `private/`. Each draft was checked only against the projects given for that job. Items in order: goal, specific, honest proof, plan, ask. The latest run of the judge is shown.

| Job | **v2.0.8** | Plain ChatGPT | v2.0.6 (earlier round) |
| --- | --- | --- | --- |
| Laravel code audit | Skip held, no draft | fail: – – Y Y Y | fail: Y Y – Y – (Skip I overrode; quote left as "[your price and timeline]") |
| Mobile booking app designer | Skip held, no draft | — | **pass**: Y Y Y Y Y (Skip I overrode) |
| AI marketplace MVP | **pass**: Y Y Y Y Y (plan only, after my override) | fail: – Y Y – – | fail: – Y Y – – (passed in the first judge run) |
| Complete n8n workflow | **pass**: Y Y Y Y Y | — | **pass**: Y Y Y – Y |
| AI agent & n8n specialist | **pass**: Y Y Y Y Y | — | — |
| n8n SEO autopilot | fail: Y Y – – Y (the F10 draft: "nearly this" after an override) | — | — |
| **Passing** | **3 of 4** | **0 of 2** | 2 of 4 |

Why the fails failed, from the judge's reasons (`private/real_judge.csv`):
- **ChatGPT, both jobs:** it never restated the client's goal. The Laravel draft skipped the requested quote and the confidentiality agreement and used no detail unique to the post. The marketplace draft's plan was generic ("get the core flow right") and it ended on "Looking forward to hearing more" instead of a question.
- **v2.0.6, Laravel audit:** the post asked for a fixed-price quote, and v2 left "[your price and timeline]" for me to fill in. That's deliberate, because v2 never sets a price, but scored as generated, the draft doesn't answer the ask. The confirm screen now asks for the price first (#103).
- **v2.0.8, SEO autopilot:** the overstated "I did nearly this" from F10, plus a plan that repeats the deliverables. Both are fixed in v2.0.9.

Ten drafts on six real jobs is a small sample, and the judge moves by about one draft in four between runs. It points the same way as the test set, and nothing more.

**What didn't** (write-ups in [failures.md](failures.md)):
- **F7, overstated proof on job 2.** "I did nearly this" for a booking chatbot cited on an SEO content pipeline. Both use n8n, so the evidence rule let it through; the revision made it "I completed a similar architecture". This is the same weak spot as E3, now on a real job.
- **F8, sentence slips in the drafts.** Job 6 opens "My goal is to build…" and says "I used React Native to shipped four apps". Job 4 repeats the project's result phrase twice in one sentence. Job 7's proof line is empty: "I used Automation to build systems that operate reliably", where "Automation" is the only shared skill and "operate reliably" isn't in the project. The claim check passes all four, because nothing in them names a fact that isn't there.
- **The drafts read alike.** Five of the six open with "Your goal is to…", and all end with a question and "Let us discuss". Fine for a first draft, but a client reading many proposals would notice.

### Second round on v2.0.8

Six jobs from the first round, run again on v2.0.8. Finding the job is timed on its own; "total" runs from adding the job in v2 to a draft I'd send, revision included. The line under each draft records v2's own time for the fit check and the draft.

| Job | Find | v2's call | What I did | v2's time | Total | Revisions |
| --- | --- | --- | --- | --- | --- | --- |
| Complete n8n workflow (Freelancer.com) | 3 min | Apply, high fit | Wrote it, citing my AI chatbot agent | fit check 10 s, draft 1 min 6 s | 8 min | 1 ("warmer, more detail") |
| AI agent & n8n specialist (Upwork) | 3 min | Apply, high fit, client Medium (48) | Wrote it, citing my AI chatbot agent | — | 6 min | 0 |
| AI marketplace MVP (Freelancer.com) | — | **Skip:** low fit, the scope isn't realistic for $131–395, no close project | Overrode it to try anyway; then added a project and rewrote | fit check 10 s, draft 1 min 41 s | 10 min | 1 (rewrite with a project) |
| Laravel code audit (Guru) | — | Skip: not my kind of work, 0 of 5 skill tags | **Agreed** this time, no draft | — | — | — |
| Mobile booking app UX/UI designer (Freelancer.com, keyword search) | 3 min | Skip: a design job, and I'm a developer, not a UI/UX designer | No draft this time | — | — | — |
| n8n SEO autopilot (Freelancer.com, keyword search) | 5 min | Skip: below my minimum ($16–132 against $200); client High (76) | Overrode it: the budget is fine for me | fit check 0 s (none ran), draft 1 min 42 s | — | 0 |

**What changed from the first round:**
- **The marketplace call got stricter, and better.** v2.0.6 said Apply. v2.0.8 said Skip because the budget can't cover the scope, which is the same warning plain ChatGPT gave. After my override it said plainly that no project was close enough, wrote a plan-only draft and called the marketplace work "new for me".
- **Both work-type Skips held** (the Laravel audit and the design-only job), each with a one-line reason naming what the post asks for and what I do. On v2.0.6 I overrode both; this time I left them.
- **No "My goal", no broken verbs, no invented client type** in the three new drafts. Each opens on the client's goal, lists the deliverables and ends on one question.
- **Still there (F9):** the n8n draft says "production-ready n8n workflow file (JSON) with clear node labels" twice, and both n8n drafts copy the chatbot project's "What I did" almost word for word. Asked to be "warmer, with more detail", the revision only added "Hello there!".
- **The SEO job broke two things (F9, F10).** After my override, the draft said "I did nearly this" for the booking chatbot again, because the override path skipped the proof rules (F10). It also listed every deliverable and then repeated three of them word for word as the plan, which made it too long for Freelancer.com. The draft page flagged both, the length and the repeated phrase. Both are fixed in v2.0.9.
- **Time:** 6–10 minutes from adding the job to send-ready, plus 3–5 minutes to find a job.

## 8. Proxy user

**Who:** a computer science student learning Django. Not yet a freelancer or a developer. That makes him a harder test than an experienced freelancer: no project library, no Upwork habits.

**What he ran, on the live link:**
1. A real Upwork job (Python + OpenAI lead qualification for an existing app and CRM, $400–600 fixed), pasted.
2. A real Freelancer.com job (a custom e-commerce storefront), fetched by link.

It took him about **10 minutes** to open the app, pick a job he liked and get a proposal. He asked me two things, what "exclude terms" means and what "client history" is; everything else he handled alone.

**What worked:**
- With no projects in his library, both drafts said so honestly ("This part is new for me, here's how I'd de-risk it") instead of inventing experience.
- The drafts used only his own profile: the storefront draft's "I usually focus on editing" comes from the skills he entered, not from the model.
- The drafts answered the posts' own asks: three to four concrete integration steps, retries and duplicate handling, a question back to the client.
- The Solution Brief flagged the storefront budget as far too low for the scope and suggested asking about a template or CMS.

**What broke or confused him, and what changed:**

| Finding | Change |
| --- | --- |
| "Exclude terms" on the search tab was confusing | Removed (#62); whole-phrase matching already keeps unrelated jobs out |
| "It decides nothing; the fit check runs once you pick a job" read as jargon | Rewritten: "Find new Freelancer.com jobs by keyword. Pick one, and v2 checks it and writes the proposal" (#68) |
| The Upwork post said "Confirm your fixed price and timeline", and the draft confirmed "$400–$600 and 5–7 days" for him | v2 never commits to a price or timeline: it uses the freelancer's own note, or writes "[your price and timeline]" with a reminder to fill it in (#67) |
| The Solution Brief showed "131.65 – 131.65–394.95" (dollar signs read as maths) | Fixed (#68) |
| He asked what "client history" is and where to get it | Both the paste form and the confirm screen now say it's the **About the client** section of the job's page (below the skills on Upwork, on the right on Freelancer.com), with an Open job button right there (#69) |
| The post asked "Share one AI or API integration you've built"; he had none to share | Handled as designed: the draft warns that no past work is cited and names the unanswered request (F3) |
| His storefront draft said "as I usually focus on editing" | Checked: editing is in his own skills, so the claim is grounded, not invented |



## 9. Where v2 is still weak

- **"How close is this project?" is the hardest call.** The "same records" fact still flips between live runs (T02 on v2.0.8). The obvious rule, "the record type must appear in both texts", would also flip T05's frozen answer, so it needs a better test than a word match.
- **Vague posts get weak drafts.** T04's "questions first" draft is honest now but generic, and the rubric doesn't fit this kind of draft well.
- **Fit questions are still the model's answers**, now voted on three times rather than asked once.
- **Free-tier limits set the speed.** About 2 minutes per drafted job, mostly waiting, and some drafts come from the fallback model when the daily quota runs out.
- **Client data is thin on some platforms.** Freelancer.com's API gives no client history, so trust there rests on what the user copies in.
- **The live app forgets.** Streamlit Cloud resets local files on restart; the sent log has to be downloaded as an Excel file.
- **Small test set.** 12 synthetic cases on one sample profile, plus 7 real jobs. The real-job set is too small to give a skip accuracy; that needs 30 jobs with my call written down before v2's.
- **Drafts restate the post and copy the project's wording (F9).** v2.0.7's order (goal, every deliverable, steps) made drafts complete, and the judge's score went up, but longer and repetitive. "Warmer" revisions change too little.
- **The judge still fails 2 of 9 test drafts:** the vague two-line post (T04) and the 2,000-word spec (T06).
- **The freelancer still reads every draft before sending,** which is why v2 never sends.
