# Day 4 results: evaluate, break, harden

**Short answer:** across four fully live runs, v2 got **every decision and every trust score right (48 of 48)**. The one unstable part was how it describes the proof: "I did nearly this" versus "same skills". Two code changes (a vote over three checks, and an evidence rule) cut that from 2 misses per run to 0–1. The final code, run live twice, passed **12 of 12** and **11 of 12** (23 of 24 cases, 399 of 400 checks). Drafts pass the rubric **8 of 9** in the last run, with **0** unsupported claims. Six live failures (F1–F6) and three eval failures (E1–E3) are written up with root causes.

Still to add: real-job timing against the baseline, and proxy-user feedback.

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

## 4. Metrics

| Category | Metric | Plain ChatGPT | v1 | v2 (final code, live) |
| --- | --- | --- | --- | --- |
| Quality | Decisions right on the 12 cases | No decision step | No decision step | **12 of 12** in all four live runs (48 of 48) |
| Quality | Trust scores right | No client check | No client check | **12 of 12** in all four live runs |
| Quality | Proof framing right | — | — | **23 of 24** over the final code's two live runs (10 of 12 per run before #59–#60) |
| Quality | Rubric pass rate | 3 of 3 (T01–T03) | 0 of 5 (agency format) | **8 of 9** in the last run (7 of 9 in the two before) |
| Quality | Unsupported or overstated claims | 0 (+1 borderline) | 5–7 per draft | **0 in 9 drafts** in the last run (2, then 1, in the two before) |
| Quality | Claim check | None | None | 9 of 9 drafts pass; 1 fixed by the automatic retry (T03); 0 left "needs review" |
| Speed | Minutes per proposal, open → send-ready | ~57 (estimate) | 65–85+ | _from the real-job check_ |
| Speed | Pipeline time per job | ~30 s per answer | ~3 min per generation | **Drafted job: p50 ~100–116 s** across the two final runs (87–153 s; outliers of 247 s and 343 s under rate limits). **Skip: 7–35 s** |
| Cost | LLM calls per job | 1 chat + 3+ revisions | Full chain + images | Drafted: 7 (9 with the claim retry). Work-type Skip: 4. Red-flag or below-minimum Skip: 1 |
| Cost | Tokens per drafted job | Subscription | No figure | ~6,500–10,200 in and ~2,300–3,300 out; the 2,000-word spec ~24,000 in / 6,600 out. The vote adds about 40%. **$0 on the free tier** |
| Reliability | Model errors absorbed | — | Token expiry under load | 57 busy or rate-limit errors in each final run, every one retried or sent to the fallback; 0 cases lost |
| Human input | Before the first draft | Job + background written per job | 10 fields | One paste or link, then confirm |
| Human input | Approvals | — | 1 | 2 (confirm details, then the draft); v2 never sends |

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

_Pending: 6–10 fresh jobs, with my call written down before v2 runs._

## 8. Proxy user

_Pending: proxy session notes._

## 9. Where v2 is still weak

- **"How close is this project?" is the hardest call.** It's the only thing that failed in the live runs, and the claim check can't catch an overstated "nearly this". The vote and the evidence rule cut it to 0–1 misses per run; "same records" needs the same evidence rule next.
- **Vague posts get weak drafts.** T04's "questions first" draft is honest now but generic, and the rubric doesn't fit this kind of draft well.
- **Fit questions are still the model's answers**, now voted on three times rather than asked once.
- **Free-tier limits set the speed.** About 2 minutes per drafted job, mostly waiting, and some drafts come from the fallback model when the daily quota runs out.
- **Client data is thin on some platforms.** Freelancer.com's API gives no client history, so trust there rests on what the user copies in.
- **The live app forgets.** Streamlit Cloud resets local files on restart; the sent log has to be downloaded as CSV.
- **Small test set.** 12 synthetic cases on one sample profile; the real-job check is the outside test.
