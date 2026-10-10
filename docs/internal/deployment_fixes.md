# Deployment Fixes Log (APEX demo prep)

Internal record of the demo-hardening work done on 2026-10-09 and 2026-10-10.
It covers what was found, what was changed, and what is still open.
No secrets are recorded here.

---

## 1. Goal

Turn APEX (AI sales co-pilot: FastAPI + Next.js 15 + Supabase Postgres / SQLite fallback + ChromaDB RAG)
into a client-facing demo for Dataosis AI. Seven tasks were set:

1. Security: get `data.db`, `llm_cache.json` and `logs/*.log` out of git, and check them for real data or keys.
2. Seed believable dummy CRM data, including at-risk scenarios.
3. One-command run on a fresh machine (`docker compose up --build`).
4. Move internal docs out of the repo root into `docs/internal/`.
5. Client-facing README with screenshots, outcomes, architecture and "built by Dataosis".
6. A smooth demo path: login → dashboard → at-risk account → AI plan.
7. A 2-minute Loom script and a one-page case study.

---

## 2. Status by task

| # | Task | Status | Where |
|---|------|--------|-------|
| 1 | Security cleanup | Done | `.gitignore` covers `*.db`, `*.log`, `llm_cache.json`, `.env`, `chroma_db/`, and the old real-name xlsx. These files are removed from tracking (staged deletions). |
| 2 | Dummy CRM data | Done | `backend/demo_dataset.py` → `backend/demo_crm_data.xlsx`. Seeded on first backend start. |
| 3 | One-command run | **Open: Docker build not yet verified** | See section 5 |
| 4 | Root cleanup | Done | `docs/internal/`, `docs/architecture/` |
| 5 | README | Done | `README.md`, screenshots in `docs/images/` |
| 6 | Demo path | Ran end to end on 2026-10-09 (an account plan takes ~35s in the UI through OpenRouter). Re-check in Docker. | — |
| 7 | Loom script and case study | Done | `docs/demo/LOOM_SCRIPT.md`, `docs/CASE_STUDY.md` |

LLM path: OpenRouter when `OPENROUTER_API_KEY` is set. Since 2026-10-10 free models only: `nvidia/nemotron-3-super-120b-a12b:free`, with Gemma 4 `:free` fallbacks (override with `OPENROUTER_MODEL` / `OPENROUTER_FALLBACK_MODELS`). Free tier: 50 requests/day.

---

## 3. Security finding: leaked database password

- A real Supabase connection string, including its password, was found in git history. It was first committed in `2b7579a` (2026-06-22) and belongs to project `hqofkucrppxzgtajpjxh`.
- No Gemini or OpenRouter keys were found in history.
- **Action taken by Vinayak (2026-10-09):** rotated the Supabase password. The old password in history no longer works.
- History was **not** rewritten. A `git filter-repo` purge plus force-push is optional now that the password is dead. Only do it with explicit approval.
- `.env`, `backend/.env` and `frontend/.env.local` are all git-ignored (verified with `git check-ignore`).

---

## 4. Database check after the password change

- The backend connects to Supabase Postgres (`engine.dialect.name == "postgresql"`). It no longer falls back to SQLite.
- The CRM tables were empty. The backend's own startup seeding (`ensure_demo_user` + `sync_crm_to_sqlite_for_user`) was run once against Supabase. Result for the demo user:
  - 16 accounts, 34 opportunities, 42 contacts, 15 cases, 44 activities
  - The 44 activities were also indexed in ChromaDB, in the local `backend/chroma_db` folder.
- `tests/test_rls.py` (multi-tenant isolation) now runs against Postgres and **passes**.

---

## 5. Test fixes

The starting point was 26 passed and 5 failed. CI (`.github/workflows/ci.yml`) runs the full `pytest` suite, so a push would have failed the build.

| Test | Cause | Fix |
|------|-------|-----|
| `tests/test_rls.py` | The skip check looked at `DATABASE_URL`. A dead Postgres URL falls back to SQLite, so the test ran on SQLite and crashed. | The test now checks the engine actually in use (`engine.dialect.name != "postgresql"`). |
| `tests/test_skills.py::test_intent_classification` | **A real bug.** The "factual bypass" in `intent_classifier.py` matched any question containing "what is" or "who is", so "What is the 7-day playbook for Deloitte?" skipped the AI reasoning and got a plain lookup. | Planning words (`playbook, plan, strategy, recommend, briefing, next steps, should`) now override the factual bypass. Side effect: "who should I contact at X?" now gets a reasoned answer instead of a plain contact list. |
| `tests/test_skills.py::test_reasoning_engine_factual` | Stale test. The data-display (OPERATIONAL) path has returned confidence 0.9 since July 2026. The test expected 0.3. | The test assertion was updated to 0.9. The code was not changed. |
| `tests/test_skills.py::test` | Calls the two tests above. | Fixed by the two fixes above. |
| `test_auth.py` | Local only: starlette 0.27 doesn't work with httpx 0.28. | Not changed. CI installs fresh versions, so it should pass there. Local fix if wanted: `pip install -U fastapi starlette`. |

Current result: **30 passed, 1 failed** (`test_auth`, local versions only).

---

## 6. Docker: why the build fails and the fix plan

### What was found (2026-10-10)
- **Disk:** C: had ~1.5 GB free out of 207 GB. Docker stores everything in one file on C::
  `C:\Users\VINAYAK\AppData\Local\Docker\wsl\disk\docker_data.vhdx`, which was **23.7 GB**.
- **RAM:** the machine has 7.8 GB in total. `C:\Users\VINAYAK\.wslconfig` limits Docker to `memory=4GB, processors=2, swap=2GB`.
  The backend build (PyTorch + sentence-transformers) and the frontend build (Next.js) each use a lot of memory, so building both together runs out.
- Docker Desktop was not running. Only a leftover `docker-buildx` process was visible.
- The Dockerfile is already lean: CPU-only PyTorch, and `.dockerignore` excludes `chroma_db/`, `*.db`, `.env`, logs and `llm_cache.json`.
- E: has 99.1 GB free. The expected total on E: is ~38 GB (24 GB Docker storage + 6–8 GB images and cache + up to 6 GB swap), which leaves ~60 GB.

### Fix steps
1. **Move Docker's storage to E:** (in progress as of 2026-10-10)
   Docker Desktop → Settings → Resources → Advanced → Disk image location → `E:\DockerData` → Apply & restart.
   Let Docker do the move; never move the `.vhdx` by hand. Afterwards C: should show about 25 GB free.
2. **Clean up (optional, safe):**
   ```
   docker image ls
   docker builder prune -f      # deletes only the build cache
   docker image rm <old-project-image>   # only if that demo isn't needed soon
   ```
3. **Put swap on E:** by editing `C:\Users\VINAYAK\.wslconfig`:
   ```
   [wsl2]
   memory=4GB
   processors=2
   swap=6GB
   swapFile=E:\\wsl-swap.vhdx
   ```
   Then run `wsl --shutdown` and restart Docker Desktop. Keep `memory` at 4 GB.
4. **Build one service at a time** (close Chrome and extra VS Code windows first):
   ```
   docker compose build backend
   docker compose build frontend
   docker compose up
   ```
   After that, `docker compose up --build` works normally from the cache.

Docker's storage file grows but does not shrink by itself. Prune old images and build cache now and then.

### Compose facts
- `docker-compose.yml` runs `db` (postgres:15-alpine on host port 5433), `backend` (port 8002) and `frontend` (port 3000).
- Demo login: `demo@apex.example` / `ApexDemo#2026` (fictional data, seeded on first start).
- An OpenRouter key goes in a root `.env` file (`OPENROUTER_API_KEY=...`). It is git-ignored.
- Inside Docker the backend uses its own Postgres container, not Supabase.

---

## 7. Still open

1. Finish the Docker steps above, then check the full flow at http://localhost:3000:
   login → dashboard → at-risk account → AI plan.
2. Commit the work. Nothing is committed yet, and Vinayak's own unfinished files are mixed into the working tree. Commit the demo work separately from them.
3. Optional: purge the old password from git history (needs approval; low priority now that it has been rotated).
4. Optional: fix `test_auth` locally by upgrading fastapi/starlette.
