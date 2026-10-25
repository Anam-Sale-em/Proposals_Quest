# Eval run v2.0.7_20261025-203200

- prompt_version: v2.0.7 · commit: be18265 · LLM mode: live
- Cases passed: **10 of 12**
- Checks passed: 198 of 200
- Drafts needing review after the retry: 2
- Drafts that needed the retry: 4
- Latency per case: p50 88.8 s, p95 123.0 s
- Tokens: 101577 in, 34203 out · list-price cost $0.0000
- LLM errors (retried or fell back): 66

| Case | Type | Expected | Got | Trust (exp → got) | Result | Failed checks |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | representative | Apply | apply:apply | 71 High → 71 High | FAIL | validators_pass |
| T02 | representative | Apply | apply:apply | 58 Medium → 58 Medium | PASS |  |
| T03 | representative | Apply | apply:apply | None Unknown → None Unknown | PASS |  |
| T04 | edge | Apply with questions | apply_with_questions:placeholder | 50 Medium → 50 Medium | PASS |  |
| T05 | edge | Apply | apply:apply | 76 High → 76 High | PASS |  |
| T06 | edge | Apply | apply:apply | 94 Excellent → 94 Excellent | PASS |  |
| T07 | edge | Apply | apply:apply | 71 High → 71 High | PASS |  |
| T08 | failure | Skip: work type | skip:work_type | 73 High → 73 High | PASS |  |
| T09 | failure | Skip: below your minimum | skip:below_minimum | 35 Low → 35 Low | PASS |  |
| T10 | failure | Skip: red flag | skip:red_flag | 15 Red flag → 15 Red flag | PASS |  |
| T11 | failure | Apply | apply:apply | 76 High → 76 High | PASS |  |
| T12 | failure | Apply | apply:apply | 63 High → 63 High | FAIL | validators_pass |

Rubric scores and unsupported claims are filled in by hand in results.csv, then by `scripts/judge.py`.
