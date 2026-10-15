# Session log: 14 October 2026

APEX was deployed publicly on free tiers. This records the setup, the tests behind it, what Vinayak did in each dashboard, and what is still open. Continues from [10_oct.md](10_oct.md). No secrets are recorded here.

---

## 1. Result

| Part | Where | Status |
|---|---|---|
| Frontend | Vercel: https://account-planner-ten.vercel.app | Live. `BACKEND_URL` env var points at Render |
| Backend | Render free, Singapore: https://account-planner-759r.onrender.com | Live, lite mode, ~280 MB of 512 MB |
| Database | Supabase (Sydney session pooler) | Connected (`[SUCCESS] PostgreSQL/Supabase connection verified`) |
| CI | GitHub Actions `ci.yml` | Green after the fix in section 5 |
| Keep-alive | GitHub Actions `keep-alive.yml` | First manual run green |

Demo login: `demo@apex.example` / `ApexDemo#2026` (fictional data).

Checked through the Vercel URL: `/api/health` operational, demo login works, "Which accounts are at risk?" answered correctly in 13 s.

## 2. Constraints and decisions

- **No card** (RuPay), so the same free stack as Document Q&A: Render free (512 MB, 0.1 CPU), Vercel, Supabase.
- **Render hours are shared.** A second Render workspace needs the paid Pro plan, so APEX lives in the same workspace as `docqa-backend` (project `demo-account-planner`). The 750 free hours a month are shared; both keep-alives should ping only 05:00–13:50 UTC (~10:30–19:30 IST), about 600 h together.
- **New service instead of the old one.** The old `apex-account-planner-backend` was in Oregon (region cannot be changed) and ran the full image. It is **suspended**; delete it once the new one has run cleanly for a day. Its `DATABASE_URL` had the old (rotated) Supabase password, which is why the first deploy fell back to SQLite until the URL was updated.

## 3. Lite mode (code)

Full mode is unchanged and still the default (Docker Compose, local development).

| File | Change |
|---|---|
| `backend/embeddings.py` (new) | One loader for all-MiniLM-L6-v2. `EMBEDDINGS_BACKEND` = `sentence-transformers` (default), `fastembed` (ONNX, no PyTorch) or `none`. FastEmbed gave the same router similarity (0.8595) as sentence-transformers on the same query. |
| `backend/intent_classifier.py` | Semantic router uses the shared loader. |
| `backend/vector_store.py` | Without ChromaDB, activity search uses in-memory vectors (rebuilt at startup). ChromaDB is touched only after a model loads, so a missing model no longer deletes `chroma_db/`. Duplicate activities from re-syncs are de-duplicated in search. |
| `backend/requirements-lite.txt` (new) | `requirements.txt` without chromadb and sentence-transformers, plus `fastembed==0.8.0`. |
| `deploy/render/Dockerfile` (new) | Lite image, model baked in, port 10000, `EMBEDDINGS_BACKEND=fastembed`, `DISABLE_CHROMA=true`. |
| `render.yaml` (new) | Blueprint: free plan, Singapore, `/api/health`, free OpenRouter models. |

### Tested locally at `--memory=512m --cpus=0.1`

| | Result |
|---|---|
| Cold start | 173 s (Render: similar) |
| Memory | 275 MB idle, 282 MB peak, never killed |
| Data questions (at-risk, expansion, closing this month, revenue, opportunities) | 1–12 s |
| "hi" / "Tell me about Acme Corp" | 8 s / 28 s, correct |
| AI answers (free Nemotron) | Meridian contact 240 s; 7-day playbook 317 s (one stage took 104 s) |
| Unit tests | 88 passed |

## 4. Render and Vercel settings

**Render service** (Docker): branch `main`, root directory empty, Dockerfile `deploy/render/Dockerfile`, build context `./backend`, health check `/api/health`, auto-deploy on commit, build filters `backend/**` and `deploy/render/**`.
Environment variables: `OPENROUTER_API_KEY`, `DATABASE_URL` (Supabase session pooler, current password), `SECRET_KEY`, `OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free`, `OPENROUTER_FALLBACK_MODELS=google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free`, `LOCAL_OLLAMA=false`.

**Vercel**: root directory `frontend`, `BACKEND_URL=https://account-planner-759r.onrender.com`. Next.js rewrites proxy `/api` and `/auth`, so the browser only talks to the Vercel domain (no CORS or cross-site cookie settings needed). The URL is baked in at build time: change it, then redeploy.

## 5. CI fix

`cd backend && pytest` also collected `backend/test_db.py`, an admin script that reads `DATABASE_URL` at import; CI has none, so collection failed (exit code 2) before any test ran. `ci.yml` now runs `pytest tests`. This also leaves out `backend/test_auth.py` (fails locally on a starlette/httpx version mismatch); move it into `tests/` once fixed. Node 20 deprecation warnings on the `@v3`/`@v4` actions are harmless for now.

## 6. Keep-alive

`.github/workflows/keep-alive.yml`: pings `/api/health` every 10 minutes 05:00–13:50 UTC, and logs in as the demo user once a day (`5 5 * * *`) so the free Supabase project is not paused (`/api/health` does not query the database). Needs repository secret `BACKEND_URL`. GitHub pauses scheduled workflows after 60 days without commits.

## 7. Repository visibility and secrets

- **APEX history:** only the old Supabase password (`APEX$2026...`, rotated on 10 Oct, dead) and placeholder/local passwords. No API keys. Safe to make public.
- **Document Q&A history** (`E:\Research_Paper_Summary`): the initial commit (31 Dec 2025) tracked `.env` with a **real Gemini API key** (starts `AIzaSy`, 39 characters), replaced on 7 Feb 2026. **On 14 Oct the key still worked (HTTP 200).** It is not one of the two `AQ.` keys Vinayak deleted from AI Studio; it is probably in another Google Cloud project or account. Decision: **keep DocQA private** until that key is found and deleted (Cloud Console → each project → APIs & Services → Credentials), or the history is rewritten with `git filter-repo` (needs explicit approval, force-push).
- DocQA demo PDFs name "Rohan Kulkarni", "Meher Textiles" and "Skyline Residency": confirm they are fictional before publishing.
- **Private repos limit GitHub Actions to 2,000 minutes a month** across all private repos, and every run bills at least 1 minute. The 10-minute pings cost about 1,620 minutes a month per repo, so two private repos with pings exceed the limit. While repos are private, move the 10-minute pings to an external pinger such as cron-job.org (free, no card; hours 10–19, Asia/Kolkata) and keep only the daily Supabase login in GitHub Actions.

## 8. Open items

1. **Actions minutes** (section 7): APEX was made **public** on 14 Oct, so its pings are free. DocQA is still private: change its cron to `*/10 5-13 * * *` (~1,620 min/month) or move its pings to cron-job.org.
2. **README commit**: live link, demo login, free-hosting note, corrected figures (12 AI calls per plan, ~4 plans a day, default free Nemotron), and untracking of `backend/test_report.json` and `backend/stream.txt`. Commit and push if not done yet.
3. **DocQA keep-alive**: change its cron to `*/10 5-13 * * *` (or move it to cron-job.org).
4. **Delete** the suspended Oregon service on Render.
5. **Fast mode**: AI plans take 4–5 minutes on free models and can fail through Vercel's proxy, which drops a request after 120 s without data. Cut a plan from ~12 to ~3 AI calls. Top product task.
6. Revoke the old Gemini key, then decide on DocQA visibility.
7. Still from 10 Oct: chip actions, PipelineLogger format bug, telemetry "can't adapt type dict", formatter "Missing schema key: urgency" (seen once on a playbook; answer still returned).
