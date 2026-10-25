# Evaluation package

Frozen on 2026-10-21, before any v2 code existed, so the build couldn't tune the test. One amendment since, logged openly: T04 and T09 expected "0 reviews" on client boxes that show no reviews line, against the extraction rule (null when not shown); both are now null (decision log #53).

Results: [day4-results.md](day4-results.md) · failures: [failures.md](failures.md).

| File | What it holds |
| --- | --- |
| [test_cases.md](test_cases.md) and [test_cases.json](test_cases.json) | 12 test cases and their expected behavior: 3 representative, 4 edge, 5 failure |
| [../fixtures/jobs/](../fixtures/jobs/) | The 12 job inputs, synthetic |
| [../fixtures/profile_sample.json](../fixtures/profile_sample.json) | The synthetic profile they run on |
| [trust_examples.json](trust_examples.json) | The plan's 16 worked trust-score examples, as unit tests |
| [rubric.md](rubric.md) | The 5-item draft rubric and how drafts are scored |
| [metrics.md](metrics.md) | The success metric; quality, speed, cost and human-intervention metrics; guardrails |
| [baseline.md](baseline.md) | The plain-ChatGPT baseline on T01–T03, scored, plus v1's numbers from testing |
| [baseline_prompts.md](baseline_prompts.md) and [baseline_runs/](baseline_runs/) | The fixed ChatGPT prompts and the three raw drafts |
| [../labels/](../labels/) | Templates for the two real-data sets |

## Test sets

| Set | Size | Data | Used for |
| --- | --- | --- | --- |
| Core cases | 12 | Synthetic, frozen | Decisions, drafts, validators and failure handling; v1 against v2 |
| Trust examples | 16 | From the plan | Unit tests for the trust scorer, with no LLM |
| Decision table | 15 cells, both gates and every budget rule | From the plan | Unit tests for the decision function, with no LLM |
| Fresh jobs | 6 | Real jobs from Upwork, Freelancer.com and Guru, run on the live link on Day 5 | Minutes per proposal by stopwatch, v2's call and my override, client trust per platform, draft problems |

## Running the evals

```bash
python scripts/run_evals.py              # every case; cached responses when present, otherwise live
python scripts/run_evals.py --replay     # cached responses only (same result every time, offline)
python scripts/run_evals.py --record     # call the APIs and refresh the cache
python scripts/judge.py evals/results/<run> --hand evals/hand_scores.csv
```

Results land in `evals/results/<prompt_version>_<time>/`: `results.csv`, `summary.md` and `drafts/`. Fill the rubric and unsupported-claim columns by hand, then run the judge.

## Rules

- Evals run on frozen fixtures, never live fetches, so anyone can rerun them.
- Each case runs in a fresh workspace, so one case can't leak into another.
- Every LLM response is cached during evals, so reruns cost no quota.
- Every run logs prompt_version, the git commit, model, latency, tokens, validation results and the decision. Before-and-after tables are keyed by prompt_version.
- Three timed runs each way is directional evidence, so every run is shown, not just the medians.

## Fresh jobs

Six open jobs, run on the live link with my own projects: two pasted from Upwork, three from Freelancer.com (two links, one keyword search), one pasted from Guru. For each I timed opening the job to a draft I'd send, and noted v2's call, what I did with it, the proof it cited and any revision. Results are in [day4-results.md](day4-results.md), section 7; the job posts stay private.

Six jobs show the time and the draft problems. They're too few for a skip accuracy. The next set is 30 jobs, with my own call written down before v2 runs (template: [`../labels/day4_calls_template.csv`](../labels/day4_calls_template.csv)), so v2 can't influence it.

The trust thresholds stay at the plan's values, checked by the 16 worked examples; they aren't tuned on the real jobs.
