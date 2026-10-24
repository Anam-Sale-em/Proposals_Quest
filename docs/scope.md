# Scope and non-goals

v2 is an AI OS Mini for job triage. It checks a freelance job, decides Apply, Apply with questions or Skip, and drafts a proposal that only claims work the freelancer has really done. The human always sends.

## Success metric

On the same three test jobs (T01–T03), v2's median time from opening a job to a send-ready proposal must be below the plain-ChatGPT baseline (about 57 minutes) and v1 (65–85+), with every v2 draft passing the rubric and zero unsupported claims. I report the result either way. Definitions, the full metric list and the guardrails are in [metrics](../evals/metrics.md).

## Non-goals for the five days

- Images, video, storyboards and per-proposal scripts. v1 spent 120+ minutes and paid credits per approved proposal on visuals, and they weren't the bottleneck.
- Auto-submitting or auto-filling proposals on any platform.
- Scraping any site, paid scrapers such as Apify actors included.
- Fetching from platforms without an official API (Upwork and Guru come in by paste), and fetching on a schedule. Fetches run only when the user asks.
- Pricing, win-chance, voice matching and rule learning.
- Drafting in languages other than English.
- Multi-user login, team accounts and payments. (Login was built on Day 2, then removed: decision log #34.)

## Scope decisions

| Decision | Why |
| --- | --- |
| Text only | Visuals are paid, slow and hard to evaluate in five days, and they aren't the bottleneck |
| Paste first; official APIs only | No Upwork API access in time, and fetching Upwork's pages breaks its terms |
| Code decides; the LLM extracts and writes | The freelancer's judgment becomes explicit, adjustable rules instead of prompt luck |
| The human always sends | Upwork treats extensions and scripts acting in your session as bots, and its API can't submit proposals |
| One schema per LLM step | Prompt, parser and validator share it, so a missing field fails loudly instead of silently |
| Python, Streamlit and free tiers | Reviewers get a live link and can rerun the evals with one command |
| Local JSON first, Firestore last | Storage sits behind one interface, and Firestore is the first thing cut if Day 3 runs long |

## Day 5 scope (the brief's "v1 scope")

In this repo v1 means my previous workflow, so the brief's "v1 scope" is called the Day 5 scope here.

**Never cut**

- Intake by paste (job link plus job details) from any platform.
- Link and duplicate checks, extraction I confirm, the client trust score and the budget gate.
- Fit assessment and the decision: Apply, Apply with questions or Skip, each with a reason and an Override.
- Solution Brief, a proposal grounded in real projects, and the claim check (one retry, then "needs review").
- The draft screen: proof switch, editor and copy buttons.
- Mark as sent, with the sent log downloadable as CSV from My jobs.
- The passphrase gate.
- The eval runner (one command) and replay mode from cached LLM responses.

**Cut in this order if Day 3 runs long**

1. Firestore (the live link runs on local JSON)
2. PDF upload in CV import (pasted text stays)
3. Revise-with-comment
4. One-tap outcomes (Mark as sent stays)
5. The Details expander

**Freelancer.com:** fetch by link and by keyword passed the Day 2 check against the live API. The public API returns no client, so I copy the rating, review count and payment status from the job page; Freelancer.com jobs are scored on those three (reviews stand in for hires) and can't reach Excellent. The keyword feed only lists new jobs that mention a keyword, with their skills; it decides nothing. The decision runs once I pick a job.

**Only if ahead:** the n8n Community jobs adapter, and talking points for video interviews.

**Stack:** Python with Pydantic contracts, Streamlit Community Cloud, Gemini (Groq as fallback and as the eval judge), local JSON storage behind one interface, and a CSV download for the sent log.
