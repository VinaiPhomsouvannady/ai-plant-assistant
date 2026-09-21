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

The document store uses PostgreSQL when `DATABASE_URL` is configured and falls back to in-memory storage for lightweight local tests. The vector column is prepared for the embedding-ingestion step.

## PostgreSQL

Start PostgreSQL with pgvector and the API together:

```powershell
docker compose up --build
```

When `DATABASE_URL` is set, the API creates the `documents` and `document_chunks` tables and persists ingested procedures across restarts. New document chunks are embedded with `text-embedding-3-small` and searched with pgvector cosine similarity. If embeddings are unavailable, keyword retrieval remains available.
