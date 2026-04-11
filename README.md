# APEX — Account Planning & Execution Intelligence

**APEX** is a sophisticated AI-powered account planning assistant designed to help sales teams, account managers, and revenue leaders automate the manual grind of account analysis. By integrating CRM-style data with Large Language Models (LLMs), APEX provides actionable insights, health scores, and risk assessments to drive business growth.

---

## 🚀 Overview

The project consists of a high-performance **FastAPI** backend and a modern **Next.js** frontend. It processes account data from Excel and interacts with a local LLM to provide a "human-in-the-loop" AI colleague experience.

### Key Features
- **Account Health Scorecard:** Automatically calculates scores (0-100) based on revenue, engagement, and deal progression.
- **Engagement Momentum:** Analyzes interaction frequency and breadth to detect account warmth.
- **Risk Detection:** Identifies "single-threaded" deals, stalled opportunities, and unresolved critical cases.
- **AI Chat Interface:** Natural language interface to query account details and generate structured account plans.

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI
- **Data Logic:** Pandas, NumPy
- **AI Integration:** Local LLM (Ollama / Phi-3)
- **Environment:** Python 3.x

### Frontend
- **Framework:** Next.js 15+ (React 19)
- **Styling:** Tailwind CSS
- **Animations:** Framer Motion
- **Visualization:** Recharts
- **Language:** TypeScript

---

## 📁 Project Structure

```text
Account-Planner/
├── backend/            # FastAPI application
│   ├── main.py         # API entry point & LLM integration
│   ├── data_engine.py  # Data processing and scoring logic
│   └── README.md       # Backend setup guide
├── frontend/           # Next.js application
│   ├── src/            # React components & pages
│   └── README.md       # Frontend setup guide
├── pyproject.toml      # Poetry configuration
└── requirements.txt    # Python dependencies
```

---

## 🚦 Getting Started

Follow these steps to set up and run the entire ecosystem locally.

### 1. Prerequisite: Local LLM (Ollama)
APEX relies on a local LLM server to process queries.
1.  Install [Ollama](https://ollama.ai/).
2.  Pull the required model (used in `backend/main.py`):
    ```bash
    ollama pull phi3:mini
    ```
3.  Ensure Ollama is running (typically on `http://localhost:11434` or `http://localhost:8000` depending on your config).

### 2. Setup the Backend
The backend manages data logic and AI orchestration.
1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```
2.  **Configuration:** Update the `DATA_PATH` in `backend/main.py` (Line 24) to point to your local `.xlsx` file if it differs from the default.
3.  **Install Dependencies:**
    ```bash
    # If using Poetry:
    poetry install
    # If using Pip:
    pip install -r ../requirements.txt
    ```
4.  **Run the Server:**
    ```bash
    uvicorn main:app --reload --port 8001
    ```
    *The API will be live at `http://localhost:8001`.*

### 3. Setup the Frontend
The frontend provides the interactive dashboard.
1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Install Dependencies:**
    ```bash
    npm install
    ```
3.  **Run the Development Server:**
    ```bash
    npm run dev
    ```
    *The Dashboard will be live at `http://localhost:3000`.*

---

## 🛠️ Verification & Troubleshooting

-   **Backend Health Check:** Open `http://localhost:8001/` in your browser. You should see `{"message": "Account Planner Agent API is running"}`.
-   **Data Loading:** If the backend fails to start, ensure the Excel file path in `main.py` exists and is accessible.
-   **LLM Connectivity:** Ensure Ollama is running before starting the backend, as it attempts to connect to the model on startup.

---

## 📊 Data Schema
APEX expects data in an Excel format (`.xlsx`) with the following sheets:
1. **Account**: Profile, tier, revenue, territory.
2. **Opportunity**: Deals, stages, amounts, competitors.
3. **Contact**: Roles, engagement levels, seniority.
4. **Activity**: Calls, emails, meetings.
5. **Case**: Support tickets, severity, CSAT scores.

---

## 📝 License
Proprietary. All rights reserved.
