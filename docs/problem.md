# User and problem

**The bottleneck:** turning one Upwork job into a send-ready proposal takes about an hour with plain ChatGPT and 65–85+ minutes with my previous pipeline (my estimates, step by step). Most of that is getting the job and my background into the tool, then 2–3+ revision rounds to make the draft sound like me. Neither way decides whether a job is worth it. My previous pipeline was built for an agency's sales format, with a generated sample case study in every proposal; a solo freelancer needs proof from their own projects instead.

## Whose workflow

Mine. v1 is the Upwork proposal workflow I built and ran at my previous job: an n8n pipeline with chained LLM steps and a mobile review app. The brief recommends a real workflow from your own work, and I have v1's export to back every step described here. The export stays out of this repo, because it holds my former employer's prompts and credentials.

## Target user and job to be done

**Target user:** a freelancer who applies to posted jobs several times a week. I'm the first one, since I freelance on Upwork myself. v2 must also work for a non-developer, with no prompting skill needed, because its rules live in code rather than in prompts. A non-developer proxy runs it on Day 3.

**Job to be done:** "When a job catches my eye, tell me quickly whether it's worth applying to, and give me a proposal I'd actually send: specific to the post, claiming only work I've done."

## Evidence of pain

Every pain below hits every job. Times are my per-step estimates: v1's from testing it on 100+ jobs, plain ChatGPT's from walking through T01–T03 ([baseline](../evals/baseline.md)).

| Pain | Evidence | How often | Cost per job | v2 change |
| --- | --- | --- | --- | --- |
| Getting the job into the tool | v1: 10 fields typed into a form; auto-fill was on v1's roadmap. ChatGPT: find and paste the job details | Every job | v1: 10 min · ChatGPT: 5 min | Paste a link, pick from a keyword search, or paste the whole post; the LLM extracts the fields and I confirm them |
| Picking proof and writing my background | ChatGPT: choose which projects fit, then write the background for this job | Every job | ChatGPT: 10 min | A profile saved once; the right projects pre-selected per job |
| Revisions to make it sound like me | v1: 2–3 rounds, and each rewrote the whole proposal and all 36 frame prompts. ChatGPT: 3+ rounds, each adding odd things to find and remove | Every job | v1: 40–60+ min · ChatGPT: about 31 min | Revisions change only what the comment asks; the draft starts from my real projects |
| Judging which jobs and clients to trust | Neither way has a skip step or a client check, so every job gets a full draft; job scoring with red flags was on v1's roadmap | Every job | v1: 5 min to choose, done by me | A trust score from the client's history, then Apply, Apply with questions or Skip, each with its reason |
| Duplicates checked by hand | No duplicate check in either way; duplicate prevention was on v1's roadmap | Every job | Inside the 5 min above | One record per job, keyed on the job's ID; a repeat opens the existing draft |
| Proof built for an agency format | By design, v1 generated a sample case study for each job (a company, a scenario and its results) to showcase the approach, and the proposal was built around it. For a solo freelancer, proof has to come from their own projects. Five real v1 drafts scored on Day 1: 5–7 case-study claims each, 29 in all, none from a project library | Every v1 draft | Every v1 draft misses the rubric's real-proof item, which v2 requires | Proof only from the freelancer's real projects, plus a claim check |
| Jobs that need a question first | v1 was built to draft every job it was given, with job choice done by a person beforehand. Two of the five real v1 drafts were for posts with a budget well below the scope, or no budget and few details | Whenever a post is unclear or unrealistic | A full draft where a scoping question would serve better | Realistic and clarity checks: Apply with questions or Skip |

Building and testing v1 also taught two engineering lessons that shape v2: keep every step's inputs and outputs in one shared contract, and plan for load. Under load, access tokens expired mid-run, which I solved with a token-refresh branch.

## Is the problem real, recurring and measurable?

- **Real:** it's my own workflow; I built v1, tested it on 100+ jobs, and three of v2's fixes were already on v1's roadmap.
- **Recurring:** every job hits every pain, jobs went in daily at my previous job, and I still freelance on Upwork.
- **Measurable:** the baseline is about 57 minutes per job with plain ChatGPT and 65–85+ with v1, with plain ChatGPT's three drafts scored on the rubric. v2 is timed on the same jobs with the same clock on Day 4.

## Assumptions

The brief asks for these to be stated when synthetic data is used.

- The 12 test jobs and the sample profile are synthetic, written to trigger each case. Their layout approximates real Upwork and Freelancer.com pages.
- Real-job evidence comes from five real v1 drafts and, on Day 4, 6–10 fresh Upwork jobs where I record my own calls before running v2.
- My own use stands in for "a freelancer who applies several times a week". Non-developer use is checked with a proxy on Day 3.
- v1 can't be re-run (I no longer have access), so its times come from my testing. The plain-ChatGPT times are per-step estimates; one stopwatch ChatGPT run on Day 4 checks them.
