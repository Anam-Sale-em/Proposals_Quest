# Eval run v2.0.6_20261024-051144

- prompt_version: v2.0.6 · commit: 9c8d70e · LLM mode: cache_first
- Cases passed: **12 of 12**
- Checks passed: 200 of 200
- Drafts needing review after the retry: 0
- Drafts that needed the retry: 0
- Latency per case: p50 0.1 s, p95 71.3 s
- Tokens: 2402 in, 897 out · list-price cost $0.0000
- LLM errors (retried or fell back): 6

| Case | Type | Expected | Got | Trust (exp → got) | Result | Failed checks |
| --- | --- | --- | --- | --- | --- | --- |
| T01 | representative | Apply | apply:apply | 71 High → 71 High | PASS |  |
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
| T12 | failure | Apply | apply:apply | 63 High → 63 High | PASS |  |

Rubric scores and unsupported claims are filled in by hand in results.csv, then by `scripts/judge.py`.
