from fastapi import APIRouter, Depends

from backend.ai.embeddings import embed_texts
from backend.ai.service import fallback_answer, generate_answer
from backend.api.auth import require_write_token
from backend.database.store import DocumentStore
from backend.models import (
    Alarm,
    AlarmCreate,
    Document,
    DocumentCreate,
    SearchRequest,
    Source,
    RecurringIssue,
    TroubleshootRequest,
    TroubleshootResponse,
)
from backend.rag.chunker import chunk_text
from backend.rag.retriever import retrieve, vector_retrieve


def build_router(store: DocumentStore) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/alarms", response_model=Alarm, status_code=201, dependencies=[Depends(require_write_token)])
    def ingest_alarm(payload: AlarmCreate) -> Alarm:
        return store.add_alarm(payload)

    @router.post("/alarms/bulk", response_model=list[Alarm], status_code=201, dependencies=[Depends(require_write_token)])
    def ingest_alarms(payload: list[AlarmCreate]) -> list[Alarm]:
        return [store.add_alarm(alarm) for alarm in payload]

    @router.get("/alarms/recurring", response_model=list[RecurringIssue])
    def recurring_alarms(limit: int = 20) -> list[RecurringIssue]:
        return store.recurring_issues(limit=max(1, min(limit, 100)))

    @router.get("/documents", response_model=list[Document])
    def list_documents() -> list[Document]:
        return store.all()

    @router.post("/documents", response_model=Document, status_code=201, dependencies=[Depends(require_write_token)])
    async def ingest_document(payload: DocumentCreate) -> Document:
        embeddings = await embed_texts(chunk_text(payload.content))
        return store.add(payload, embeddings or None)

    @router.post("/search", response_model=list[Source])
    async def search_documents(payload: SearchRequest) -> list[Source]:
        embeddings = await embed_texts([payload.query])
        sources = vector_retrieve(store, embeddings[0], payload.equipment, payload.limit) if embeddings else []
        return sources or retrieve(store, payload.query, payload.equipment, payload.limit)

    @router.post("/troubleshoot", response_model=TroubleshootResponse)
    async def troubleshoot(payload: TroubleshootRequest) -> TroubleshootResponse:
        query = f"{payload.equipment} {payload.problem}"
        embeddings = await embed_texts([query])
        sources = vector_retrieve(store, embeddings[0], payload.equipment, payload.limit) if embeddings else []
        sources = sources or retrieve(store, query, payload.equipment, payload.limit)
        alarms = store.recent_alarms(payload.equipment)
        answer, generated_by = await generate_answer(payload.equipment, payload.problem, sources, alarms)
        _, severity, next_checks = fallback_answer(payload.equipment, payload.problem, sources)
        return TroubleshootResponse(
            answer=answer,
            severity=severity,
            next_checks=next_checks,
            sources=sources,
            generated_by=generated_by,
        )

    return router
