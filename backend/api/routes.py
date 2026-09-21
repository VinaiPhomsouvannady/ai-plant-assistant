from fastapi import APIRouter

from backend.ai.service import fallback_answer, generate_answer
from backend.database.store import DocumentStore
from backend.models import (
    Document,
    DocumentCreate,
    SearchRequest,
    Source,
    TroubleshootRequest,
    TroubleshootResponse,
)
from backend.rag.retriever import retrieve


def build_router(store: DocumentStore) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/documents", response_model=list[Document])
    def list_documents() -> list[Document]:
        return store.all()

    @router.post("/documents", response_model=Document, status_code=201)
    def ingest_document(payload: DocumentCreate) -> Document:
        return store.add(payload)

    @router.post("/search", response_model=list[Source])
    def search_documents(payload: SearchRequest) -> list[Source]:
        return retrieve(store, payload.query, payload.equipment, payload.limit)

    @router.post("/troubleshoot", response_model=TroubleshootResponse)
    async def troubleshoot(payload: TroubleshootRequest) -> TroubleshootResponse:
        sources = retrieve(store, f"{payload.equipment} {payload.problem}", payload.equipment, payload.limit)
        answer, generated_by = await generate_answer(payload.equipment, payload.problem, sources)
        _, severity, next_checks = fallback_answer(payload.equipment, payload.problem, sources)
        return TroubleshootResponse(
            answer=answer,
            severity=severity,
            next_checks=next_checks,
            sources=sources,
            generated_by=generated_by,
        )

    return router
