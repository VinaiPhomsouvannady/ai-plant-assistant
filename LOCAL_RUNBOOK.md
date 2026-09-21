# Plant Operations Assistant Local Runbook

## Start the stack

```bash
docker compose up -d --build
```

## Verify the services

```bash
docker compose ps
curl http://127.0.0.1:8000/health
```

Expected:

- `api` is running
- `db` is running and healthy
- health response includes `status: "ok"`

## Validate Postgres and pgvector

```bash
docker compose exec db psql -U plantops -d plantops -c "\dt"
docker compose exec db psql -U plantops -d plantops -c "SELECT extname FROM pg_extension ORDER BY extname;"
```

Expected tables:

- `documents`
- `document_chunks`
- `equipment_alarms`
- `alembic_version`

Expected extension:

- `vector`

## Test the API endpoints

```bash
# Search
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"equipment":"Centrifugal pump","query":"low discharge pressure","limit":3}'

# Troubleshoot
curl -X POST http://127.0.0.1:8000/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"equipment":"Centrifugal pump","problem":"low discharge pressure","limit":3}'

# Alarm ingestion
curl -X POST http://127.0.0.1:8000/api/alarms \
  -H "Content-Type: application/json" \
  -d '{"equipment":"Centrifugal pump","alarm_code":"P-204-01","message":"Discharge pressure low","occurred_at":"2026-09-21T10:00:00Z","value":1.2,"unit":"bar"}'
```

## Migration workflow

The app container runs Alembic automatically during startup:

```bash
docker compose logs api --tail=50
```

Look for:

```text
Running upgrade  -> 0001_initial_schema, create plant operations schema
```

## Local environment notes

- The Docker container should use the Compose `DATABASE_URL`.
- Local `.env` values must not override container runtime values.
- The app falls back to in-memory mode if Postgres is unreachable, which is useful for local development but not for production.

## Run the tests

```bash
.\.venv\Scripts\python.exe -m pytest -q
```
