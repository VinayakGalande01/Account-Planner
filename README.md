# APEX: AI Co-pilot for Account Planning

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Next.js 14](https://img.shields.io/badge/Next.js-14-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/) [![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/) [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**APEX reads your CRM, tells you which accounts are about to slip and why, and writes the account plan to save them.**

**Live demo: [account-planner-ten.vercel.app](https://account-planner-ten.vercel.app)**. Click **Log In**, then **Use demo account** (`demo@apex.example` / `ApexDemo#2026`).

> The demo runs on free hosting. Outside about 10:30–19:30 IST the first visit can take ~3 minutes while the server wakes up. Data questions (at-risk accounts, revenue, deals closing) answer in seconds; full AI account plans use free AI models and take about 2 minutes.

![APEX dashboard: portfolio health and AI-detected risks](docs/images/dashboard.png)

---

## The business problem

Renewals and expansions rarely die without warning. The signs are already in the CRM: a $1M deal with only one contact, an opportunity no one has touched in three months, a critical support case the customer's CFO is escalating. They're spread across Opportunities, Contacts, Activities and Cases, so nobody sees them until the deal slips.

## What APEX does

| | |
|---|---|
| **Account health score (0–100)** | Calculated for every account from pipeline vs. business won, contact coverage, engagement recency, deal progression and support quality. |
| **Automatic risk detection** | Flags single-threaded deals, stalled strategic accounts, deals past close date, open critical cases and low CSAT. These are deterministic rules, so you can see exactly why an account is flagged. |
| **One-click AI account plan** | Click a flagged account and APEX writes a plan grounded in that account's records: who to call, what's at stake and what to do this week. |
| **Answers for each role** | The same data is framed for an Account Manager, a VP of Sales or an executive. |
| **Grounding checks** | Each AI answer is scored against the CRM values it cites, and pipeline totals are itemised by a calculation auditor. |

| Accounts ranked by health | AI account plan for an at-risk account (one click from the dashboard) |
|---|---|
| ![Accounts](docs/images/accounts.png) | ![Account plan](docs/images/account-plan.png) |

> All companies, people and numbers in the demo are fictional (see [`backend/demo_dataset.py`](backend/demo_dataset.py)).

---

## Run the demo (one command)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
# Optional, enables AI account plans (dashboard and risk detection work without it)
echo "OPENROUTER_API_KEY=your_key_here" > .env

docker compose up --build
```

Open **http://localhost:3000**, click **Log In**, then **Use demo account** (`demo@apex.example` / `ApexDemo#2026`).

The first build downloads Python ML dependencies and takes several minutes. Later starts are fast.

> **Model:** AI calls go through [OpenRouter](https://openrouter.ai) using free models only: `nvidia/nemotron-3-super-120b-a12b:free`, falling back to Gemma 4 when it is busy (change with `OPENROUTER_MODEL` / `OPENROUTER_FALLBACK_MODELS`). An account plan uses about 3 model calls (`AI_FAST_MODE`, on by default; set `AI_FAST_MODE=0` for the full multi-stage pipeline, about 12 calls). OpenRouter's free tier allows 50 requests per day, roughly 15 AI plans; data questions (revenue, contacts, at-risk lists) use none.

---

## Architecture & System Design

### 1. High-Level System Architecture

```mermaid
flowchart TB
    subgraph INGESTION["1. Data Ingestion & Storage"]
        CRM["CRM Data Sources<br/>(Salesforce / HubSpot / Excel)"] --> SYNC["Sync Daemon / Ingestion Engine<br/>(backend/sync_daemon.py)"]
        SYNC --> DB[("Primary Database<br/>PostgreSQL / Supabase<br/>(SQLite local fallback)")]
    end

    subgraph DETERMINISTIC["2. Deterministic Analytics Engine"]
        DB --> HEALTH["Health Scoring Engine<br/>• Pipeline vs. Closed Won<br/>• Contact Coverage<br/>• Engagement Recency<br/>(Score: 0–100)"]
        DB --> RISK["Risk Detection Rules<br/>• Single-Threaded Deals<br/>• Stalled Strategic Accounts<br/>• Stale Close Dates<br/>• Unresolved Critical Cases"]
        DB --> HYGIENE["CRM Hygiene Auditor<br/>• Missing Contact Roles<br/>• Incomplete Fields"]
    end

    subgraph RAG["3. Vector Store & Semantic Retrieval"]
        DB --> EMBED["FastEmbed / Sentence-Transformers<br/>(Activity & Note Embeddings)"]
        EMBED --> CHROMA[("ChromaDB Vector Store<br/>Semantic Search")]
    end

    subgraph ORCHESTRATOR["4. AI Reasoning & Co-Pilot (FastAPI)"]
        PROMPT["User Request / Query Router"] --> INTENT{"Intent Classification<br/>(Data Query vs. Plan)"}
        INTENT -- "Data Query" --> SQL_EXEC["Deterministic Calculation & SQL"]
        INTENT -- "Account Plan" --> AGENT_ORCH["Multi-Perspective Reasoning Engine"]
        
        CHROMA --> AGENT_ORCH
        DB --> AGENT_ORCH
        
        subgraph AGENTS["Role Perspectives"]
            AGENT_ORCH --> AM["Account Manager<br/>(Tactical steps & contacts)"]
            AGENT_ORCH --> VP["VP of Sales<br/>(Revenue risk & forecasting)"]
            AGENT_ORCH --> EXEC["Executive<br/>(High-level summary)"]
        end

        AGENTS --> AUDITOR["Grounding & Calculation Auditor<br/>(Verifies claims against CRM values)"]
    end

    subgraph LLM_LAYER["5. Model Provider Layer"]
        AUDITOR <--> LLMS{{"LLM Providers<br/>• OpenRouter (Nemotron / Gemma)<br/>• Google Gemini API<br/>• Local Ollama"}}
    end

    subgraph PRESENTATION["6. Frontend Presentation (Next.js 14)"]
        HEALTH --> DASHBOARD["Next.js Responsive Dashboard<br/>(React · TypeScript · Tailwind · Recharts)"]
        RISK --> DASHBOARD
        SQL_EXEC --> DASHBOARD
        AUDITOR --> DASHBOARD
        DASHBOARD --> USER(("Sales Team / Executive"))
    end
```

### 2. End-to-End Data Flow

```mermaid
sequenceDiagram
    autonumber
    actor User as Sales Rep / VP
    participant UI as Next.js Dashboard
    participant API as FastAPI Backend
    participant Engine as Deterministic Engines
    participant Vector as ChromaDB
    participant DB as PostgreSQL / SQLite
    participant LLM as Model Provider (OpenRouter / Gemini / Ollama)

    User->>UI: View Portfolio / Request Account Plan
    UI->>API: GET /api/accounts or POST /api/plan
    activate API

    alt Request: Portfolio & Health Status
        API->>Engine: Run Deterministic Rules & Health Scoring
        Engine->>DB: Query Accounts, Deals, Contacts, Cases
        DB-->>Engine: Raw Records
        Engine-->>API: Health Scores (0-100) & Flagged Risks
        API-->>UI: Render Dashboard Cards & Risk Badges
    else Request: AI Account Plan Generation
        API->>DB: Fetch structured account data (pipeline, stage, team)
        DB-->>API: Account metrics & contact records
        API->>Vector: Query semantic context (recent activity logs, notes)
        Vector-->>API: Relevant interaction snippets
        API->>LLM: Prompt with CRM context + Multi-Role Reasoning instructions
        LLM-->>API: Synthesized strategy & action plan
        API->>Engine: Grounding check (Audit figures vs. CRM ground truth)
        Engine-->>API: Grounding score & audited plan
        API-->>UI: Display role-specific plan with grounded recommendations
    end

    deactivate API
    UI-->>User: Visualized insights & actionable next steps
```

---

## Technical Stack & Components

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, pandas, ChromaDB, FastEmbed / sentence-transformers
- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, Recharts, Framer Motion
- **Database:** PostgreSQL / Supabase with multi-tenant row-level isolation (SQLite fallback for local runs)
- **AI Models:** OpenRouter API (Nemotron 3 Super, Gemma 4 fallback), Google Gemini API, or fully local Ollama
- **DevOps & Infrastructure:** Docker, Docker Compose, GitHub Actions CI, Render (backend), Vercel (frontend), Supabase (database)

More detail: [architecture docs](docs/architecture/README.md) · [case study](docs/CASE_STUDY.md)

---

## Use your own data

APEX loads the built-in demo dataset by default. To load a Salesforce-style Excel export instead (sheets: `Account`, `Opportunity`, `Contact`, `Activity`, `Case`), set `DATA_PATH=/path/to/export.xlsx` for the backend. The column format is shown in [`backend/demo_crm_data.xlsx`](backend/demo_crm_data.xlsx), which you can regenerate with `python backend/demo_dataset.py`. Early Salesforce and HubSpot API sync functions are in [`backend/sync_daemon.py`](backend/sync_daemon.py). They're untested against a live org.

## Local development (without Docker)

```bash
# Backend (http://localhost:8002)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8002

# Frontend (http://localhost:3000), in a second terminal
cd frontend
npm install
BACKEND_URL=http://localhost:8002 AUTH_URL=http://localhost:8002 npm run dev
```

Without `DATABASE_URL` the backend uses a local SQLite file. Optional backend settings (environment variables or `backend/.env`): `OPENROUTER_API_KEY` / `OPENROUTER_MODEL`, `GEMINI_API_KEY`, `DATABASE_URL`, `LLM_URL` / `MODEL_NAME` for a local Ollama model.
