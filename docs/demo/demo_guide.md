# APEX Demo Guide

How to run a client demo or interview walkthrough of APEX: setup, the free AI model limits and what they mean for a session, the questions to ask in order, what each answer should show, and what to do when something goes wrong.

Last verified against the running Docker stack on 2026-10-10.

---

## 1. What APEX is (the 30-second pitch)

APEX is an AI sales co-pilot for account managers. It reads CRM data (accounts, opportunities, contacts, support cases, activities) and answers two kinds of questions:

- **Data questions** ("Which accounts are at risk?", "What's closing this month?", "List contacts at Brightwater"). Answered straight from the CRM data in about a second, with no AI model involved, so the numbers are always exact.
- **Planning questions** ("Give me a 7-day playbook for Northwind", "Why are we losing Halvorsen?"). Answered by a multi-step AI reasoning pipeline that is grounded in the account's real deals, contacts and cases, and returns a prioritised plan with owners and deadlines.

What to stress to a client: APEX never invents companies, people or numbers. Every name and figure in an answer comes from their CRM data, and urgency (P1/P2/P3) is calculated from health scores and open cases, not guessed by the AI.

---

## 2. Before the demo

### 2.1 Start the stack

From the repository root:

```powershell
docker compose up -d
docker compose ps
```

Wait until `apex-backend` shows `(healthy)`. The first start takes about a minute while it loads models and seeds the demo data.

| Service | Address |
|---|---|
| App (frontend) | http://localhost:3000 |
| API (backend) | http://localhost:8002 |
| Database | Postgres container `apex-db` (host port 5433) |

### 2.2 Log in

| Field | Value |
|---|---|
| Email | `demo@apex.example` |
| Password | `ApexDemo#2026` |

All data is fictional: 16 accounts, 34 opportunities, 42 contacts, 15 support cases and 44 activities. Company names, people, `*.example` emails and `555-01xx` phone numbers are invented.

### 2.3 Check today's AI budget

Free AI requests are limited per day (see section 3). Check what is left before a demo:

```powershell
$key = (Get-Content .env | Select-String '^OPENROUTER_API_KEY=').ToString().Split('=',2)[1]
Invoke-RestMethod https://openrouter.ai/api/v1/key -Headers @{Authorization = "Bearer $key"} | Select-Object -ExpandProperty data
```

`is_free_tier: True` means the 50-requests-per-day limit applies.

### 2.4 Checklist

- [ ] `docker compose ps` shows all three containers up, backend healthy
- [ ] Logged in at http://localhost:3000
- [ ] Started a **New** conversation (each conversation keeps its own history)
- [ ] No AI-heavy rehearsal earlier the same day (it spends the daily budget)
- [ ] The Loom recording is ready as a backup for the AI plan (section 6)

---

## 3. Free AI model limits and what they mean

APEX uses only free OpenRouter models. No paid usage.

| Setting | Value |
|---|---|
| Main model | `nvidia/nemotron-3-super-120b-a12b:free` |
| Automatic fallbacks | `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free` (used when the main model is busy) |
| Change with | `OPENROUTER_MODEL`, `OPENROUTER_FALLBACK_MODELS` in `docker-compose.yml` or the root `.env` |
| Cost | $0 |

### 3.1 OpenRouter free-tier limits

| Account state | Requests per minute | Requests per day |
|---|---|---|
| Never bought credits (current: `is_free_tier: True`) | 20 | **50** |
| Bought at least $10 of credits once (still free models only) | 20 | 1,000 |

The daily counter resets once a day (OpenRouter uses UTC midnight, which is 5:30 AM IST). Check OpenRouter's documentation if the limits change.

### 3.2 Requests used per question (measured 2026-10-10)

| Question type | Examples | AI requests | Typical time |
|---|---|---|---|
| Portfolio data | which accounts have expansion potential, what's closing this month | **0** | ~1 s |
| Account data | revenue, health score, list contacts, show opportunities | **0** | ~1 s |
| At-risk list / risk review | which accounts are at risk | 0–1 | 1–4 s |
| Unknown account | tell me about Acme Corp | 1 | ~2–10 s |
| Greeting | hi | 1 | ~2–10 s |
| **AI plan / reasoning** | 7-day playbook, why are we losing X, who should I contact at Y | **8–12** | **2–2.5 min** |

The AI plan figure was measured on a Northwind playbook: 12 requests (8 pipeline steps plus JSON repairs), each taking 15–17 s on the free model.

### 3.3 Daily and monthly capacity

Using 8–12 requests per AI plan:

| | Free tier (50/day) | After a one-time $10 credit purchase (1,000/day) |
|---|---|---|
| AI plans per day | 4–6 | 83–125 |
| AI plans per month (30 days) | 125–187 (1,500 requests) | 2,500–3,750 (30,000 requests) |
| Data questions | Unlimited (0 requests) | Unlimited |

Working out the numbers: 50 ÷ 12 ≈ 4 and 50 ÷ 8 ≈ 6 plans per day; × 30 days for the month.

The per-minute limit (20) is not the constraint for one presenter: a single plan spreads its 12 requests over about 2.5 minutes. Two plans running at the same time could hit it.

### 3.4 Budget for one demo session

| Item | Requests |
|---|---|
| Data questions (the whole of section 5, steps 1–6) | 0 |
| Greeting | 1 |
| Unknown-account check | 1 |
| One live AI plan | ~12 |
| **Total** | **~14** |

That leaves room for 2–3 more AI plans the same day. Do not run more than 3 live AI plans on a demo day, and rehearse AI plans on a different day.

### 3.5 What the user sees

- While a slow answer runs, an animated progress line appears after 6 seconds with: "Free AI model in use: detailed plans can take 1–3 minutes. Data questions (revenue, contacts, at-risk lists) answer instantly."
- Under the input box: "Running on free AI models: about 6 full AI plans per day. Data questions are instant and unlimited."
- If the daily limit is reached, AI plans do not error out. APEX returns a simpler plan built only from the CRM data (correct figures, the critical case, the main contact, day-by-day steps), and data questions keep working. Billing and limit errors are not retried, so this fallback arrives in seconds rather than minutes.

---

## 4. Demo data at a glance

| Account | Health | Story |
|---|---|---|
| Sablewood Manufacturing | 14 | No named decision maker, engagement fading |
| Halvorsen Retail Co. | 23 | Last two deals lost to Competitor C |
| Northwind Logistics | 28 | $1.2M renewal 21 days past its close date, single champion (Marcus Hale), 2 critical support cases |
| Bluefin Media Studios | 36 | High risk |
| Crestline Realty Group | 38 | $480K CRM rollout blocked by support escalations |
| Meridian Health Network | 41 | $2.4M expansion silent for 110 days past close date |
| Brightwater Capital | 88 | Healthy, $2.39M open pipeline (strongest expansion candidate) |

Opportunity close dates are generated relative to the day the database was first seeded, so "days past close" and "closing this month" drift as time passes. Re-seed (section 7) if a demo is weeks after setup.

---

## 5. The demo script

Start each part in a **New** conversation. Expected answers below were captured on 2026-10-10.

### Step 1: Portfolio risk (0 requests, ~1–4 s)

> **Which accounts are at risk?**

Expect a ranked table: Sablewood (14), Halvorsen (23), Northwind (28), Meridian (41) as Critical, then Bluefin (36) and Crestline (38) as High. A risk review card shows **$4.83M revenue at risk**, with stalled deals at their real days past close (Northwind renewal 21, Northwind add-on 95, Meridian expansion 110) and the named competitors.

Say: "This list is calculated, not generated. Healthy accounts don't appear, and the order comes from health and risk flags."

### Step 2: Growth (0 requests, ~1 s)

> **Which accounts have expansion potential?**

Expect: "10 accounts show expansion potential: healthy (health 65+) with $7.07M of open pipeline between them. Strongest: Brightwater Capital ($2.39M, health 88), Keystone Mutual Insurance ($1.30M, health 74), Cobalt Grid Energy ($870K…)", plus a ranked table.

### Step 3: This month's forecast (0 requests, ~1 s)

> **What's closing this month?**

Expect: open deals due in the next 30 days, their total and probability-weighted value, and a table sorted by close date. On 2026-10-10 this was 6 deals worth $3.77M ($2.74M weighted).

### Step 4: Quick facts (0 requests, ~1 s each)

> **What is the revenue of Brightwater Capital?**

"Brightwater Capital's annual revenue is $2.1B (Financial Services, Strategic, North America)."

> **List contacts at Brightwater Capital**

4 contacts: Olivia Chen (Decision Maker), Jamal Wright (Champion), Hiro Tanaka (Technical Buyer), Rachel Moore (Influencer), with a table.

> **Show opportunities for Northwind Logistics**

"Northwind Logistics has 2 open opportunities worth $1.54M, plus 1 closed." The closed-lost pilot is listed but not counted.

> **What's the health score of Sablewood Manufacturing?**

"Sablewood Manufacturing's health score is 14/100 (critical)."

### Step 5: Honesty check (1 request)

> **Tell me about Acme Corp**

Expect: "I couldn't find an account called "Acme Corp" in your CRM data. Which account did you mean?" with account buttons. Click **Northwind Logistics** and APEX re-runs the question for Northwind.

Say: "It tells you when it doesn't know instead of guessing."

### Step 6: Risk review button (0 requests)

After a Northwind answer, click **Review Risks** in the suggested actions under the answer. Expect $1.54M at risk, single-threaded relationship, 2 stalled deals (21 and 95 days), 2 open critical/high cases with their real ages, and Competitors A and B.

### Step 7: The AI plan (about 12 requests, 2–2.5 min)

> **Give me a 7-day playbook for Northwind Logistics**

Expect a P1 card: headline about the at-risk $1.2M renewal, the critical support cases, Marcus Hale as the only champion, the need to reach the VP of Operations, and day-by-day actions with owners.

Ask this **at the start of the meeting** and talk through steps 1–6 while it runs, or play the recorded version (section 6). The animated notice tells the audience why it takes time.

Other good AI questions (same cost):

- **Why are we losing Halvorsen Retail?** (P1: low health, single-threaded Inventory Sync deal, past losses to Competitor C)
- **Who should I contact at Meridian?** (P2: Elena Park, the decision maker, and the HL7 feed case)
- **How are support cases affecting Crestline Realty?**

---

## 6. Recording the Loom

The script is in [LOOM_SCRIPT.md](LOOM_SCRIPT.md). For the AI plan, record the full run and cut the waiting time in editing. Record on a day with a fresh request budget and check `is_free_tier` and usage first (section 2.3).

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| AI plan returns a plain data-only plan | Daily free limit reached, or all free models busy | Use data questions; AI plans work again after the daily reset. Check usage (section 2.3). |
| An answer mentions the wrong account | Old browser conversation from before 2026-10-10 | Click **New** to start a fresh conversation |
| Backend container keeps restarting | Port clash or database not ready | `docker compose logs backend --tail 50` |
| Log shows `Falling back to local SQLite` | Database URL or driver problem | Confirm `apex-db` is healthy; `database.py` uses the `psycopg2` driver |
| Close dates look stale | Data was seeded weeks ago | `docker compose down -v` then `docker compose up -d` re-seeds (this deletes demo chats) |
| Everything is slow | Free model busy | Wait a minute; fallbacks switch automatically |

Useful log filter while presenting:

```powershell
docker compose logs -f backend | Select-String "INPUT\]|Direct Answer|Checkpoint|API Retry|ERROR"
```

---

## 8. Interview talking points

- **Grounded output.** A formatter step that used to let the LLM invent companies ("Acme Corp", "Globex") now only reorganises data that is present, and a post-check removes any opportunity, risk or placeholder not found in the source data.
- **Deterministic where it matters.** Revenue, health, contacts, pipeline, expansion and closing-soon questions are answered in Python from the CRM tables: no LLM cost, no hallucination, under a second.
- **Calculated urgency.** P1/P2/P3 comes from health score and open case severity.
- **Resilience.** Free-model fallbacks; billing and daily-limit errors fail fast; when the LLM is unavailable a data-only plan is returned.
- **Account resolution.** Whole-word matching (an earlier substring match let the word "I" resolve to Northwind Logistics), per-conversation sessions, and clarifications that only resume when the reply names a real account.
- **Testing.** 88 automated tests plus a live check script that drives the running Docker stack through the API.

Known limits to state honestly: AI plans take 2–2.5 minutes on free models and are capped at about 6 per day; quick-action buttons such as "Draft email" still return a full report rather than the email itself.
