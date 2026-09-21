import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.api.routes import build_router
from backend.ai.embeddings import embed_texts
from backend.database.seed import SEED_DOCUMENTS
from backend.database.store import DocumentStore
from backend.rag.chunker import chunk_text

load_dotenv(override=True)

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


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(Path(__file__).parent.parent / "frontend" / "index.html")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "documents": len(store.documents),
        "chunks": len(store.chunks),
        "alarms": len(store.alarms),
    }
