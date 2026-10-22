# Test cases

12 cases, frozen on 2026-10-21 before any v2 code exists: 3 representative, 4 edge and 5 failure. They all run on the synthetic sample profile (`fixtures/profile_sample.json`, minimums $30/hr and $200 fixed) from frozen fixtures, so anyone can rerun them. Full expectations, including what each case must do to pass, are in [`test_cases.json`](test_cases.json).

| ID | Type | Case | Expected behavior | Covers |
| --- | --- | --- | --- | --- |
| T01 | Representative | n8n build that matches a sample project; High-trust client | Apply; draft cites P1; numbers only from P1's result or the post | Proof |
| T02 | Representative | HubSpot and PostgreSQL sync; no HubSpot project in the profile | Apply; same-skills framing with P2; never claims HubSpot experience | Proof |
| T03 | Representative | Freelancer.com job pasted; the page shows a payment-verified flag only | Trust Unknown (1 of 6 fields) with 'check the client manually'; Apply with P2 | Trust, Intake |
| T04 | Edge | Two-line vague post with a $5 fixed budget | Apply with questions; card says the budget looks like a placeholder | Judging |
| T05 | Edge | Post asks applicants to start with 'blue whale' | Apply; draft starts with 'blue whale'; the validator confirms it | Instructions |
| T06 | Edge | About 2,000-word spec with three questions for applicants | Apply; draft inside the length limit; answers all three questions; latency logged | Length |
| T07 | Edge | Whole-page paste with similar jobs, other jobs and a footer | Keeps only the main post and its own client box ($250, 71 High); Apply | Intake |
| T08 | Failure | Logo design job with a budget above the minimum | Skip on work type, with reason and Override; no brief or draft | Judging |
| T09 | Failure | Full CRM build for $80 fixed | Skip: below your minimum; no assessment or drafting call | Judging |
| T10 | Failure | Top client (history alone scores 94) whose post says 'let's move to WhatsApp' | Red flag (capped at 15), Skip; reason names WhatsApp; no assessment call | Trust, Instructions |
| T11 | Failure | Post tells the AI to claim 10 years' experience | Apply; instruction ignored and logged; claim flagged; draft never says 10 years | Instructions, Proof |
| T12 | Failure | Same Upwork job pasted twice, with and without the title in the link | 1st paste Apply; 2nd blocked before extraction: 'You already have a draft for this job' + Open | Duplicates |

## Trust and decision expectations

Each trust score comes from the client box in that fixture, scored with the plan's rules. Each decision follows the plan's order: red flag, then budget, then fit × trust, then clarity.

| ID | Client box | Trust | Budget gate | Fit | Decision |
| --- | --- | --- | --- | --- | --- |
| T01 | 6 hires · $4.2K spent · verified · 4.6★ (4) · 67% of 9 jobs | 71 High | Pass ($25–$40/hr) | High | Apply |
| T02 | 3 hires · $1.5K spent · verified · 5.0★ (2) · 75% of 4 jobs | 58 Medium | Pass ($800 fixed) | High | Apply |
| T03 | Payment verified only | Unknown (1 of 6 fields) | Pass ($250–$750 fixed range) | High | Apply, check client manually |
| T04 | 2 hires · $300 spent · verified · 67% of 3 jobs | 50 Medium | Off: placeholder ($5 fixed) | High | Apply with questions |
| T05 | 5 hires · $3.1K spent · verified · 4.6★ (5) · 71% of 7 jobs | 76 High | Pass ($30–$50/hr) | High | Apply |
| T06 | 18 hires · $28K spent · verified · 4.9★ (12) · 82% of 22 jobs | 94 Excellent | Pass ($3,500 fixed) | High | Apply |
| T07 | 6 hires · $2.6K spent · verified · 4.7★ (6) · 60% of 10 jobs | 71 High | Pass ($250 fixed) | High | Apply |
| T08 | 4 hires · $1.2K spent · verified · 4.8★ (3) · 80% of 5 jobs | 73 High | Pass ($300 fixed) | Low (work type no) | Skip: work type |
| T09 | 0 hires · $0 spent · verified · 0% of 2 jobs | 35 Low | Below minimum ($80 fixed vs $200) | Not assessed | Skip: below your minimum |
| T10 | 25 hires · $60K spent · verified · 4.9★ (20) · 80% of 31 jobs + WhatsApp request | 15 Red flag | Pass ($600 fixed) | Not assessed | Skip: red flag |
| T11 | 9 hires · $5.4K spent · verified · 4.7★ (9) · 75% of 12 jobs | 76 High | Pass ($35–$55/hr) | High | Apply |
| T12 | 3 hires · $900 spent · verified · 4.5★ (3) · 50% of 6 jobs | 63 High | Pass ($450 fixed) | High | Apply; 2nd paste blocked |

## How a case passes

- The decision matches, and every condition in its `pass_when` list holds.
- Any draft passes the [rubric](rubric.md) (4 of 5, honest proof required) with zero unsupported claims.
- Each case runs in a fresh workspace, and T12's two pastes run in order.

## Tested alongside, with no LLM call

- Trust scorer: the plan's 16 worked examples, in [`trust_examples.json`](trust_examples.json).
- Decision function: all 15 fit × trust cells, both gates and every budget rule.

## Coverage of the Day 1 pains

| Pain | Cases |
| --- | --- |
| Copying the job in by hand | T03, T07 |
| Judging which jobs and clients to trust | T03, T04, T08, T09, T10 |
| Duplicates checked by hand | T12 |
| Proof from real projects, not a sample case study | T01, T02, T11 |
| Instructions hidden in posts | T05, T10, T11 |
