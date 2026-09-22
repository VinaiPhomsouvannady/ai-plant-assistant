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
      .button, button { display: inline-block; padding: 10px 14px; border: 0; border-radius: 10px; background: #8fe3a1; color: #071a1c; text-decoration: none; font-weight: 700; cursor: pointer; }
      button.danger { background: #ff9b8f; }
      button:disabled { cursor: wait; opacity: 0.65; }
      .panel { background: rgba(13,31,35,0.95); border: 1px solid rgba(131,179,173,0.2); border-radius: 16px; padding: 18px; margin-bottom: 24px; }
      .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
      label { display: grid; gap: 6px; color: #b3d0cb; font-size: 13px; }
      input { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid rgba(131,179,173,0.35); border-radius: 8px; background: #10282b; color: #e7f5f1; }
      textarea { box-sizing: border-box; width: 100%; min-height: 120px; padding: 10px; border: 1px solid rgba(131,179,173,0.35); border-radius: 8px; background: #10282b; color: #e7f5f1; resize: vertical; }
      .full { grid-column: 1 / -1; }
      .form-actions { display: flex; align-items: center; gap: 12px; margin-top: 14px; }
      .status { color: #b3d0cb; min-height: 20px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 18px; }
      .card { background: rgba(13,31,35,0.95); border: 1px solid rgba(131,179,173,0.2); border-radius: 16px; padding: 18px; }
      .card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
      .card-header h2 { margin-top: 0; }
      .document-card { cursor: pointer; transition: border-color 0.2s, transform 0.2s; }
      .document-card:hover, .document-card:focus-visible { border-color: #8fe3a1; transform: translateY(-2px); outline: none; }
      .meta { color: #b3d0cb; font-size: 12px; margin-bottom: 10px; }
      .snippet { color: #dfece9; line-height: 1.6; max-height: 160px; overflow: hidden; }
      .empty { color: #b3d0cb; }
      dialog { width: min(760px, calc(100% - 32px)); max-height: 80vh; padding: 0; border: 1px solid rgba(143,227,161,0.45); border-radius: 16px; background: #0d1f23; color: #e7f5f1; }
      dialog::backdrop { background: rgba(3, 12, 14, 0.78); }
      .dialog-content { padding: 24px; }
      .dialog-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
      .dialog-header h2 { margin: 0; }
      .dialog-body { white-space: pre-wrap; line-height: 1.7; color: #dfece9; overflow-wrap: anywhere; }
      .close-button { background: transparent; color: #e7f5f1; border: 1px solid rgba(131,179,173,0.35); }
      @media (max-width: 640px) { .form-grid { grid-template-columns: 1fr; } .full { grid-column: auto; } }
    </style>
  </head>
  <body>
    <main>
      <div class="toolbar">
        <h1>PlantOps AI Documents</h1>
        <a class="button" href="/">Back to dashboard</a>
      </div>
      <section class="panel">
        <h2>Add document</h2>
        <form id="document-form">
          <div class="form-grid">
            <label>Title<input name="title" required maxlength="200" placeholder="Pump startup checklist" /></label>
            <label>Equipment<input name="equipment" required maxlength="120" placeholder="Centrifugal pump" /></label>
            <label>Source<input name="source" maxlength="500" placeholder="Operations manual" /></label>
            <label>File (.txt, .md, .pdf)<input name="file" type="file" accept=".txt,.md,.pdf" /></label>
            <label class="full">Content (or choose a file)<textarea name="content" minlength="20" placeholder="Paste the procedure or maintenance guidance here..."></textarea></label>
          </div>
          <div class="form-actions">
            <button type="submit">Add document</button>
            <span id="form-status" class="status" role="status"></span>
          </div>
        </form>
      </section>
      <div id="documents" class="grid"></div>
      <dialog id="document-dialog">
        <div class="dialog-content">
          <div class="dialog-header">
            <div>
              <h2 id="dialog-title"></h2>
              <p id="dialog-meta" class="meta"></p>
            </div>
            <button id="close-dialog" class="close-button" type="button">Close</button>
          </div>
          <div id="dialog-body" class="dialog-body"></div>
        </div>
      </dialog>
    </main>
    <script>
      const container = document.getElementById('documents');
      const status = document.getElementById('form-status');
      const form = document.getElementById('document-form');
      const dialog = document.getElementById('document-dialog');
      const dialogTitle = document.getElementById('dialog-title');
      const dialogMeta = document.getElementById('dialog-meta');
      const dialogBody = document.getElementById('dialog-body');
      const closeDialog = document.getElementById('close-dialog');
      let documentsById = {};

      function escapeHtml(value) {
        return String(value).replace(/[&<>'"]/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
      }

      async function loadDocuments() {
        const response = await fetch('/api/documents', { credentials: 'include' });
        if (!response.ok) throw new Error('Failed to load documents');
        const documents = await response.json();
        documentsById = Object.fromEntries(documents.map((document) => [document.id, document]));
        container.innerHTML = documents.length ? documents.map((doc) => `
          <article class="card document-card" tabindex="0" role="button" data-view="${escapeHtml(doc.id)}" aria-label="View ${escapeHtml(doc.title)}">
            <div class="card-header">
              <h2>${escapeHtml(doc.title)}</h2>
              <button class="danger" type="button" data-delete="${escapeHtml(doc.id)}">Delete</button>
            </div>
            <div class="meta">${escapeHtml(doc.equipment)} · ${escapeHtml(doc.source || 'Manual entry')} · ${doc.chunks} chunks</div>
            <p class="snippet">${escapeHtml(doc.content.slice(0, 500))}${doc.content.length > 500 ? '...' : ''}</p>
          </article>
        `).join('') : '<div class="card empty">No documents have been indexed yet.</div>';
      }

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        status.textContent = 'Adding document...';
        const data = new FormData(form);
        const file = data.get('file');
        if (!file.name && String(data.get('content') || '').trim().length < 20) {
          status.textContent = 'Add at least 20 characters of content or choose a file.';
          return;
        }
        const request = file && file.name
          ? fetch('/api/documents/upload', { method: 'POST', body: data, credentials: 'include' })
          : fetch('/api/documents', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ title: data.get('title'), equipment: data.get('equipment'), source: data.get('source') || null, content: data.get('content') }) });
        const response = await request;
        if (!response.ok) {
          status.textContent = response.status === 401 ? 'Sign in from the dashboard before adding documents.' : 'Unable to add document.';
          return;
        }
        form.reset();
        status.textContent = 'Document added.';
        await loadDocuments();
      });

      function openDocument(documentId) {
        const document = documentsById[documentId];
        if (!document) return;
        dialogTitle.textContent = document.title;
        dialogMeta.textContent = `${document.equipment} · ${document.source || 'Manual entry'} · ${document.chunks} chunks`;
        dialogBody.textContent = document.content;
        dialog.showModal();
      }

      container.addEventListener('click', (event) => {
        const card = event.target.closest('[data-view]');
        if (card && !event.target.closest('[data-delete]')) openDocument(card.dataset.view);
      });

      container.addEventListener('keydown', (event) => {
        const card = event.target.closest('[data-view]');
        if (card && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault();
          openDocument(card.dataset.view);
        }
      });

      closeDialog.addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', (event) => {
        if (event.target === dialog) dialog.close();
      });

      container.addEventListener('click', async (event) => {
        const button = event.target.closest('[data-delete]');
        if (!button || !confirm('Delete this document?')) return;
        button.disabled = true;
        const response = await fetch('/api/documents/' + encodeURIComponent(button.dataset.delete), { method: 'DELETE', credentials: 'include' });
        if (response.status === 401) alert('Sign in from the dashboard before deleting documents.');
        else if (!response.ok) alert('Unable to delete document.');
        await loadDocuments();
      });

      loadDocuments().catch(() => { container.innerHTML = '<div class="card empty">Unable to load records from the document store.</div>'; });
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
