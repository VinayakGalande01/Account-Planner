# Summary of LLM Timeout & Context Resolution Session (17 June 2026)

This document provides a detailed summary of the diagnostics, code changes, and execution results for resolving the local LLM timeouts and performance bottlenecks on an 8GB RAM machine.

---

## 1. Initial State & Configuration Goals
The project was configured to run a local LLM (`gemma2:2b`) via a custom `AI_STACK` server running on port `8000`. The initial pipeline had several limitations:
- **HTTP 404 Errors:** Caused by a double slash (`//`) typo in the URL mapping of `backend/.env` and `llm_cache.json`.
- **Pipeline Timeouts:** Processing a massive JSON payload (15+ opportunities) on CPU-only hardware took over 3 minutes, triggering backend and browser connection timeouts.
- **Hardware Profile:** The system was running on a laptop with an **Intel Core i3-10110U (2 Cores)**, **8GB DDR4 RAM** (with only 1.3GB available), and **Integrated Intel UHD Graphics** (no dedicated VRAM/GPU).

---

## 2. Implemented Solutions & Code Changes

To make the app robust on a resource-constrained local setup, the following changes were successfully executed:

### A. Dynamic Context Truncation & Optimization
- **File:** [reasoning_engine.py](file:///e:/Account%20Planner/backend/reasoning_engine.py)
- **Change:** Modified `summarize_large_dataset` to:
  1. Accept a dynamic `requested_count` parameter extracted from the query.
  2. Aggressively strip out empty/null fields (such as `contacts: []`, `cases: []`, and empty sub-structures) to reduce the JSON token footprint.
  3. Truncate the opportunity list to the requested size (defaulting to 5) before sending it to the model.

### B. Extended Pipeline Timeouts
- **File:** [reasoning_engine.py](file:///e:/Account%20Planner/backend/reasoning_engine.py) and [agent_orchestrator.py](file:///e:/Account%20Planner/backend/agent_orchestrator.py)
- **Change:** Increased default execution timeouts for reasoning perspective threads (from 15/30 seconds to 300/600 seconds) to accommodate CPU-only generation.

### C. Keep-Alive Heartbeat Streaming
- **File:** [main.py](file:///e:/Account%20Planner/backend/main.py)
- **Change:** Wrapped the synchronous agent pipeline call in a background async task. While the LLM is generating (taking 30–60 seconds per agent on CPU), the stream yields keep-alive status updates (`[SYS_LOG] Processing... Reasoning engine is active.`) every 5 seconds to reset the browser’s network idle timer.

### D. Google Gemini API Cloud Fallback
- **File:** [reasoning_engine.py](file:///e:/Account%20Planner/backend/reasoning_engine.py)
- **Change:** Added a check for `GEMINI_API_KEY` in `backend/.env`. If the key is present, calls to `_call_llm` are routed to Google's cloud Gemini API (resolving in under 2 seconds). Otherwise, it falls back to the local `gemma2:2b` server.

---

## 3. Post-Implementation Diagnostic Milestones

### Milestone 1: Local Server Refused Connections (`WinError 10061`)
- **Observation:** The backend fallback returned a `WinError 10061` message.
- **Diagnostic:** The local model server was either shut down or not listening on port `8000`.
- **Resolution:** Starting the local AI Stack server resolved the connection issue.

### Milestone 2: Successful 4-Minute Execution (Validation of Heartbeats)
- **Observation:** The query completed in **245 seconds (4.08 minutes)**.
- **Diagnostic:** The browser connection remained open the entire time without dropping, proving the **Keep-Alive Heartbeats** successfully prevented browser idle timeouts.

### Milestone 3: Missing Playbooks/Narratives on the UI
- **Observation:** The frontend rendered the database table and grounding metrics, but did not display the generated narrative or the 7-day playbook.
- **Diagnostic:** 
  1. In [intent_classifier.py](file:///e:/Account%20Planner/backend/intent_classifier.py), the query *"Give me the top 5 opportunities..."* is classified as `OPPORTUNITY_RANKING` with **`OPERATIONAL`** complexity via strict keyword regex matching.
  2. In [section_mapper.py](file:///e:/Account%20Planner/backend/section_mapper.py), queries classified as `OPERATIONAL` are designed to display **only** the data table, intentionally filtering out the narrative and playbooks. 
  3. Strategic playbooks are reserved for `STRATEGIC` and `EXECUTIVE` queries (e.g. *"Create a relationship strategy and playbook for ACC025"*).

---

## 4. Hardware Recommendations for Future Scale

| Metric | Minimum (CPU-Only Local) | Recommended (GPU Accelerated Local) | Cloud Deployment (Hybrid) |
| :--- | :--- | :--- | :--- |
| **RAM** | 8 GB - 12 GB | 16 GB - 32 GB | 2 GB - 4 GB |
| **GPU/VRAM** | Integrated | Dedicated NVIDIA GPU (6GB+ VRAM) | Integrated |
| **Speed** | Slow (30s - 4mins) | Fast (2s - 10s) | Instant (sub-2s) |
| **Model** | 1.5B - 2B Quantized | 7B - 8B FP16 | Any API Endpoint |


What is covered in the summary:
1. **Initial Constraints**: Analysis of the local setup (dual-core CPU, 8GB RAM) and the double-slash HTTP 404 connection typos.
2. **Key Implementations**: Details on the dynamic context truncation (cleaning nulls/empty fields), backend timeout extensions, the Keep-Alive Heartbeat loop (yielding messages every 5 seconds to prevent browser drops), and the Gemini API Cloud Fallback integration.
3. **Log & UI Diagnostics**: Explanations of the WinError 10061 connection refusal error, the successful 4.08-minute run (which proved the heartbeats worked), and why the playbooks are hidden by design on OPERATIONAL complexity queries according to section_mapper.py.
4. **Hardware Guidelines**: Recommended specs for running models locally vs. utilizing cloud models.