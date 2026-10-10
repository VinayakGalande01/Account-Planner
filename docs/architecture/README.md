# APEX Account Planner Documentation Index

Welcome to the documentation folder for the APEX Account Planner. This index details the files available and explains the architectural distinction between the current running prototype/development setup and the projected production blueprints.

---

## 1. System State Clarification: Current vs. Target Scale

The diagrams and files in this folder describe both the **current active configuration** and the **target production reference architecture** designed to scale up to 100 million active users.

### Current Implementation State (Development/Local-First)
* **Hosting Topology:** Single-process local FastAPI backend (`main.py`) paired with a Next.js frontend, typically run locally under Uvicorn.
* **AI Reasoning Engine:** Integrated with the cloud-hosted **Google Gemini API** (Gemini 1.5/3.5/Pro/Flash) as the primary cognitive routing layer.
* **Database Layer:** Hosted **Supabase PostgreSQL** cloud instance acting as the primary database with an active connection pool, falling back to a local **SQLite** database (`local_planner.db`) if network errors occur.
* **Search / RAG:** Local vector index run using **ChromaDB**.

### Target Production Blueprint (Future Roadmap)
* **Hosting Topology:** Managed Kubernetes cluster deployed via **AWS EKS** with Application Load Balancers (ALBs) and edge Content Delivery Networks (AWS CloudFront CDN).
* **AI Reasoning Engine:** Decoupled GPU inference zone running a private **vLLM / Ollama** load-balanced cluster.
* **Event & Ingestion Pipeline:** Asynchronous background CRM ingestion tasks and score calculations managed using **Apache Kafka** brokers and Celery async workers.
* **Data Layer:** Multi-region active-active distributed databases sharded by organization tenant context.

For folders containing static diagrams (e.g., [Cloud_Architecture](./Cloud_Architecture/), [User_Journey](./User_Journey/), [Complete_Blueprint](./Complete_Blueprint/), and [API_Architecture](./API_Architecture/)), please note that these represent the **target production topology** and not the active development environment.

---

## 2. Core Documentation Files

- [Architectural Master Blueprint](file:///Users/theabhijitjagtap/Account-Planner/documentation/apex_architectural_blueprint.md): Complete high-level and low-level design, sequence flows, operational design patterns, and reliability runbooks.
- [Database Architecture & Schema](file:///Users/theabhijitjagtap/Account-Planner/documentation/database_architecture.md): The hybrid database setup (Postgres + SQLite fallback) and detailed schema maps of the core, evaluation, and observability tables.
- [Multi-Tenancy Architecture](file:///Users/theabhijitjagtap/Account-Planner/documentation/TENANCY_DOCUMENTATION.md): Logic behind logical user-level data isolation, FastAPI request-scoping, and ChromaDB metadata tenant filtering.
- [Local LLM Optimization Guide](file:///Users/theabhijitjagtap/Account-Planner/documentation/local_llm_optimization_guide.md): Optimization guide for compiling context size and quantizing models when running in offline Ollama-inference fallback mode.
