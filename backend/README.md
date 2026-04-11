# Account Planner Backend

This is the FastAPI backend for the Account Planner agent.

## Setup with Poetry

If you are using Poetry, you can initialize the project and add dependencies as follows:

```bash
# Initialize poetry (if not already done)
poetry init -n

# Add dependencies from requirements.txt
cat requirements.txt | xargs -L 1 poetry add
```

## Running the Server

```bash
uvicorn main:app --reload --port 8001
```
*(Note: Port 8001 is used to avoid conflict with the LLM server on 8000)*
