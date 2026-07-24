# 🛠️ APEX Account Planner Ecosystem Setup Guide

This guide details how to install dependencies and run both the FastAPI Python Backend and Next.js Frontend Dashboard services locally.

---

## 🐍 1. Backend Setup & Run (FastAPI)

The backend is built with FastAPI.

### Prerequisites
- Python 3.10+
- Pip or Poetry

### Installation
Choose either standard pip or Poetry:

#### Option A: Pip Installation
```bash
cd backend
pip install -r requirements.txt
```

#### Option B: Poetry Setup
```bash
cd backend
poetry init -n
cat requirements.txt | xargs -L 1 poetry add
```

### Running the Services
The backend is split into two microservices:
1. **Auth Service (Port 8001)**:
   ```bash
   uvicorn auth_main:app --reload --port 8001
   ```
2. **Main Backend API (Port 8002)**:
   ```bash
   uvicorn main:app --reload --port 8002
   ```

---

## 🎨 2. Frontend Setup & Run (Next.js)

The frontend is a React/Next.js client.

### Prerequisites
- Node.js 18+
- npm, yarn, or pnpm

### Installation
```bash
cd frontend
npm install
```

### Running the Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

---

## 🚀 3. Quick Start Launcher
To start both backend services and the frontend together in separate terminal windows, run the launcher script from the project root:
- **macOS / Linux**:
  ```bash
  ./run_project.sh
  ```
- **Windows**:
  ```cmd
  run_project.bat
  ```
