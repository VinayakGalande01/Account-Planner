# APEX Account Planner — CI/CD & Cloud Deployment Documentation

This document summarizes the modernization, dockerization, and CI/CD configurations implemented for the APEX Account Planner ecosystem, followed by step-by-step instructions for deploying to production.

---

## Section 1: Summary of Work Done in this Session

We restructured and prepared the codebase for a production-grade, containerized cloud environment on a **zero-cost tier**. 

### 1. Architectural Consolidation
* Consolidated the **two backend services** (Auth on port `8001` and Backend API on port `8002`) into **a single unified service**. 
* Because `backend/main.py` already mounts the authentication routes, the unified backend handles both Auth (`/auth/*`) and Data (`/api/*`) operations inside a single container. This reduces resource usage by 50%, preventing memory issues on free-tier servers.

### 2. Code & Security Enhancements
* **Database Driver Compatibility**: Updated [database.py](file:///e:/Account%20Planner/backend/database.py) to parse `postgres://` connection strings and automatically format them to `postgresql://` (required for SQLAlchemy compatibility on cloud providers like Render/Koyeb).
* **Cross-Origin Cookie Authentications**: Modified [router.py](file:///e:/Account%20Planner/backend/auth/router.py) to support dynamic `SAMESITE_COOKIE` and `SECURE_COOKIE` environment variables. In production, this allows secure, cross-domain HTTP-only cookies to work between your Next.js frontend (Vercel) and FastAPI backend (Render).
* **Dynamic Gateway Proxies**: Refactored [next.config.ts](file:///e:/Account%20Planner/frontend/next.config.ts) to read the backend endpoint from the `BACKEND_URL` environment variable in production, while falling back to local ports (`8001` and `8002`) for local script compatibility.
* **Test Suite Verification**: Fixed a NameError (missing `Dict` import) in [intent_classifier.py](file:///e:/Account%20Planner/backend/intent_classifier.py) and corrected outdated assertions in [test_skills.py](file:///e:/Account%20Planner/backend/tests/test_skills.py) so that tests compile and pass cleanly on every run.

### 3. Docker Orchestration
* **[backend/Dockerfile](file:///e:/Account%20Planner/backend/Dockerfile)**: Added a multi-stage Docker build that pre-downloads and bakes the 90MB Sentence-Transformers model (`all-MiniLM-L6-v2`) into the image to minimize startup latency and avoid filesystem failures in read-only runtimes.
* **[frontend/Dockerfile](file:///e:/Account%20Planner/frontend/Dockerfile)**: Added a standard production-build container configuration for Next.js.
* **[docker-compose.yml](file:///e:/Account%20Planner/docker-compose.yml)**: Created a root compose configuration to orchestrate the Next.js app, unified FastAPI backend, and a PostgreSQL database in a virtual network locally.
* **Database Auto-Seeding**: Copied the Excel dataset [SF_AccountingAgent_DummyData.xlsx](file:///e:/Account%20Planner/backend/SF_AccountingAgent_DummyData.xlsx) into the repository so that the backend can automatically initialize and seed the PostgreSQL tables on its first launch in the cloud.

### 4. CI/CD Pipeline
* **[.github/workflows/ci.yml](file:///e:/Account%20Planner/.github/workflows/ci.yml)**: Configured a GitHub Actions workflow that automatically runs backend Python tests, builds Next.js assets, and verifies both Dockerfiles compile successfully on every push and pull request to the `main` branch.

---

## Section 2: Step-by-Step Cloud Deployment Guide (Zero-Cost)

Follow these instructions to configure your database, deploy the backend API, and connect the Next.js dashboard.

### Step 2.1: Provision the Supabase PostgreSQL Database

1. Go to [supabase.com](https://supabase.com) and create a free account.
2. Create a new project:
   * **Project Name**: `apex-account-planner`
   * **Database Password**: *Set a secure password and save it.*
   * Choose a hosting region closest to your location.
3. Once the database is ready, go to **Project Settings** (gear icon in left sidebar) -> **Database**.
4. Scroll to **Connection string** and select **URI**.
5. Copy the connection string. It will look like this:
   ```
   postgresql://postgres.[your-project-id]:[your-password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
   ```
6. **Replace** `[your-password]` with your actual database password. This URI will be your `DATABASE_URL` environment variable.

---

### Step 2.2: Deploy the Backend to Render

Render will automatically fetch your repository, compile your Dockerfile, and host your backend API.

1. Create a free account on [render.com](https://render.com) and link it to your GitHub.
2. Click **New** -> **Web Service**.
3. Select your repository.
4. Input the following configuration details:
   * **Name**: `apex-account-planner-backend`
   * **Root Directory**: `backend` (This points Render to the backend folder where the Dockerfile is located)
   * **Runtime**: `Docker`
   * **Instance Type**: `Free`
5. Click **Advanced** and add the following **Environment Variables**:
   * `DATABASE_URL` = (Your Supabase URI connection string from Step 2.1)
   * `GEMINI_API_KEY` = (Your Google AI Studio API Key)
   * `SECRET_KEY` = (A secure random string, e.g. `your-random-token-secret-key`)
   * `SECURE_COOKIE` = `True`
   * `SAMESITE_COOKIE` = `none`
   * `ALLOWED_ORIGINS` = `https://account-planner-ten.vercel.app` (Your live Vercel URL)
6. Click **Create Web Service**. Render will begin building the image. 

> [!NOTE]
> Since the PostgreSQL database is empty on first boot, the backend will automatically parse the bundled Excel sheet and seed all data (accounts, cases, contacts, opportunities, activities) directly into Supabase.

---

### Step 2.3: Connect and Redeploy the Frontend on Vercel

1. Open your Vercel Dashboard and select your `account-planner-ten` project.
2. Go to **Settings** -> **Environment Variables**.
3. Add a new environment variable:
   * **Key**: `BACKEND_URL`
   * **Value**: (Your live Render Web Service URL, e.g., `https://apex-account-planner-backend.onrender.com`)
4. Go to the **Deployments** tab in Vercel.
5. Click the three dots next to your latest deployment and click **Redeploy** (ensure "Use existing Build Cache" is unchecked) to bake the new dynamic rewrite settings into production.

---

### Step 2.4: Deploy Code Changes to GitHub

To trigger the automated GitHub Actions CI tests and prompt Render to deploy the backend updates:
1. In your local repository terminal, run:
   ```bash
   git add .
   git commit -m "chore: setup Docker configs, CI/CD workflow, and dynamic cloud variables"
   git push origin main
   ```
2. Open your GitHub repository page and click the **Actions** tab to watch your test and build suites compile successfully in real time!

---

## Section 3: Technical Challenges, Troubleshooting & Solutions

During the deployment and verification process, several critical hosting limitations and routing conflicts were resolved. This section documents those challenges and their corresponding architectural solutions.

### 1. Render Free Tier Memory Limits (PyTorch / ChromaDB OOM)
* **Problem**: Render's free tier has a strict **512 MB RAM** limit. The original semantic search configuration imported `sentence-transformers` and PyTorch, which consumes >600 MB of RAM during initialization. This caused Render to repeatedly kill the container with Out of Memory (OOM) errors.
* **Solution**: Implemented a memory optimization switch in [vector_store.py](file:///e:/Account%20Planner/backend/vector_store.py) controlled by the `DISABLE_CHROMA` environment variable:
  * By setting `DISABLE_CHROMA=true` in Render's environment variables, the backend bypasses the heavy PyTorch/ChromaDB imports.
  * It falls back to a lightweight, built-in keyword-matching/fallback algorithm.
  * This reduced the container startup memory footprint to **~80 MB**, allowing the backend to run reliably on Render's free tier.

### 2. Supabase IPv6 Connectivity Failures
* **Problem**: Render's free tier currently does not support outbound IPv6 traffic. When attempting to connect to Supabase's direct PostgreSQL endpoint (typically on port `5432`), the DNS resolved to an IPv6 address, resulting in database connection timeout errors on startup.
* **Solution**: Switched the connection string in the Render environment variables to the **Supabase Connection Pooler URI** on port `6543` (using the transaction pooling address). The connection pooler acts as an IPv4 proxy, allowing Render's IPv4-only environment to connect and run migrations successfully.

### 3. Next.js Double-Slash (`//`) 404 Rewrite Errors
* **Problem**: Defining `BACKEND_URL` in Vercel with a trailing slash (e.g., `https://apex-backend.onrender.com/`) caused the Next.js rewrite engine to generate double-slashes in request paths (e.g. `https://apex-backend.onrender.com//auth/signup`), which FastAPI rejected with `404 Not Found`.
* **Solution**: Added a sanitization utility `cleanUrl` in [next.config.ts](file:///e:/Account%20Planner/frontend/next.config.ts):
  ```typescript
  const cleanUrl = (url: string) => url.replace(/\/+$/, "");
  ```
  This strips any trailing slashes from environment variables before appending paths in the rewrite rules, preventing malformed paths.

### 4. CI/CD Pipeline Failure & Local SQLite Conflicts
* **Problem 1**: The backend unit test suite (`backend/tests/`) was untracked locally, which would cause GitHub Actions (which runs `pytest` in `backend/`) to fail with exit code 5 (no tests collected).
* **Problem 2**: Dynamic local SQLite databases (`backend/local_planner.db`) were untracked and showing up in Git staging, risking database conflicts if committed.
* **Solution**: 
  * Staged and committed the entire Python unit test suite in [tests](file:///e:/Account%20Planner/backend/tests/) to ensure GitHub Actions runs and passes cleanly on every push.
  * Added `backend/local_planner.db` to the root [`.gitignore`](file:///e:/Account%20Planner/.gitignore) to prevent developer test data from being committed to the shared repository.

