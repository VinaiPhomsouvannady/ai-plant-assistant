# AI Plant Operations Assistant

A modular FastAPI and React prototype for procedure-grounded equipment troubleshooting.

## Run the backend

```powershell
.\\.venv\\Scripts\\python.exe -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/` for the operator frontend or `http://127.0.0.1:8000/docs` for the API explorer.

Copy `.env.example` to `.env` and add a valid OpenAI API key for LLM responses. Without a key or available credits, the API returns a cited retrieval fallback.

## Test

```powershell
.\\.venv\\Scripts\\python.exe -m pytest
```

The current document store is in memory. PostgreSQL and vector embeddings can be added behind `backend/database` and `backend/rag` without changing the API contracts.
