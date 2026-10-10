# Session log: 10 October 2026

Record of the work done on 2026-10-10 to make APEX demo-ready: what was broken, how it was diagnosed, what was changed, how it was verified, and what is still open. Continues from [deployment_fixes.md](deployment_fixes.md). No secrets are recorded here.

---

## 1. Summary

| Area | Before | After |
|---|---|---|
| Docker | Storage on a full C: drive; build unverified | Storage on E:, full stack runs; backend uses its own Postgres |
| Account resolution | "Who should I contact at Meridian?" answered about Northwind | Whole-word matching; Meridian resolves to Meridian |
| Invented content | "hi" produced a P1 report about Acme Corp, Globex, Stark Industries | Greeting is a plain reply; cards only contain data from the CRM |
| Urgency | Every answer P1, including a health-88 account | P1/P2/P3 calculated from health and open cases |
| Clarifications | A pending clarification hijacked the next question | Resumes only when the reply names a real account |
| Conversations | All new chats shared `default_session` history | Each conversation gets its own id |
| At-risk list | Largest companies first, including "low risk" ones | Ranked by risk level and health; only High/Critical |
| Risk review card | $18.28M "at risk" (every deal), fixed "45 days stalled" | $4.83M portfolio / $1.54M Northwind, real stall days |
| Data questions | Full 30 s AI report for "what is the revenue of X" | Direct answer from CRM data, ~1 s, no AI request |
| LLM | Paid model; account ran out of credits (402) | Free models only, with fallbacks; limits shown in the UI |
| Credentials | Supabase password hardcoded in 5 scripts | Read from environment; password rotated by Vinayak |
| Tests | 30 passing | 88 passing (only the known local `test_auth` failure remains) |

---

## 2. Docker move from C: to E:

C: had about 1.5 GB free and Docker's disk image (`docker_data.vhdx`, ~22 GB) lived there. It was moved through Docker Desktop (Settings → Resources → Advanced → Disk image location) to `E:\DockerData\DockerDesktopWSL\disk\docker_data.vhdx`. Afterwards C: had 23.7 GB free and E: 77 GB.

Not done yet: the WSL swap file is still `swap=2GB` on C: (`C:\Users\VINAYAK\.wslconfig`). Moving it to E: is optional now that builds succeed.

Images were rebuilt one service at a time:

```powershell
docker compose down            # keeps the database volume (no -v)
docker image rm accountplanner-backend
docker compose build --no-cache backend
docker compose up -d
```

### Postgres driver

Inside Docker the backend logged `No module named 'psycopg'` and fell back to SQLite. The container installs SQLAlchemy 2.1.4, which maps a plain `postgresql://` URL to the newer `psycopg` (v3) driver, while `requirements.txt` installs `psycopg2-binary`. `database.py` now rewrites the URL to `postgresql+psycopg2://`. The container log shows `PostgreSQL/Supabase connection verified successfully`. (The following `SQLite database is empty` line is a misleading message; seeding goes to Postgres.)

---

## 3. Diagnosis of the wrong answers

Fourteen UI screenshots and the backend logs were reviewed. Four root causes explained every wrong answer.

### A. The response formatter invented content

`main.py` sent every answer through `format_response_for_user`, a second LLM call that rewrites the answer into the P1/P2/P3 card. For "hii" the pipeline correctly produced a short greeting in 2 s, then the formatter had to fill the card's risks and actions sections with nothing to go on, and invented Acme Corp, Globex and Stark Industries. It also chose the urgency, which is why everything was P1.

### B. Clarification checkpoint hijacked the next question

"Tell me about Acme Corp" correctly asked which account was meant and saved a checkpoint. The next message, "Which accounts have expansion potential?", was treated as the answer: the account was set to the whole question text and classification was skipped. The checkpoint was also serialised with `json.dumps(default=str)`, so the saved intent came back as a string and the original question was lost.

### C. Conversations shared one history

The frontend sent `activeSessionId || 'default_session'`, and the sidebar fell back to `default_session` on first load, after deleting a chat and after logout. Unsaved conversations therefore shared one history full of Northwind answers, which leaked into later questions.

### D. Account names matched on substrings

The classifier treated any capitalised word as a possible account. In "Who should I contact at Meridian?" it skipped "Who" but kept "I". Account lookup then used a substring match, and most account names contain the letter "i", so the first row, Northwind Logistics, won. "Tell me about Acme Corp" picked "Tell". When a name didn't match, the orchestrator also quietly swapped in the active account.

---

## 4. Fixes

### D: Account resolution

- New `backend/account_resolver.py`: one rule used everywhere. A query matches an account by full name, Account_ID, or brand word (first word of the name, e.g. "Meridian"), always whole-word. Filler words ("I", "Tell", "Which"…) are never account names.
- `intent_classifier.py`: uses the resolver; carries an account over from history only from the user's own messages, never from APEX's answers.
- `agent_orchestrator.py`: an unknown company goes to clarification; the active account is substituted only when the typed name is a contact.
- `clarification_builder.py`: "I couldn't find an account called "Acme Corp" in your CRM data. Which account did you mean?"

### A: Formatter

- Skipped for greetings, clarifications and factual answers (the frontend already had a plain style for clarifications).
- Prompt has grounding rules: only names and numbers from the input, empty arrays when there is nothing, no placeholders, no internal pipeline terms.
- Post-check drops opportunities and risks not present in the source, placeholders such as "[Insert Decision Maker Name Here]", and terms such as "Crucible" and "test_to_disambiguate".
- Urgency is calculated: P1 if health < 35 or an open Critical case; P2 if health < 60 or an open High case; otherwise P3.
- The greeting reply was wrapped as `{"response": "…"}` (the LLM helper always requests JSON); it is now unwrapped.

### B: Clarification checkpoint

The checkpoint stores the original question and the unknown name. The next message resumes it only if it is short (≤ 6 words) and names a real account, e.g. "Northwind Logistics" or a suggestion button; the question is re-run with the name substituted ("Tell me about Northwind Logistics"). Any other message discards the checkpoint.

### C: Sessions

`SidebarContext.tsx` creates a unique id (`session_<time>_<random>`) instead of `default_session` everywhere, and ignores a stored `default_session`. The chat page resets the active account when the conversation changes.

### At-risk list and risk review

- The at-risk table sorted by a priority score that added revenue × 0.05 (about $105M for Brightwater) to risk flags worth ~100,000 each, so the biggest company always came first. Its flag-based score also rated Sablewood (health 14) and Halvorsen (23) as low risk. The table now uses the worse of the flag label and a health band (< 30 Critical, < 45 High, < 60 Medium), sorts by that and then by health, and lists only High/Critical accounts for "at risk" questions.
- `RiskReviewHandler` counted closed deals, treated every account as single-threaded in portfolio scope, used fixed values (45 days stalled, 10 days case age), read a `priority` field that doesn't exist (cases have `severity`), and printed "Competitor replacement threat". It now uses open deals only, at-risk accounts only for portfolio scope, real days past the close date and case age, case severity, named competitors, and counts each deal once.
- Opportunities passed to the pipeline now include probability, competitor and account id. Pipeline totals exclude closed deals (Northwind $1.54M, not $1.72M).

### Direct answers (new `backend/direct_answers.py`)

Answered from the CRM tables with no LLM call, before the intent classifier runs:

- Portfolio: expansion candidates (health 65+ with open pipeline), deals closing this week/month/quarter.
- One account: annual revenue, health score, contacts, opportunities.

Questions with planning or causal words ("why", "should", "plan", "strategy", "risk"…) still go to the reasoning pipeline. Table IDs are shown without the per-user storage prefix (`OPP004`, not `1_OPP004`), and typed IDs in either form resolve.

### LLM provider

- The OpenRouter account ran out of credits during testing: every call returned `402 This request requires more credits`. The code retried each 402 three times at every pipeline step, so a playbook took 111 s before failing. `api_retry.py` now fails fast on 401/402/403 and on per-day limits.
- Switched to free models only (Vinayak's decision: no paid usage). Benchmarked with a JSON-output prompt:

| Model | Result |
|---|---|
| `nvidia/nemotron-3-super-120b-a12b:free` | Valid JSON; 4 s small prompt, 15–17 s per real pipeline call. **Chosen as primary.** |
| `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free` | Rate-limited upstream when tested. **Configured as fallbacks.** |
| `nvidia/nemotron-3.5-lightning:free` | Returned its thinking process instead of JSON (49 s) |
| `dots-studio/dots-3-note-preview:free`, `apodex/apodex-1.1-mini:free` | Invalid JSON |

- `reasoning_engine.py` sends OpenRouter a `models` list so it falls back automatically, and strips `<think>` blocks.
- The key reports `is_free_tier: True`: 50 requests/day, 20/minute. A full AI plan measured 12 requests and about 2.5 minutes. Capacity calculations are in [demo_guide.md](../demo/demo_guide.md#3-free-ai-model-limits-and-what-they-mean).
- The chat UI shows an animated notice after 6 s of waiting, and a one-line note under the input, so users know why plans are slow and that data questions are unaffected.

### Security

A Supabase connection string with a password was hardcoded in `add_role_column.py`, `create_eval_tables.py`, `rebuild_db.py`, `seed_golden_dataset.py` and `test_db.py` (tracked and pushed since July). They now read `ADMIN_DATABASE_URL` / `DATABASE_URL` from the environment. Vinayak confirmed the password has been rotated, so the copy in git history is dead.

---

## 5. Verification

- **Unit tests:** new `test_routing.py` (24), `test_response_formatter.py` (14), `test_direct_answers.py` (14), `test_api_retry.py` (4), plus updated `test_quick_actions.py`. Full suite: 88 passed; `test_auth` fails locally only (starlette 0.27 with httpx 0.28).
- **Live checks:** a script logs in as the demo user and sends questions to `/api/chat` on the running container, each in a fresh session, then reads `docker compose logs backend`. Two bugs were caught only this way (local `import re` / `import json` lines further down a function shadowing the module import, which broke every request with "Processing Error"); the unit tests did not exercise the chat endpoint.
- **Live results (2026-10-10):**

| Question | Result |
|---|---|
| Who should I contact at Meridian? (Northwind sent as active account) | Meridian Health Network, Elena Park, P2 |
| Tell me about Acme Corp | "I couldn't find an account called "Acme Corp"…", plain message with account buttons |
| Acme → reply "Northwind Logistics" | Resumed as "Tell me about Northwind Logistics" |
| Acme → "Which accounts have expansion potential?" | Treated as a new question |
| Why are we losing Halvorsen Retail? | Halvorsen, P1 |
| Which accounts are at risk? | Sablewood 14, Halvorsen 23, Northwind 28, Meridian 41, Bluefin 36, Crestline 38; $4.83M at risk |
| Which accounts have expansion potential? | 10 accounts, $7.07M, Brightwater first; 0 AI requests, 1.0 s |
| What's closing this month? | 6 deals, $3.77M ($2.74M weighted); 0.6 s |
| What is the revenue of Brightwater Capital? | $2.1B; 0.7 s |
| Show opportunities for Northwind Logistics | 2 open worth $1.54M, plus 1 closed |
| Give me a 7-day playbook for Northwind Logistics | P1 card on the free model; 12 requests, ~140 s |
| hi | Plain greeting, no card |

---

## 6. Commits

The first commit of the day, `6d2300a`, has the pasted instructions block as its message (its content is correct: removal of tracked DB/log files and the docs move). It was already pushed, so it was left as is rather than force-pushing `main`.

---

## 7. Still open

1. **AI plan speed on free models:** ~12 requests and ~2.5 min per plan, about 4–6 plans per day. Proposed "fast mode": skip the pre-reasoning layers on free models to cut a plan to ~3 requests (~45–60 s, ~15 plans/day).
2. **Quick-action buttons** such as "Draft email" return a full report instead of the email or agenda.
3. **Logging:** `PipelineLogger` summary fails with `Invalid format specifier ',:<12'`; the "LLM Calls" counter shows 0; the "Gemini API (model: llama3.2:latest)" label is wrong.
4. **Telemetry:** saving trace payloads fails with `can't adapt type 'dict'` (dict passed where JSON text is expected).
5. **UI pass:** all checks so far went through the API; one manual click-through in the browser is still needed.
6. **Optional:** move the WSL swap file to E:; upgrade fastapi/starlette locally so `test_auth` passes.
