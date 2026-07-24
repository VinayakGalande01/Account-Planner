# APEX — Account Planning & Execution Intelligence

## ❓ What it does?
**APEX** is a sophisticated, enterprise-grade AI-powered account planning assistant designed for sales teams, account managers, and revenue leaders. It automates the manual grind of account analysis by acting as a "human-in-the-loop" AI colleague. 

Key capabilities include:
- **Account Health Scoring:** Automatically calculates scores (0-100) based on revenue, engagement, and deal progression.
- **Engagement Momentum:** Analyzes interaction frequency and breadth to detect account warmth.
- **Risk Detection:** Identifies "single-threaded" deals, stalled opportunities, and unresolved critical support cases.
- **AI Chat Interface:** Natural language interface to query account details and stream structured, multi-perspective strategic plans.
- **AI Evaluation & Observability:** Internal metrics tracking, prompt evaluation runner, and end-to-end request trace telemetry.

---

## 🛠️ Tech Stack

### Backend
- **Framework:** FastAPI
- **Data Processing:** Pandas, NumPy
- **Database Layer:** Supabase-hosted PostgreSQL (Primary) with SQLAlchemy connection pooling, falling back automatically to local **SQLite** (`local_planner.db`) on connection timeout.
- **AI Integration:** Google Gemini Cloud API (Primary routing) with configurable local LLM fallback (Ollama running Llama/Qwen) for zero-data-egress requirements.
- **Vector Search:** ChromaDB for local semantic RAG.

### Frontend
- **Framework:** Next.js 15+ (React 19)
- **Styling:** Vanilla CSS (Tailwind CSS in legacy backup components)
- **Animations:** Framer Motion
- **Visualization:** Recharts
- **Language:** TypeScript

---

## 🧠 Architecture Overview
The system employs a decoupled 4-phase AI reasoning pipeline:
1. **Phase 1 - Intent Classification:** Parses the user's natural language query to determine the intent and extracts target entities.
2. **Phase 2 - Retrieval Layer:** Queries the database (Postgres/SQLite) and performs semantic searches (ChromaDB) to fetch target-scoped context.
3. **Phase 3 - Reasoning Engine:** Analyzes data across multiple personas (Account Manager, VP, and Data perspective) to produce a Structured Intelligence Package (SIP).
4. **Phase 4 - Narrative Streamer:** Crafts role-specific responses and streams markdown-formatted strategies to the user in real-time.

---

## 🚦 Getting Started

### 1. Prerequisites & Environment Setup
Create a `.env` file inside the `backend` directory with the following variables:
```env
# AI API Key (Required for Gemini mode)
GEMINI_API_KEY=your_gemini_api_key_here

# Database Config (Defaults to SQLite if omitted or offline)
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres

# Model Configuration
MODEL_NAME=gemini-1.5-flash
```

### 2. Setup the Backend
1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```
2. **Install Dependencies:**
   ```bash
   poetry install
   # Or using pip: pip install -r requirements.txt
   ```
3. **Seed the database (Optional):**
   ```bash
   python seed_golden_dataset.py
   ```
4. **Run the Server:**
   ```bash
   uvicorn main:app --reload --port 8001
   ```
   *The API will be live at `http://localhost:8001`.*

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
   *The dashboard will be live at `http://localhost:3000`.*

---

## 📊 Documentation
For in-depth explanations, check the dedicated [documentation directory](./documentation/):
- [README Index](./documentation/README.md): Index of system topologies and diagrams.
- [Architectural Blueprint](./documentation/apex_architectural_blueprint.md): Detailed high/low level designs and sequence flows.
- [Database Architecture](./documentation/database_architecture.md): Hybrid Postgres/SQLite configurations and schema references.
- [Multi-Tenancy Guide](./documentation/TENANCY_DOCUMENTATION.md): Logical user isolation and access check mechanisms.
- [Local LLM Optimization](./documentation/local_llm_optimization_guide.md): Guide for running APEX in local-offline Ollama mode.

## 📝 License
Proprietary. All rights reserved.
