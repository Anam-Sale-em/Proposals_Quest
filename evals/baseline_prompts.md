# Baseline prompts: plain ChatGPT on T01–T03

The same prompt for every job, so the three runs are comparable. The background is the synthetic sample profile, written as plain text the way a freelancer would paste it.

## Rules for each run

- Open a new temporary chat for each job, so memory and earlier chats don't help. Use the same model all three times and write it down.
- Start the stopwatch when you open the job text. Read it and judge the client as you normally would.
- Paste the prompt. Edit the answer by hand, or ask ChatGPT for changes, until you'd actually send it. Then stop the stopwatch.
- Save the raw first answer and your final version to `private/chatgpt_drafts/` (e.g. `T01_raw.txt`, `T01_final.txt`).
- Note the minutes, how many follow-up messages you sent, the rubric score, and unsupported claims (any claim not in the background or the job).

## T01: Build an n8n workflow: Typeform → Google Sheets → Slack, with duplicate check

```
Write a proposal for this freelance job. Use my background below.

My background:
I'm a freelancer doing workflow automation, API integrations, data sync scripts, LLM-powered automations.
Skills: n8n, Python, JavaScript, REST APIs, Webhooks, Google Sheets API, Slack API, Shopify API, PostgreSQL, Gmail API, Airtable, Gemini API.
Minimum rates: $30/hr, $200 fixed.

Past projects:
- Lead intake automation with n8n: Leads from the website's forms were copied into a spreadsheet by hand, with duplicates and slow follow-up. Built an n8n workflow: form webhooks, field validation, a duplicate check by email, a new Google Sheets row and a Slack alert to the sales channel. Result: Lead entry dropped from about 2 hours a week to under 10 minutes.
- Shopify to PostgreSQL inventory sync: Stock counts in the store and the warehouse database drifted apart, so items oversold. Wrote a Python service that listens to Shopify inventory webhooks, reconciles counts against PostgreSQL on a schedule and logs every change. Result: Stock synced every 15 minutes, with no oversold orders in the first month.
- Support inbox triage with an LLM: A small support team sorted every incoming email by hand. Built a Python job that reads new Gmail messages, classifies them with the Gemini API, writes them to Airtable and leaves low-confidence ones for a person to review. Result: About 300 emails a week sorted into 6 categories; low-confidence ones go to a person.

Job:
Build an n8n workflow: Typeform → Google Sheets → Slack, with duplicate check

Posted 2 hours ago · Worldwide

We collect demo requests through two Typeform forms. Right now someone copies each response into our Google Sheet and posts it in Slack by hand, and we keep getting duplicates when people submit twice.

We need an n8n workflow (we already self-host n8n) that:
- Triggers on new responses from both Typeform forms
- Checks the Sheet for an existing row with the same email and skips duplicates
- Adds a new row with name, email, company, form name and timestamp
- Posts a short message to our #sales Slack channel with a link to the row
- Emails us if any step fails

Please share a similar workflow you've built and tell us how you'd handle duplicates.

Hourly: $25.00 – $40.00
Intermediate
Less than 1 month, less than 30 hrs/week

Skills and expertise: n8n · Google Sheets · Slack · Typeform · API Integration

About the client
Payment method verified
4.6 of 4 reviews
United States
9 jobs posted
67% hire rate, 1 open job
$4.2K total spent
6 hires, 2 active
Member since Mar 4, 2022
```

## T02: HubSpot and PostgreSQL two-way contact sync (Python or Node)

```
Write a proposal for this freelance job. Use my background below.

My background:
I'm a freelancer doing workflow automation, API integrations, data sync scripts, LLM-powered automations.
Skills: n8n, Python, JavaScript, REST APIs, Webhooks, Google Sheets API, Slack API, Shopify API, PostgreSQL, Gmail API, Airtable, Gemini API.
Minimum rates: $30/hr, $200 fixed.

Past projects:
- Lead intake automation with n8n: Leads from the website's forms were copied into a spreadsheet by hand, with duplicates and slow follow-up. Built an n8n workflow: form webhooks, field validation, a duplicate check by email, a new Google Sheets row and a Slack alert to the sales channel. Result: Lead entry dropped from about 2 hours a week to under 10 minutes.
- Shopify to PostgreSQL inventory sync: Stock counts in the store and the warehouse database drifted apart, so items oversold. Wrote a Python service that listens to Shopify inventory webhooks, reconciles counts against PostgreSQL on a schedule and logs every change. Result: Stock synced every 15 minutes, with no oversold orders in the first month.
- Support inbox triage with an LLM: A small support team sorted every incoming email by hand. Built a Python job that reads new Gmail messages, classifies them with the Gemini API, writes them to Airtable and leaves low-confidence ones for a person to review. Result: About 300 emails a week sorted into 6 categories; low-confidence ones go to a person.

Job:
HubSpot and PostgreSQL two-way contact sync (Python or Node)

Posted 5 hours ago · Worldwide

We run our product on PostgreSQL and our sales team lives in HubSpot. Contacts drift apart: new signups don't reach HubSpot for days, and edits made by sales never come back to our database.

Scope:
1. Two-way sync of contacts between HubSpot and our PostgreSQL users table
2. New signups appear in HubSpot within 5 minutes
3. Changes to lifecycle stage in HubSpot are written back to PostgreSQL
4. Conflicts: the most recent update wins, and every conflict is logged
5. Runs on our server, with a short README so our developer can maintain it

Fixed price: $800.00
Intermediate
1 to 3 months

Skills and expertise: HubSpot · PostgreSQL · Python · API Integration

About the client
Payment method verified
5.0 of 2 reviews
Canada
4 jobs posted
75% hire rate, 1 open job
$1.5K total spent
3 hires, 1 active
Member since Jan 18, 2024
```

## T03: Python script to pull Shopify orders into Google Sheets daily

```
Write a proposal for this freelance job. Use my background below.

My background:
I'm a freelancer doing workflow automation, API integrations, data sync scripts, LLM-powered automations.
Skills: n8n, Python, JavaScript, REST APIs, Webhooks, Google Sheets API, Slack API, Shopify API, PostgreSQL, Gmail API, Airtable, Gemini API.
Minimum rates: $30/hr, $200 fixed.

Past projects:
- Lead intake automation with n8n: Leads from the website's forms were copied into a spreadsheet by hand, with duplicates and slow follow-up. Built an n8n workflow: form webhooks, field validation, a duplicate check by email, a new Google Sheets row and a Slack alert to the sales channel. Result: Lead entry dropped from about 2 hours a week to under 10 minutes.
- Shopify to PostgreSQL inventory sync: Stock counts in the store and the warehouse database drifted apart, so items oversold. Wrote a Python service that listens to Shopify inventory webhooks, reconciles counts against PostgreSQL on a schedule and logs every change. Result: Stock synced every 15 minutes, with no oversold orders in the first month.
- Support inbox triage with an LLM: A small support team sorted every incoming email by hand. Built a Python job that reads new Gmail messages, classifies them with the Gemini API, writes them to Airtable and leaves low-confidence ones for a person to review. Result: About 300 emails a week sorted into 6 categories; low-confidence ones go to a person.

Job:
Python script to pull Shopify orders into Google Sheets daily

Budget $250 – $750 USD
Paid on delivery

Project details
I need a Python script that runs once a day, pulls the previous day's orders from my Shopify store through the API, and adds them to a Google Sheet: order number, date, customer email, items, total and fulfilment status. It should skip orders that are already in the sheet and write a short log so I can see it ran.

Please explain how you would schedule it and how you would handle Shopify API rate limits.

Skills Required
Python · Shopify · Google Sheets · API

About the client
Payment verified
```
