import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import build_router
from backend.ai.embeddings import embed_texts
from backend.database.seed import SEED_DOCUMENTS
from backend.database.store import DocumentStore
from backend.rag.chunker import chunk_text

# Keep runtime environment variables from the host/container as the source of truth.
# This prevents local .env files from overriding Docker Compose values such as DATABASE_URL.
load_dotenv(override=False)

store = DocumentStore(os.getenv("DATABASE_URL"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not store.documents:
        for seed in SEED_DOCUMENTS:
            embeddings = await embed_texts(chunk_text(seed.content))
            store.add(seed, embeddings or None)
    yield


app = FastAPI(title="Plant Operations Assistant", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(build_router(store))

frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    built_index = frontend_dist / "vite.html"
    if built_index.exists():
        return FileResponse(built_index)
    raise FileNotFoundError("Vite build not found. Run the frontend build before starting the app.")


@app.get("/documents", include_in_schema=False)
def documents_page() -> HTMLResponse:
    return HTMLResponse(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>PlantOps AI Documents</title>
    <style>
      body { font-family: Arial, sans-serif; margin: 0; background: #071a1c; color: #e7f5f1; }
      main { max-width: 1100px; margin: 0 auto; padding: 32px 20px 60px; }
      h1 { margin-bottom: 12px; }
      .toolbar { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 24px; }
      a.button { display: inline-block; padding: 10px 14px; border-radius: 10px; background: #8fe3a1; color: #071a1c; text-decoration: none; font-weight: 700; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
      .card { background: rgba(13,31,35,0.95); border: 1px solid rgba(131,179,173,0.2); border-radius: 16px; padding: 18px; }
      .meta { color: #b3d0cb; font-size: 12px; margin-bottom: 10px; }
      .snippet { color: #dfece9; line-height: 1.6; max-height: 160px; overflow: hidden; }
      .empty { color: #b3d0cb; }
    </style>
  </head>
  <body>
    <main>
      <div class="toolbar">
        <h1>PlantOps AI Documents</h1>
        <a class="button" href="/">Back to dashboard</a>
      </div>
      <div id="documents" class="grid"></div>
    </main>
    <script>
      fetch('/api/documents')
        .then((response) => {
          if (!response.ok) {
            throw new Error('Failed to fetch documents');
          }
          return response.json();
        })
        .then((documents) => {
          const container = document.getElementById('documents');
          if (!documents.length) {
            container.innerHTML = '<div class="card empty">No documents have been indexed yet.</div>';
            return;
          }
          container.innerHTML = documents.map((doc) => `
            <article class="card">
              <div class="meta">${doc.equipment} · ${doc.source || 'Manual entry'} · ${doc.chunks} chunks</div>
              <h2>${doc.title}</h2>
              <p class="snippet">${doc.content.slice(0, 500)}${doc.content.length > 500 ? '...' : ''}</p>
            </article>
          `).join('');
        })
        .catch((error) => {
          document.getElementById('documents').innerHTML = '<div class="card empty">Unable to load records from the document store.</div>';
          console.error(error);
        });
    </script>
  </body>
</html>
        """
    )


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "documents": len(store.documents),
        "chunks": len(store.chunks),
        "alarms": len(store.alarms),
    }
