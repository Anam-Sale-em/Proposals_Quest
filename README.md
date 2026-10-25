# Proposal Pipeline v2

v2 is an AI OS Mini for freelance job triage. Paste a job, and it checks the link and duplicates, scores the client, decides **Apply**, **Apply with questions** or **Skip** with one plain reason, and drafts a proposal that only claims work you've really done. You approve the extracted details and the final draft. v2 never submits anything: you copy the draft and send it yourself.

## For non-developers: just open the link

Nothing to install.

1. Open **https://proposalsquest-ziiaqxdgbmuguhpzntuyjf.streamlit.app/**. If it says the app is asleep, click **Yes, get this app back up** and wait about a minute.
2. Type the passphrase **`UnknownEntity`** and click **Open**.
3. In the sidebar, pick **Sample workspace → Load sample data**. You get a sample freelancer with 3 projects, the 12 test jobs, and sample Freelancer.com jobs for the link and search tabs. Pick a test job under **New job**, click **Fill the form**, then **Check job**.

**My workspace** holds my own projects and jobs, and everyone with the passphrase shares it, so please try things in the Sample workspace. Nothing you do on the live app is permanent: see [Where your data lives](#where-your-data-lives).

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

My jobs → **Download sent log (Excel)** gives every sent proposal with v2's call, client trust, proof, minutes from adding the job to sending it, how much of the draft you changed (0% = sent as written) and the outcome. It opens in Excel or Google Sheets. On the live link it's the only record that survives a restart, so download it now and then.

### Live link (Streamlit Community Cloud, free)

1. Push this repo to GitHub (a private repo is fine).
2. At [share.streamlit.io](https://share.streamlit.io), sign in with GitHub → **Create app** → pick the repo, branch `main` and file `app.py`. Under **Advanced settings**, choose Python 3.12.
3. In **Secrets**, paste `.streamlit/secrets.toml.example` with your passphrase and both keys filled in, then **Deploy**.
4. Make the app public in its sharing settings so people can open it without a Streamlit account. The passphrase still keeps strangers out.

Online, the key setup screen never appears: until the Secrets are set, visitors only see "This app isn't set up yet".

Limits: the app sleeps after 12 hours without visitors (open the link and click the wake-up button; wake it before a demo). Waking up, a reboot or a push restarts it, and a restart clears everything saved in the app (next section).

## Where your data lives

There is one storage model: **JSON files on the disk of whatever machine runs the app**, under `data/users/<workspace>/`. There is no database. On your own computer that disk is yours and keeps everything. On Streamlit Community Cloud the disk belongs to the app's container, and a restart replaces the container with a fresh copy of the repo.

| Data | Where it's stored | Survives a restart on the live link? | Who can see it on the live link |
| --- | --- | --- | --- |
| Profile: rates, skills, kinds of work | `data/users/me/settings/profile.json` | No | Everyone with the passphrase (one shared "My workspace") |
| Settings change log | `data/users/me/settings_log.jsonl` | No | Same |
| Projects | `data/users/me/projects/*.json` | No | Same |
| Jobs: post, client details, decision, drafts, timings, sent status, outcome | `data/users/me/proposals/*.json` | No | Same |
| Sample workspace | `data/users/sample/`, built from `fixtures/` by **Load sample data** | No, but one click rebuilds it | Everyone with the passphrase |
| Model call logs | `logs/runs/<date>.jsonl` | No | Only the app's operator, not shown in the app |
| Model response cache | `evals/cache/` | Only what's committed to the repo (the eval cache) | Not shown in the app |
| Screen in progress (an unconfirmed job, form fields) | Your browser tab's session | No: also lost when you refresh the page | Only you |
| Passphrase and API keys | Streamlit **Secrets** (online) or `.env` (local), never in the repo | Yes | Only the app's owner |
| Sent log | The Excel file you download from My jobs | Yes: it's on your computer | Only you |

**What isolation there is:** two workspaces, My workspace and Sample workspace, kept in separate folders. There are no per-person accounts. On the live link, two people using My workspace see and change the same jobs and projects. To have a workspace of your own, run the app on your own computer (3 steps above). Each copy keeps its data on its own disk.

**What's lost, and when:** on the live link, a reboot, a wake-up from sleep or a new push starts the app from the repo again. That clears both workspaces, the logs and anything new in the cache. Only Secrets and files you downloaded are kept. On your own computer nothing is lost on restart. Data goes only when you use Settings → **Delete all data in this workspace** or delete the `data/` folder.

**Checked:**
- **Restart on a local run (25 Oct 2026).** I loaded the sample data and checked one job in one process, then started a fresh process on the same `data/` folder. The job, its decision and the 3 projects were all still there.
- **Restart on the live link.** Open the Sample workspace, click **Load sample data**, then **Reboot app** from the Streamlit Cloud menu. Open the link again: the Sample workspace is empty and My workspace has no jobs. Download the sent log before you try this.

## Using it

1. **New job:** paste the job link (the job's own page; on Freelancer.com use the project's **Share → Copy link**) and the whole job post from Upwork, Freelancer.com or Guru (copying the whole page is fine; v2 keeps only the main post and its own client box). Freelancer.com jobs can also come in by link or keyword search. **Check if this job is a good fit first** is ticked by default; untick it to go straight to the draft (red flags and a low budget still show as warnings). Pasting a job you already have offers Open, New version or Check again.
2. **Confirm the details:** check what v2 took from the post, fix anything wrong (budget type, client history), then **Confirm and check**. Client history is the **About the client** section of the job's page: below the skills and activity on Upwork, on the right side on Freelancer.com (Open job is right there). For Freelancer.com jobs, copy the rating, review count and payment status; for Guru, the **Posted By** box (feedback, total spend, jobs posted, jobs paid, paid and outstanding invoices). If the post asks for a quote or timeline, a **Your price and timeline** field appears; fill it in, or the draft leaves "[your price and timeline]" for you. Add anything the proposal must say under **Anything you want in the proposal?** (your own words; v2 treats them as true). Under **Proof**, let v2 pick the best project, choose up to 3 yourself, or cite none.
3. **Decision card:** one decision, one reason, client trust, budget and fit. **Apply with questions** means it's worth applying, but the post is vague or the budget looks unreal, so the proposal leads with questions. Changed your skills, rates or projects? **Check the fit again** reruns it. **Write proposal**, or **Override** a Skip (logged). Forgot the client's details? **Edit client details** updates trust and the decision without rerunning the fit check; a client with no details reads "can't rate". **Details** shows the trust score with its top reasons, the four fit answers, whether the three checks agreed, the skill tags and the link check.
4. **Draft:** your best project is pre-selected as proof. Pick up to 3 (the first is the main one), or none for plan only, then **Rewrite with this proof**. Edit the text, answer the screening questions, fix any line the claim check flags, or revise with a comment (it changes only what you ask). The line under the title shows how long the fit check and each draft took.
5. **Send:** Open job, paste, **Mark as sent**, then record the outcome with one tap. My jobs → **Download sent log (Excel)** keeps the record.

## Run the tests and evals

```bash
python -m pytest -q                      # 100 tests: rules, pipeline, app, integrations (offline)
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
| `evals/` | Test cases, trust examples, rubric, metrics, baseline, Day 4 results, failures, rubric scores, run outputs |
| `docs/` | Case study, AI collaboration note, problem, workflow map, scope, architecture, v1 → v2, decision log |
| `scripts/` | Eval runner, judge, terminal v0 |
| `tests/` | Unit, pipeline, app and integration tests |

## Operator runbook

| Problem | What you see | What to do |
| --- | --- | --- |
| Gemini rate limit (free tier: 5 a minute, about 20 a day on 3.8 Flash) | Slower answers (a drafted job takes about 1.5–2 minutes on the free tier) | Nothing: the other Gemini model, then Groq, take over. If all fail, the app says so; wait a minute, or add billing to the Gemini project |
| Gemini busy (503 "high demand") | A slower answer; the run log shows retries, then another model | Nothing: v2 retries, tries the other Gemini model, then Groq. If everything is busy, the app says so; wait a minute |
| Every model fails | "The AI service didn't respond properly after trying every model…" | Run `python scripts/check_models.py`, then list only available models under `[models]` in `config.toml`; check both keys and quotas; set `LLM_MODE=replay` for a demo |
| Replay mode has no saved response | "Replay mode has no saved response for the … step" | Run once with `LLM_MODE=live`, or `run_evals.py --record` |
| Sleeping app | Streamlit's "This app has gone to sleep" page | Click the wake button; wait about 30 seconds |
| Failed extraction | "No job title or description was found in the paste" | Copy the job's own page (not a search page) and paste again, or fill the fields by hand on the confirm screen |
| Wrong link or job | "The link and the details may be different jobs" | Fix the link or details, or Proceed anyway (logged) |
| A Skip that looks wrong | The card's reason | Open Details to see which rule fired; Override (logged), or adjust minimum rates or trust cut-offs in Settings (each change is recorded in `settings_log.jsonl` in the workspace folder) |
| Draft needs a check | "Check before sending" with the doubtful lines | Edit those lines, switch the proof, or add the missing project under Projects |
| An old job's check looks out of date | The job shows an old decision | Paste it again → **Check again** (not offered once a job is marked as sent) |
| "The three checks split on …" in Details | The model answered a fact differently across its three checks | The majority answer is used; read the reason and override if you disagree |
| Freelancer.com fetch fails | "Freelancer.com didn't return this job…" | Paste the job text instead |

Logs: `logs/runs/<date>.jsonl` has one line per LLM call (step, model, provider, latency, tokens, prompt_version, commit, cache hit, error).

## Data and privacy

- Your data stays in your workspace's folder (`data/users/me/`). The sample workspace is separate. See [Where your data lives](#where-your-data-lives) for what's shared and what's lost on the live link.
- Settings → **Delete all data in this workspace** removes it. Download the sent log first if you want to keep it.
- Leave confidential client details and NDA work out of your projects.
- Gemini's free tier may use content to improve Google's products. Use a paid key for anyone else's data.
- `private/` (gitignored) holds v1's export, v1's raw drafts and my Day 4 calls. None of it is committed.

## Results and docs

- [Case study](docs/case-study.md) · [AI collaboration note](docs/ai-collaboration-note.md)
- [Results, Days 4–5](evals/day4-results.md): seven fully live eval runs, every decision and trust score right (84 of 84); an AI judge passed v2's drafts 5–7 of 9 across four prompt versions; the submitted v2.0.9 passes 11 of 12 live
- [Failures](evals/failures.md) · [Architecture](docs/architecture.md) · [Decision log](docs/decision-log.md)
