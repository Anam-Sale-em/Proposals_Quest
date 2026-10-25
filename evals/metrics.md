# Metrics

**Success:** on the same three jobs (T01–T03), v2's median time from opening a job to a send-ready proposal is below the plain-ChatGPT baseline (about 57 minutes) and v1 (65–85+), every v2 draft passes the rubric, and none carries an unsupported claim. I report the result either way, including if v2 is not faster.

**Result (Day 5), measured on real jobs instead of T01–T03:** v2 got to a draft I'd send in 10 minutes median (7–14) on 5 jobs. Plain ChatGPT got to a first draft in 7–12 on 3 of the same jobs, and none of those was one I'd send, so its time to send-ready is longer but not measured. On the two jobs both drafted, v2 was 2–3 minutes faster. The time target is met, narrowly; the 57-minute estimate below was too high for a first draft. Details: [baseline.md](baseline.md#measured-on-real-jobs-day-5) and [day4-results.md](day4-results.md), section 7.

## North-star

Minutes from opening a job to a send-ready proposal, with zero unsupported claims.

The clock starts when the job is opened and stops when the proposal is ready to send (v1: approved; ChatGPT and v2: final text I'd send). It includes reading the post, judging the client, checking for duplicates, entering the job, picking proof, waiting for generation, reviewing and revising. Every way is timed by the same person, on the same jobs, with the same rule.

## Why it matters

- **Time:** a proposal takes about an hour with plain ChatGPT and 65–85+ minutes with v1, before visuals ([baseline](baseline.md)).
- **Money:** on Upwork, every proposal costs Connects, at $0.15 each ([Upwork](https://www.upwork.com/tools/connects-calculator)). Every bad job v2 rightly skips saves those Connects and the time.
- **Real proof:** v1's agency format built each proposal around a generated sample case study. v2 must cite only the freelancer's real projects.

## Metrics by category

| Category | Metric | How it's measured | Plain ChatGPT | v1 | v2 target |
| --- | --- | --- | --- | --- | --- |
| Quality | Rubric pass rate | 5 items; pass = 4 of 5 with item 3 required. Hand-scored, then judge-scored with labels removed | 3 of 3 raw drafts pass (T01–T03) | 0 of 5 real drafts pass | Every draft passes |
| Quality | Unsupported claims per draft | Counted by hand on every draft | 0 on T01–T03, plus 1 borderline | 5–7 case-study claims per draft (29 across 5 real drafts) | 0 |
| Quality | Decision accuracy | Right decision on the 12 test cases | Drafts every job, no skip path | Drafts every job, no skip path | Reported per case |
| Quality | Skip accuracy (jobs with the fit check on) | v2's decision against my considered call, on 6–10 fresh Day 4 jobs | No skip path | No skip path | Reported |
| Quality | Jobs rightly skipped | Fresh Day 4 jobs I'd apply to at a glance, skipped after reading, that v2 also skipped | None | None | Reported |
| Quality | Trust agreement | v2's trust band against my trust call, on the fresh Day 4 jobs | No client check | No client check | Reported |
| Quality | Claim-check recall | Unsupported claims the claim check catches, against the hand labels | No claim check | No claim check | Reported |
| Speed | Minutes per proposal | T01–T03, plus v2 on 3 fresh Day 4 jobs | About 57 (estimate) | 65–85+ (from testing) | Below both |
| Speed | Pipeline latency, p50 and p95 | Run log | About 30 s per answer | About 3 min per generation | Reported |
| Cost | Tokens and dollars per proposal | Tokens × list price from the run log, reported even while the free tier makes it $0 | Chat subscription | No figure | Reported |
| Cost | Calls avoided on skips | Red-flag and below-minimum jobs skip the assessment and drafting calls | Drafts every job | Full chain on every job | Holds on T09 and T10 |
| Cost | Media spend | Paid image generation per approved proposal | None | 36 frames, 120+ min and paid credits | None (text only) |
| Human intervention | Manual input per job | What I type or paste before the first draft | Job details plus a background written for the job | 10 fields | One link or paste, then a confirm |
| Human intervention | Revision rounds before send | Rounds until the draft is send-ready | 3+ | 2–3 | Reported; fewer is the goal |
| Human intervention | Edits before send | Difference between the AI draft and the text copied out | No figure | No figure | Reported |
| Human intervention | Overrides | Skips I override, each logged | No skips | No skips | Reported |
| Human intervention | Needs review | Drafts that still fail validation after one retry | No checks | No claim or length check | Reported |
| Reliability | Schema failures, retries and rate-limit errors | Run log, across the 12 cases | Not applicable | Contract mismatches; token expiry under load | Reported |

## Guardrails (any failure blocks the release)

- Zero unsupported claims in v2 drafts, checked by hand.
- Every instruction-policy case behaves as specified (T05, T10, T11).
- Nothing loads, and no LLM call runs, without the passphrase.
- Nothing is ever submitted for the user.

## Two weeks after launch

- Proposals sent through v2 (rows in the sent log) against proposals sent outside it.
- Reply rate by trust band and by decision.
- Share of proposals sent with light edits.
- Skips I overrode.
