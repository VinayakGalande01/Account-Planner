# APEX — Account Planning & Execution Intelligence

## ❓ What it does?
**APEX** is a sophisticated AI-powered account planning assistant designed for sales teams, account managers, and revenue leaders. It automates the manual grind of account analysis by acting as a "human-in-the-loop" AI colleague. 

Key capabilities include:
- **Account Health Scoring:** Automatically calculates scores (0-100) based on revenue, engagement, and deal progression.
- **Engagement Momentum:** Analyzes interaction frequency and breadth to detect account warmth.
- **Risk Detection:** Identifies "single-threaded" deals, stalled opportunities, and unresolved critical cases.
- **AI Chat Interface:** Natural language interface to query account details and generate structured account plans.

## 🎯 Why does it exist?
Account planning is often a manual, time-consuming process requiring sales professionals to dig through fragmented CRM data, spreadsheets, and emails. 

APEX exists to:
- **Save Time:** Reduce hours of manual research into seconds.
- **Surface Hidden Risks:** Automatically detect stalled deals and poor engagement before they lead to churn.
- **Unify Data & AI:** Bring together structured CRM-style data and Large Language Models (LLMs) to provide actionable, multi-perspective insights (from AM, VP, Data perspectives).

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI
- **Data Processing:** Pandas, NumPy
- **AI Integration:** Local LLMs (Ollama / Phi-3) for Intent Classification, Reasoning, and Response Generation.
- **Environment:** Python 3.x

### Frontend
- **Framework:** Next.js 15+ (React 19)
- **Styling:** Tailwind CSS
- **Animations:** Framer Motion
- **Visualization:** Recharts
- **Language:** TypeScript

## 🧠 Architecture Overview
The system employs a sophisticated 3-layer AI pipeline in the backend:
1. **Layer 1 - Intent Classification:** Parses the user's natural language query to determine the intent (e.g., account review, risk assessment) and extracts entities like account names.
2. **Layer 2 - Reasoning Engine:** Retrieves relevant data and runs multi-perspective reasoning threads (e.g., analyzing from Account Manager, VP, and Data angles) to synthesize a consensus.
3. **Layer 3 - Response Generator:** Crafts role-specific, tailored responses based on the synthesized consensus and retrieved CRM data.

## 🚦 Getting Started

Follow these steps to set up and run the entire ecosystem locally.

### 1. Prerequisite: Local LLM (Ollama)
APEX relies on a local LLM server to process queries securely without exposing proprietary data.
1. Install [Ollama](https://ollama.ai/).
2. Pull the required model:
   ```bash
   ollama pull phi3:mini
   ```
3. Ensure Ollama is running (typically on `http://localhost:11434`).

### 2. Setup the Backend
1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```
2. **Configuration:** Update the `DATA_PATH` in `backend/main.py` to point to your local `.xlsx` data source.
3. **Install Dependencies:**
   ```bash
   poetry install
   # Or using pip: pip install -r requirements.txt
   ```
4. **Run the Server:**
   ```bash
   uvicorn main:app --reload --port 8001
   ```
   *API will be live at `http://localhost:8001`.*

### 3. Setup the Frontend
1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```
2. **Install Dependencies:**
   ```bash
   npm install
   ```
3. **Run the Development Server:**
   ```bash
   npm run dev
   ```
   *Dashboard will be live at `http://localhost:3000`.*

## 📊 Data Schema
APEX expects structured CRM data in an Excel format (`.xlsx`) containing the following sheets:
1. **Account:** Profile, tier, revenue, territory.
2. **Opportunity:** Deals, stages, amounts, competitors.
3. **Contact:** Roles, engagement levels, seniority.
4. **Activity:** Calls, emails, meetings.
5. **Case:** Support tickets, severity, CSAT scores.

## 🛠️ Verification & Troubleshooting
- **Backend Check:** Visit `http://localhost:8001/` to see the API health message.
- **Data Issues:** Ensure the Excel file path in `main.py` is correct and accessible.
- **LLM Connectivity:** Ensure Ollama is running *before* starting the backend, as it connects to the model on startup.

## 📝 License
Proprietary. All rights reserved.
