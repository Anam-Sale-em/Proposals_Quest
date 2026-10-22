# Baseline

Before v2, one proposal took about an hour with plain ChatGPT, and 65–85+ minutes with v1, my previous pipeline. Plain ChatGPT's first drafts were honest and passed the rubric on the three test jobs. Most of the time went into getting the job and my background into the prompt, and into revision rounds to make the draft sound like me.

All times are per-step estimates from me, not stopwatch runs. The ChatGPT drafts are real outputs, scored below.

## Main baseline: plain ChatGPT on T01–T03

This is the brief's "simple ChatGPT use", and it's the previous way of working for a freelancer without a pipeline. Prompts: [baseline_prompts.md](baseline_prompts.md). Raw first answers: [baseline_runs/](baseline_runs/).

### Time per job (my estimate, the same for each of the three jobs)

| Step | Minutes |
| --- | --- |
| Find and read the job details | 5 |
| Decide which past projects to include | 5 |
| Write my background for this job | 5 |
| Generate the first answer | 0.5 |
| Read the answer thoroughly | 5 |
| Decide what to change and change it | 5 |
| **First draft subtotal** | **25.5** |
| Revision rounds, at least 3, each about 10.5 (0.5 to generate, 5 to review, about 5 to pinpoint and fix odd additions) | 31.5 |
| **Total per job** | **about 57 (an hour or more)** |

The background is written fresh for each job, because the projects worth citing change with the job. The 5 minutes of fixing per revision round is my reading of "I have to pinpoint it and do those changes".

### Quality of the raw first answers

Scored by me against the [rubric](rubric.md) and checked line by line against the background and the post.

| Job | Goal | Specific | Honest proof | Plan | Ask | Pass | Unsupported claims |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | Yes | Yes | Yes | Yes | Yes | 5/5 | 0 |
| T02 | Yes | Yes | Yes | Yes | Yes | 5/5 | 0 |
| T03 | Yes | Yes | Yes | Yes | Yes | 5/5 | 0, plus 1 borderline |

- **T01** cites P1 accurately, including its "2 hours a week to under 10 minutes" result, and covers every requirement in the post.
- **T02** never claims HubSpot experience: it cites P2 and P1 and says "the same integration principles apply here". It asks two questions where the rubric says one, which I let pass.
- **T03** says "I've also built n8n automations" (plural) when the background has one n8n project. I count it as borderline, not unsupported.

### What the rubric doesn't catch

- **Voice.** All three drafts are correct but generic. The 3+ revision rounds go into making them sound like me, and each round adds a few odd things that have to be found and removed. Day 4 counts revision rounds and edits before send.
- **Judgment.** ChatGPT drafted all three without a word about the client or whether to apply. T01–T03 are all Apply cases, so this doesn't cost anything here, but plain ChatGPT has no skip path at all: it would draft T08–T10 too.
- **Duplicates.** Nothing stops me from drafting the same job twice.

## Reference: v1, my previous pipeline

v1 can't be re-run: I no longer have access to it. These numbers come from testing it on 100+ jobs while I built it.

| Step | Minutes |
| --- | --- |
| Choose the job: read it, judge the client, check for duplicates | 5 |
| Type the 10 fields into the form | 10 |
| Wait for the use case, storyboard and proposal | 3 |
| Review to approval | 7 |
| **Before revisions** | **25** |
| 2–3 revision rounds to make the proposal unique and personal, 20+ each | 40–60+ |
| **Total per job** | **65–85+** |
| Visuals after approval (36 frames on a paid image API), not counted above | 120+ |

### v1 quality: five real drafts, scored

Five drafts v1 generated for real Upwork jobs (July–August 2026), scored by me against v2's [rubric](rubric.md). v1 was built for an agency's sales format, so this measures how far that format is from what a solo freelancer needs, not whether v1 did its own job. The raw texts stay in `private/v1_drafts/`, because they're my former employer's output. Only the scores are here.

| Job type | Goal | Specific | Real proof | Plan | Ask | Items | Pass | Case-study claims |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Technical audit of a live subscription app | No | Yes | No | Yes | Yes | 3/5 | No | 6 |
| React Native investor app on an existing NestJS backend | No | Yes | No | Yes | Yes | 3/5 | No | 7 |
| Enterprise cross-platform mobile app | Yes | Yes | No | Yes | Yes | 4/5 | No | 5 |
| Production n8n workflows for an agency | Yes | Yes | No | Yes | Yes | 4/5 | No | 6 |
| React Native food delivery MVP | Yes | Yes | No | Yes | Yes | 4/5 | No | 5 |
| **Total** | 3/5 | 5/5 | 0/5 | 5/5 | 5/5 | | **0 of 5 pass** | **29 (5–7 per draft)** |

- **Real proof is the gap.** By design, every v1 draft is built around a sample case study generated for that job, with 4–6 sample results such as "reduced onboarding time by 75%". That suits an agency showcase. For a solo freelancer, the rubric requires proof from their own projects, so the format itself is what v2 replaces.
- **Numbered asks need their own check.** Two posts asked for something specific: availability for ongoing support, and five numbered questions starting with links to live apps. Both drafts covered the job well but didn't answer those asks point by point. v2 lists each explicit ask during extraction, and rubric item 1 checks it.
- **Voice.** v1 wrote in the agency's voice ("our team"), which fit its purpose. One post asked whether the applicant would personally do the work, so v2 writes in the freelancer's own voice and rubric item 3 now checks it.
- **Job choice.** v1 drafted whatever a person chose to enter. Two of these posts would benefit from a question first: one set $1,000 fixed for two weeks against a large scope, and one gave no budget and few details. v2's realistic and clarity checks handle that.

## What this means for v2

- **Time is where v2 can win.** The fixed costs are about 25 minutes of finding the job, picking projects and writing the background, plus 3+ revision rounds. v2 targets both: a paste or link, a saved profile, pre-selected proof, and revisions that change only what's asked.
- **Quality has to hold, not jump.** On these three clean jobs, plain ChatGPT with a real background already writes honest drafts that pass the rubric. v2 has to match that with zero unsupported claims; it won't beat 5/5. Its quality gains are judgment (skips, client trust, duplicates) and fewer rounds to a send-ready draft.
- **Real proof is the deciding factor.** Plain ChatGPT given a real background passed 3 of 3. v1's agency format, built around generated case studies, passed 0 of 5 on a rubric written for solo freelancers. The difference is the source of the proof, not the prompting, so v2 is built around the freelancer's own project library.

## Day 4 comparison

v2 is timed with a stopwatch on T01–T03 with the same clock (opening the job to send-ready) and also on 3 fresh Upwork jobs. To keep the comparison fair, I also time one plain-ChatGPT run with a stopwatch on a fresh job, so at least one baseline number is measured the same way as v2's.

## Limits

- The baseline times are per-step estimates; v2's will be stopwatch times. The stopwatch ChatGPT run on Day 4 checks the estimate.
- Three jobs is directional evidence, not proof.
- The synthetic background is short and clean, which makes ChatGPT's job easier than with a real, messy CV.
- The quality scores are mine. On Day 4 the AI judge rescores all eight drafts with labels removed.
- v1's drafts are on real jobs and ChatGPT's are on synthetic ones, so the two quality rows compare ways of working, not identical inputs.
