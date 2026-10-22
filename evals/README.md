# Evaluation package

Frozen on 2026-10-21, before any v2 code exists, so the build can't tune the test.

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
| Fresh jobs | 6–10 | Real Upwork jobs pasted on Day 4, kept private | Skip accuracy, trust agreement, jobs rightly skipped, and 3 timed v2 runs |

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

## Day 4 fresh jobs: calls before v2

On Day 4 I open 6–10 new Upwork jobs, at least 3 of which I'd skip. For each job, before running v2 on it, I write down three calls in `private/day4_calls.csv` (header in [`../labels/day4_calls_template.csv`](../labels/day4_calls_template.csv)):

1. **Glance call**, from the title and budget only: Apply or Skip.
2. **Considered call**, after reading the whole post: Apply, Apply with questions or Skip.
3. **Trust call**, from the client box: would I work with this client? Yes, Unsure or No.

Then I paste the job into v2 and record its decision and trust band next to my calls. Because my calls come before v2's answer on each job, v2 can't influence them. Three of the Apply jobs similar to T01–T03 are also timed with a stopwatch.

Trust calls map to bands like this, fixed today: Yes = Medium or above, Unsure = Low or Unknown, No = Red flag.

The trust thresholds stay at the plan's values, checked by the 16 worked examples; they aren't tuned on extra labels.
