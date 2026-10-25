# Day 4 results: evaluate, break, harden

**Short answer:** across four fully live runs, v2 got **every decision and every trust score right (48 of 48)**. The one unstable part was how it describes the proof: "I did nearly this" versus "same skills". Two code changes (a vote over three checks, and an evidence rule) cut that from 2 misses per run to 0–1. The final code, run live twice, passed **12 of 12** and **11 of 12** (23 of 24 cases, 399 of 400 checks). Drafts pass the rubric **8 of 9** in the last run by my scoring and **6 of 9** by an independent AI judge, with **0** unsupported claims.

On **7 real jobs** from Upwork, Freelancer.com and Guru, v2 got to a draft I'd send in **10 minutes median (7–14)** from the open job. Plain ChatGPT, timed on 3 of the same jobs, gave a first draft in 7–12 minutes, but **I wouldn't send any of the three**, and it said Apply on a job v2 rightly skipped. So the speed gain to a first draft is small; the gain is that v2's draft is the one I send, and the Skip comes before any writing. Eight failures (F1–F8) and three eval failures (E1–E3) are written up with root causes.

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

**What the swings show:**
- **T04's decision flipped between runs** on the same rules, because the placeholder rule lived only in the prompt. Enforced in code (#55), it has been right in every run since.
- **Each rewording of "similar" moved the failure** between T02, T03 and T07. The label is now decided in code from four yes/no facts (#57, #58).
- **Fully live runs showed that the facts themselves flip.** The vote (#59) fixed T02 once; the evidence rule (#60) fixed T04 for good, because a post that names no tool can't be "nearly this", whatever the model says. What's left is the "same records" fact.
- **Two failures were the test set's fault.** T04 and T09 expected "0 reviews" on client boxes with no reviews line, against v2's rule; corrected and logged (#53).
- **T01 validators (v2.0.3 only)** failed once and passed in every later run; the draft wasn't kept, so the cause isn't confirmed.

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

Agreement per rubric item: goal 92%, specific 100%, honest proof 92%, plan 83%, ask 83%. The pass/fail call matched on 10 of 12 drafts. Every item clears the 80% bar the rubric set for trusting the judge. The two disagreements are both v2 drafts I passed and the judge failed, so the judge is the stricter scorer. The fair reading of v2's draft quality on the test set is **6–8 of 9**, not 8 of 9.

## 4. Metrics

| Category | Metric | Plain ChatGPT | v1 | v2 (final code, live) |
| --- | --- | --- | --- | --- |
| Quality | Decisions right on the 12 cases | No decision step | No decision step | **12 of 12** in all four live runs (48 of 48) |
| Quality | Trust scores right | No client check | No client check | **12 of 12** in all four live runs |
| Quality | Proof framing right | — | — | **23 of 24** over the final code's two live runs (10 of 12 per run before #59–#60) |
| Quality | Rubric pass rate | 3 of 3 (T01–T03), me and the AI judge | 0 of 5 (agency format) | **8 of 9 by me, 6 of 9 by the AI judge** in the last run (7 of 9 by me in the two before) |
| Quality | Unsupported or overstated claims | 0 (+1 borderline) | 5–7 per draft | **0 in 9 drafts** in the last run (2, then 1, in the two before) |
| Quality | Claim check | None | None | 9 of 9 drafts pass; 1 fixed by the automatic retry (T03); 0 left "needs review" |
| Speed | Minutes from the open job to a draft | **7–12, median 10** (3 real jobs, measured); none send-ready | 65–85+ (estimate) | **10 median (7–14)** to send-ready on 6 real jobs, measured, one revision on 3 |
| Speed | Same jobs, side by side | Laravel audit 12 · marketplace MVP 10 | — | Laravel audit 10 · marketplace MVP 7 |
| Quality | Fit call on the same 3 real jobs | Apply on both it was asked about, incl. the healthcare build I'd skip | No fit check | Skip, Skip, Apply: I agreed on the healthcare Skip and overrode the Laravel one |
| Speed | Pipeline time per job | ~30 s per answer | ~3 min per generation | **Drafted job: p50 ~100–116 s** across the two final runs (87–153 s; outliers of 247 s and 343 s under rate limits). **Skip: 7–35 s** |
| Cost | LLM calls per job | 1 chat + 3+ revisions | Full chain + images | Drafted: 7 (9 with the claim retry). Work-type Skip: 4. Red-flag or below-minimum Skip: 1 |
| Cost | Tokens per drafted job | Subscription | No figure | ~6,500–10,200 in and ~2,300–3,300 out; the 2,000-word spec ~24,000 in / 6,600 out. The vote adds about 40%. **$0 on the free tier** |
| Reliability | Model errors absorbed | — | Token expiry under load | 57 busy or rate-limit errors in each final run, every one retried or sent to the fallback; 0 cases lost |
| Human input | Before the first draft | Job + background written per job | 10 fields | One paste or link, then confirm |
| Human input | Approvals | — | 1 | 2 (confirm details, then the draft); v2 never sends |
| Human input | Revision rounds per draft | 3+ | 2–3 | 0 or 1 on the real jobs (1 on 3 of 6) |

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
| F7 | Real job: "I did nearly this" from a booking chatbot on an SEO content job | Same tool (n8n) counted as evidence; the deliverable never compared | Open. Next: platform alone can't make "similar"; records or deliverable must match too |
| F8 | Real jobs: "My goal…", "to shipped", a repeated phrase | Proof line pasted from project text; the claim check checks facts, not wording | Open. Next: code check for these, sent to the automatic retry |
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

**Draft quality on the real jobs, by the AI judge.** The same judge and rubric, run on the real posts with only the projects I gave each draft (`python scripts/judge.py --real private/real_jobs.json`; the posts and projects stay in `private/`). The judge doesn't know which tool wrote which draft. Rubric items in order: goal, specific, honest proof, plan, ask.

| Job | v2 | Plain ChatGPT |
| --- | --- | --- |
| Laravel code audit (v2 had said Skip; I overrode it) | Y Y – Y – · **fail** | – – Y Y Y · **fail** |
| Mobile booking app designer | Y Y Y Y Y · **pass** | not drafted |
| AI marketplace MVP | – Y Y Y Y · **pass** | – Y Y – – · **fail** |
| Complete n8n workflow automation | Y Y Y – Y · **pass** | not drafted |
| **Pass** | **3 of 4** | **0 of 2** |

On the two jobs both drafted, the judge failed ChatGPT's drafts on the goal item both times (restating the client's goal and covering every requirement), plus specifics on the Laravel draft and plan and ask on the marketplace one. v2's one fail is the Laravel audit, the job v2 itself said to Skip. Its proof was "different domain" from the start, and the judge failed it on honest proof and on the ask. Four drafts against two is a small sample, and it's one judge. I read it as "v2 holds up on real posts", not as "v2 beats ChatGPT".

**Draft quality on the real jobs, scored by the AI judge.** Same judge and rubric as the test set, run with `python scripts/judge.py --real private/real_jobs.json`. The posts and my projects stay in `private/`. Each draft was checked only against the projects given for that job. Four jobs had a full post and a known proof project; two of them also had a plain-ChatGPT draft.

| Job | v2 (goal, specific, proof, plan, ask) | ChatGPT |
| --- | --- | --- |
| Laravel code audit (v2 said Skip; I overrode) | fail: Y Y – Y – | fail: – – Y Y Y |
| Mobile booking app designer (v2 said Skip; I overrode) | **pass**: all five | not run |
| AI marketplace MVP | **pass**: – Y Y Y Y | fail: – Y Y – – |
| Complete n8n workflow | **pass**: Y Y Y – Y | not run |
| **Passing** | **3 of 4** | **0 of 2** |

Why each failed, from the judge's reasons (`private/real_judge.csv`):
- **ChatGPT, both jobs:** it never restated the client's goal. The Laravel draft skipped the requested quote and the confidentiality agreement and used no detail unique to the post. The marketplace draft's plan was generic ("get the core flow right") and it ended on "Looking forward to hearing more" instead of a question.
- **v2, Laravel audit:** failed on proof and ask, both for the same reason: the post asked for a fixed-price quote, and v2 wrote "[your price and timeline]" for me to fill in. That placeholder is deliberate, because v2 never sets a price, but scored as generated, the draft doesn't answer the ask.
- **v2, the passing drafts' weak spots:** the marketplace draft didn't cover the portal, admin dashboard, AI layer and tests (item 1). The n8n draft's plan, "kickoff and requirements gathering, then design the architecture", was generic (item 4).

Four drafts on real jobs is a small sample. It points the same way as the test set, and nothing more.

**What didn't** (write-ups in [failures.md](failures.md)):
- **F7, overstated proof on job 2.** "I did nearly this" for a booking chatbot cited on an SEO content pipeline. Both use n8n, so the evidence rule let it through; the revision made it "I completed a similar architecture". This is the same weak spot as E3, now on a real job.
- **F8, sentence slips in the drafts.** Job 6 opens "My goal is to build…" and says "I used React Native to shipped four apps". Job 4 repeats the project's result phrase twice in one sentence. Job 7's proof line is empty: "I used Automation to build systems that operate reliably", where "Automation" is the only shared skill and "operate reliably" isn't in the project. The claim check passes all four, because nothing in them names a fact that isn't there.
- **The drafts read alike.** Five of the six open with "Your goal is to…", and all end with a question and "Let us discuss". Fine for a first draft, but a client reading many proposals would notice.

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

- **"How close is this project?" is the hardest call.** It's the only thing that failed in the live runs, and the claim check can't catch an overstated "nearly this". The vote and the evidence rule cut it to 0–1 misses per run; "same records" needs the same evidence rule next.
- **Vague posts get weak drafts.** T04's "questions first" draft is honest now but generic, and the rubric doesn't fit this kind of draft well.
- **Fit questions are still the model's answers**, now voted on three times rather than asked once.
- **Free-tier limits set the speed.** About 2 minutes per drafted job, mostly waiting, and some drafts come from the fallback model when the daily quota runs out.
- **Client data is thin on some platforms.** Freelancer.com's API gives no client history, so trust there rests on what the user copies in.
- **The live app forgets.** Streamlit Cloud resets local files on restart; the sent log has to be downloaded as an Excel file.
- **Small test set.** 12 synthetic cases on one sample profile, plus 7 real jobs. The real-job set is too small to give a skip accuracy; that needs 30 jobs with my call written down before v2's.
- **Proof built from a shared tool.** Sharing n8n with a past project is enough for "I did nearly this" (F7). Platform alone shouldn't count.
- **Sentence-level slips** pass the claim check (F8). The freelancer still has to read every draft before sending, which is why v2 never sends.
