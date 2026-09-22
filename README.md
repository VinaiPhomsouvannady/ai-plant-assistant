# PlantOps AI

PlantOps AI is an AI-assisted troubleshooting workspace for industrial operations teams. It combines plant documents, equipment alarms, semantic retrieval, and optional LLM recommendations so operators can investigate equipment issues with source-backed guidance.

## Features

- Authenticated operator dashboard
- Database-backed users with scrypt password hashes
- Signed 30-minute sessions in `HttpOnly` cookies
- Equipment troubleshooting with cited source documents
- Document creation, text/Markdown/PDF upload, full-document viewing, and deletion
- Alarm ingestion, alarm history, filtering, and recurring-issue summaries
- Units overview derived from equipment in documents and alarms
- PostgreSQL persistence with pgvector embeddings
- Safe fallback recommendations when OpenAI is not configured

## Stack

- FastAPI and Uvicorn
- React, TypeScript, and Vite
- PostgreSQL 16 with pgvector
- SQLAlchemy and Alembic
- Optional OpenAI embeddings and chat completion
- Docker Compose

## Start With Docker

Docker is the recommended local workflow because it starts PostgreSQL, applies migrations, builds the frontend, and serves the built UI from FastAPI.

### 1. Configure the environment

```powershell
Copy-Item .env.example .env
```

For local development, `.env` can use:

```env
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
CORS_ORIGINS=http://localhost:5173
AUTH_USERNAME=plantops
AUTH_PASSWORD=change-this-password
AUTH_SECRET_KEY=replace-with-a-long-random-secret
AUTH_COOKIE_SECURE=false
```

Use a unique password and secret outside a local demo. Keep `.env` private.

### 2. Start the application

```powershell
docker compose up -d --build
```

Open:

- Dashboard: http://localhost:8000/
- Units: http://localhost:8000/units
- Alarms: http://localhost:8000/alarms
- Documents: http://localhost:8000/documents
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The first configured user is created as an admin during application startup. Sign in with the `AUTH_USERNAME` and `AUTH_PASSWORD` values from `.env`.

### 3. Check the services

```powershell
docker compose ps
Invoke-RestMethod -Uri 'http://localhost:8000/health' | ConvertTo-Json
```

Stop the stack with:

```powershell
docker compose down
```

Add `--volumes` only when you intentionally want to delete the PostgreSQL data volume.

## Frontend Development

The Vite project uses `frontend/vite.html` as its entry file. There is intentionally no `frontend/index.html`.

Run the frontend build:

```powershell
npm install
npm run build
```

The build writes `frontend/dist/vite.html` and its assets. FastAPI serves that built shell when running on port `8000`.

For the complete working application, use Docker. Running Vite alone on port `5173` is useful for frontend-only work, but this project does not currently configure a Vite proxy for the backend API.

## Local Python Run

Use this when PostgreSQL is already available and `DATABASE_URL` points to it.

```powershell
.\.venv\Scripts\Activate.ps1
npm install
npm run build
python -m alembic upgrade head
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

If the browser shows an error about `frontend\index.html`, an old process or stale source is running. This project serves `frontend\dist\vite.html`; stop the old server, build the frontend, and start `app:app` from the repository root.

## Application Workflow

1. Sign in at the dashboard.
2. Ask a troubleshooting question for a unit and problem.
3. Review the recommendation, severity, next checks, and cited sources.
4. Open **Documents** to add manual content or upload a `.txt`, `.md`, or `.pdf` file.
5. Click a document to read its full content, or delete it when appropriate.
6. Open **Alarms** to filter alarm history.
7. Open **Units** to review equipment represented by the document and alarm data.

## API Overview

Public/read endpoints:

```text
GET  /health
GET  /api/auth/me
GET  /api/documents
GET  /api/alarms
GET  /api/alarms/recurring
POST /api/search
POST /api/troubleshoot
```

Authentication endpoints:

```text
POST /api/auth/login
POST /api/auth/logout
```

Authenticated write endpoints:

```text
POST   /api/documents
POST   /api/documents/upload
DELETE /api/documents/{document_id}
POST   /api/alarms
POST   /api/alarms/bulk
```

The browser uses the secure session cookie automatically. API clients must preserve cookies between login and subsequent requests.

## Database and Migrations

Migrations run automatically when the Docker API container starts. To run them manually:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Current tables include:

- `users`
- `documents`
- `document_chunks`
- `equipment_alarms`
- `alembic_version`

The database also enables the `vector` extension for document embeddings.

## Testing

Backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend type checking and build:

```powershell
npm run typecheck
npm run build
```

## Security Notes

- Passwords are stored as scrypt hashes, not plaintext.
- Sessions expire after 30 minutes and use `HttpOnly` cookies.
- Set `AUTH_SECRET_KEY` to a long, random, deployment-managed value.
- Set `AUTH_COOKIE_SECURE=true` when serving over HTTPS.
- Replace the bootstrap password after the first deployment.
- Keep `.env` out of source control.
- Configure `CORS_ORIGINS` to the real frontend origin in deployment.
- Put the application behind HTTPS, rate limiting, and a managed PostgreSQL instance before external use.
- Review document access and role-specific authorization before using plant procedures in a shared environment.

## Troubleshooting

### The dashboard returns a missing `frontend\index.html` error

This usually means an old local server is running or the Vite build has not been created. The current entry is `frontend/vite.html`, not `frontend/index.html`.

Run:

```powershell
npm run build
docker compose up -d --build
```

Then open http://localhost:8000/.

### Login is rejected

Check the values in `.env`, restart the API, and use the same username and password:

```powershell
docker compose up -d --build
```

If the database already contains the user, changing `AUTH_USERNAME` or `AUTH_PASSWORD` does not overwrite that user. Update the user through an administrative workflow before changing bootstrap settings.

### The app starts but has no AI-generated response

Set `OPENAI_API_KEY` in `.env` and rebuild/restart. Without a key, the application uses its deterministic fallback recommendation.
