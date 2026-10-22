# Proposal Pipeline v2

v2 is an AI OS Mini for freelance job triage. Paste a job, and it checks the link and duplicates, scores the client, decides **Apply**, **Apply with questions** or **Skip** with one plain reason, and drafts a proposal that only claims work you've really done. You approve the extracted details and the final draft. v2 never submits anything: you copy the draft and send it yourself.

## For non-developers: just open the link

Open the app link you were given and enter the passphrase you were given. Nothing to install.

Running it locally instead? If `.env` has no keys yet, the app shows a one-time screen to paste them.

## Run it on your own computer (3 steps)

```bash
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env   — then fill in APP_PASSPHRASE, GEMINI_API_KEY and GROQ_API_KEY
python -m streamlit run app.py
```

`python -m streamlit` works even when pip installed the `streamlit` command outside your PATH (common on Windows).

Open the link Streamlit prints and enter your passphrase. Then set your minimum rates (your workspace), or pick **Sample workspace → Load sample data** to try the 12 test jobs.

### Sent log

My jobs → **Download sent log (CSV)** gives every sent proposal with its decision, client trust, proof, minutes from paste to sent, the share of the draft you edited and the outcome. It opens in Excel or Google Sheets. On the live link, download it now and then: the app's files reset when it restarts.

### Live link (Streamlit Community Cloud, free)

1. Push this repo to GitHub (a private repo is fine).
2. At [share.streamlit.io](https://share.streamlit.io), sign in with GitHub → **Create app** → pick the repo, branch `main` and file `app.py`. Under **Advanced settings**, choose Python 3.12.
3. In **Secrets**, paste `.streamlit/secrets.toml.example` with your passphrase and both keys filled in, then **Deploy**.
4. Make the app public in its sharing settings so people can open it without a Streamlit account. The passphrase still keeps strangers out.

Online, the key setup screen never appears: until the Secrets are set, visitors only see "This app isn't set up yet".

Limits: the app sleeps after 12 hours without visitors (open the link and click the wake-up button; wake it before a demo), and its local files reset whenever it restarts or you push a change. That clears saved jobs and settings. Sent proposals with their timings are kept in each user's Sheet log.

## Using it

1. **New job:** paste the job link and the whole job post (copying the whole page is fine; v2 keeps only the main post and its own client box). Add the client box separately if it isn't in the paste. Freelancer.com jobs can also come in by link or keyword search. **Check if this job is a good fit first** is ticked by default; untick it to go straight to the draft (red flags and a low budget still show as warnings).
2. **Confirm the details:** check what v2 took from the post, fix anything wrong, then **Confirm and check**.
3. **Decision card:** one decision and one reason. **Write proposal**, or **Override** a Skip (logged). **Details** shows the trust score with its top reasons, the four fit answers, the link status and the skill overlap.
4. **Draft:** your best project is pre-selected as proof (switch it, or choose plan only). Edit the text, answer the screening questions, read the claim-check notes, or revise with a comment (it changes only what you ask).
5. **Send:** Open job, paste, **Mark as sent**, then record the outcome with one tap.

## Run the tests and evals

```bash
python -m pytest -q                      # 79 tests: rules, pipeline, app, integrations (offline)
python scripts/run_evals.py              # the 12 frozen test cases on the real models (cached)
python scripts/run_evals.py --replay     # same, from saved responses only: identical every run, offline
python scripts/run_evals.py --record     # call the APIs again and refresh the saved responses
python scripts/judge.py evals/results/<run> [--hand evals/hand_scores.csv]
python scripts/cli.py --fixture T01      # one job from paste to proposal in the terminal
python scripts/check_models.py           # which configured models your keys can use (no quota used)
```

Each eval run writes `evals/results/<prompt_version>_<time>/` with `results.csv` (per-case checks, latency, tokens, model calls and blank columns for hand rubric scores), `summary.md` and every draft. The offline tests use a scripted stand-in for the LLM (`tests/scripted_llm.py`) to check the plumbing and code rules; real model quality comes from `run_evals.py`.

## Repo map

| Path | What it is |
| --- | --- |
| `app.py` | Streamlit app |
| `proposal_v2/` | Contracts, rules, validators, LLM client, prompts, pipeline, storage, integrations, eval runner |
| `config.toml` | Every threshold, model name, rate limit and length limit |
| `fixtures/` | The 12 synthetic test jobs and the sample profile |
| `evals/` | Test cases, trust examples, rubric, metrics, baseline, results, replay cache |
| `docs/` | Problem, workflow map, scope, architecture, v1 → v2, decision log |
| `scripts/` | Eval runner, judge, terminal v0 |
| `tests/` | Unit, pipeline, app and integration tests |

## Operator runbook

| Problem | What you see | What to do |
| --- | --- | --- |
| Gemini rate limit (free tier: 5 a minute, 20 a day on 3.8 Flash) | Slower answers; run log shows `groq` as provider | Nothing: Groq takes over. If both fail, the app says so; wait a minute, or add billing to the Gemini project |
| Gemini busy (503 "high demand") | A slower answer; the run log shows retries, then another model | Nothing: v2 retries, tries the other Gemini model, then Groq. If everything is busy, the app says so; wait a minute |
| Every model fails | "The AI service didn't respond properly after trying every model…" | Run `python scripts/check_models.py`, then list only available models under `[models]` in `config.toml`; check both keys and quotas; set `LLM_MODE=replay` for a demo |
| Replay mode has no saved response | "Replay mode has no saved response for the … step" | Run once with `LLM_MODE=live`, or `run_evals.py --record` |
| Sleeping app | Streamlit's "This app has gone to sleep" page | Click the wake button; wait about 30 seconds |
| Failed extraction | "No job title or description was found in the paste" | Copy the job's own page (not a search page) and paste again, or fill the fields by hand on the confirm screen |
| Wrong link or job | "The link and the details may be different jobs" | Fix the link or details, or Proceed anyway (logged) |
| A Skip that looks wrong | The card's reason | Open Details to see which rule fired; Override (logged), or adjust minimum rates or trust cut-offs in Settings (every change logged) |
| Draft needs review | Yellow box with the failing sentences | Edit those sentences, switch the proof, or add the missing project under Projects |
| Freelancer.com fetch fails | "Freelancer.com didn't return this job…" | Paste the job text instead |

Logs: `logs/runs/<date>.jsonl` has one line per LLM call (step, model, provider, latency, tokens, prompt_version, commit, cache hit, error).

## Data and privacy

- Your data stays in your workspace (`data/users/me/` locally, or Firestore). The sample workspace is separate.
- Settings → **Delete all data in this workspace** removes it. Download the sent log first if you want to keep it.
- Leave confidential client details and NDA work out of your projects.
- Gemini's free tier may use content to improve Google's products. Use a paid key for anyone else's data.
- `private/` (gitignored) holds v1's export, v1's raw drafts and my Day 4 calls. None of it is committed.

## Status

| Day | State |
| --- | --- |
| 1 Discover, map, baseline | Done: [problem](docs/problem.md), [workflow map](docs/workflow-map.md), [baseline](evals/baseline.md), [metrics](evals/metrics.md), [scope](docs/scope.md), [12 test cases](evals/test_cases.md) |
| 2 Design and v0 | Code written: [architecture](docs/architecture.md), contracts, rules with tests, LLM steps, validators, eval runner, CLI. Still to do: first real-model eval run, Freelancer.com API check |
| 3 Working core | App written and tested headlessly. Still to do: deploy, Firestore if needed, first run by a proxy user |
| 4 Evaluate and harden | Not started |
| 5 Hand off | Not started |
