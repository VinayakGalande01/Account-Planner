# APEX — Account Planning & Execution Intelligence: Project Breakdown

This document provides a comprehensive A-to-Z technical and architectural breakdown of the **APEX (Account Planner)** project.

## 1. Project Overview

**APEX** is a sophisticated, AI-powered account planning assistant designed to automate account analysis for sales teams, account managers, and revenue leaders. By combining CRM data with Large Language Models (LLMs), APEX acts as a "human-in-the-loop" co-pilot, generating actionable insights, health scores, risk assessments, and structured account plans.

### Key Value Propositions:
- **Data Synthesis:** Aggregates scattered CRM data (accounts, opportunities, activities, cases) into a unified view.
- **Automated Scoring:** Computes proprietary Health and Engagement scores.
- **AI-Driven Intelligence:** Uses a local LLM to converse with the user, providing deep insights without sending sensitive CRM data to cloud providers.

---

## 2. High-Level Architecture

The system operates on a modern, decoupled client-server architecture:

1.  **Frontend (Client):** Next.js 15+ (React 19) application utilizing Tailwind CSS, Framer Motion, and Recharts.
2.  **Backend (API Server):** High-performance FastAPI application.
3.  **Data Engine:** Pandas-based data processor that ingests local Excel data (`SF_AccountingAgent_DummyData.xlsx`).
4.  **AI Engine:** Local LLM inference server via **Ollama**, running the `phi3:mini` model.

---

## 3. Data Schema & Ingestion

The core source of truth is an Excel file containing 5 distinct sheets, representing standard CRM entities:

1.  **Account:** Base company profile, annual revenue, territory, tier.
2.  **Opportunity:** Pipeline data, deal stages, probability, amounts, expected close dates.
3.  **Contact:** Decision makers, roles, engagement levels.
4.  **Activity:** Logged calls, emails, meetings, and dates.
5.  **Case:** Customer support tickets, severity, and CSAT (Customer Satisfaction) scores.

Data is ingested securely on the backend, ensuring the LLM only accesses what is explicitly passed as context.

---

## 4. Backend Breakdown (`/backend`)

The backend is built with Python and FastAPI. It serves two primary functions: executing data logic and orchestrating the LLM.

### A. `data_engine.py` (The Brains)
This file is the analytical core of the application. It uses `pandas` to read the Excel file and perform complex aggregations.
*   **Health Score Calculation:** Calculates a 0-100 score based on 5 weighted pillars:
    *   *Revenue Health (25%)*
    *   *Relationship Depth (20%)*
    *   *Engagement Momentum (25%)*
    *   *Deal Progression (20%)*
    *   *Support & Satisfaction (10%)*
*   **Pipeline Analysis:** Aggregates total pipeline value, weighted values, and groups deals by stage.
*   **Context Formatter:** The `get_formatted_account_data()` method transforms tabular data into a structured text string designed specifically for LLM ingestion.

### B. `main.py` (The API Gateway)
This file sets up the FastAPI server, handles CORS for the frontend, and exposes the REST endpoints.
*   **Endpoints:**
    *   `GET /api/accounts/enriched`: Returns a list of all accounts appended with real-time health scores and pipeline summaries.
    *   `GET /api/accounts/{account_id}/details`: Returns structured JSON for a specific account's opportunities, contacts, and cases.
    *   `GET /api/pipeline/summary`: Returns the global aggregated pipeline view.
*   **The LLM Endpoint (`POST /api/chat`):**
    *   Receives a user query.
    *   Detects if the query references a specific account.
    *   Extracts the specific data context for that account via the `DataEngine`.
    *   Constructs a highly engineered **System Prompt** defining APEX's persona, rules, and the injected tabular data.
    *   Streams the LLM response asynchronously via `httpx` to provide a real-time ChatGPT-like typing experience on the frontend.

---

## 5. Frontend Breakdown (`/frontend`)

The frontend is a dynamic, single-page dashboard built on Next.js.

### A. State Management (`src/context/DataContext.tsx`)
A React Context provider orchestrates global state across the app. It handles fetching the enriched accounts from the backend on load and manages the globally `selectedAccount`, `activeTab`, and `aiCommand` interactions.

### B. Core UI Components (`src/components/`)
*   **`MainLayout.tsx` & `Sidebar.tsx`:** Provide the application shell, navigation, and persistent system health monitoring (pinging the backend).
*   **`PortfolioLedger.tsx`:** The main tabular view displaying all accounts, their computed health tiers (🟢 Healthy, 🟡 Needs Attention, 🔴 Critical), pipeline values, and last activity.
*   **`AccountDetail.tsx`:** A deep-dive view into a selected account, showcasing specific metrics, active deals, and recent cases.
*   **`PipelineView.tsx` & `KPIGrid.tsx`:** Data visualization components providing high-level revenue metrics and pipeline funnel analysis.
*   **`ChatTerminal.tsx`:** The interactive AI interface. It captures user inputs, sends them to `/api/chat`, and renders the streaming Markdown response.

### C. Styling & UX
*   **Tailwind CSS:** Used for utility-first, highly responsive styling (`globals.css`).
*   **WebGL / Framer Motion:** Enhances the application with premium, modern micro-interactions and smooth transitions between views (`WebGLGrid.tsx`, `InteractiveGrid.tsx`).

---

## 6. The AI Orchestration Flow (How it works)

When a user types *"Give me an account plan for DataOsis"* into the Chat Terminal:
1.  **Frontend:** Sends the query to `POST /api/chat`.
2.  **Backend Routing:** Matches "DataOsis" to `Account_ID` via pandas.
3.  **Data Extraction:** `data_engine.py` pulls every row related to DataOsis from the 5 Excel sheets.
4.  **Prompt Injection:** The backend injects the DataOsis rows into the massive `APEX_SYSTEM_PROMPT`.
5.  **Inference:** The payload is sent to the local Ollama instance (`phi3:mini`).
6.  **Streaming:** The LLM reads the data, formats a structured response based on its system instructions, and streams tokens back through FastAPI to the Next.js UI.

---

## 7. Running the Ecosystem

To run the application locally:
1.  **Start Ollama:** Ensure `ollama run phi3:mini` is running in the background.
2.  **Start Backend:** Navigate to `/backend`, run `poetry install` (or `pip install -r requirements.txt`), and execute `uvicorn main:app --reload --port 8001`.
3.  **Start Frontend:** Navigate to `/frontend`, run `npm install`, and execute `npm run dev`.
4.  **Access:** Open `http://localhost:3000` in the browser.
