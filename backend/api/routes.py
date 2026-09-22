import os
import re
import zlib
from io import BytesIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from backend.ai.embeddings import embed_texts
from backend.ai.service import fallback_answer, generate_answer
from backend.api.auth import AUTH_COOKIE_NAME, AuthService, require_authenticated_user
from backend.database.store import DocumentStore
from backend.models import (
    Alarm,
    AlarmCreate,
    Document,
    DocumentCreate,
    LoginRequest,
    SearchRequest,
    Source,
    RecurringIssue,
    TroubleshootRequest,
    TroubleshootResponse,
)
from backend.rag.chunker import chunk_text
from backend.rag.retriever import retrieve, vector_retrieve


def _extract_pdf_strings(raw_bytes: bytes) -> str:
    candidates: list[str] = []
    stream_pattern = re.compile(rb"stream\s*(.*?)\s*endstream", re.DOTALL)
    for stream_match in stream_pattern.finditer(raw_bytes):
        stream_data = stream_match.group(1).strip()
        if not stream_data:
            continue
        try:
            decoded = zlib.decompress(stream_data)
        except zlib.error:
            decoded = stream_data
        if decoded:
            text = decoded.decode("latin-1", errors="ignore")
            candidates.append(text)

    literal_pattern = re.compile(rb"\((?:\\.|[^()\\])*\)")
    for match in literal_pattern.finditer(raw_bytes):
        literal = match.group(0)
        try:
            decoded = literal.decode("latin-1", errors="ignore")
        except Exception:
            continue
        decoded = decoded.replace("\\(", "(").replace("\\)", ")").replace("\\n", " ")
        decoded = decoded.replace("\\(", "(")
        decoded = decoded.replace("\\)", ")")
        decoded = decoded.replace("\\", "")
        if decoded.strip() and decoded.strip() not in {"()", "( )"}:
            candidates.append(decoded.strip("()"))

    combined = "\n".join(part for part in candidates if part).strip()
    return combined


def extract_uploaded_text(filename: str | None, raw_bytes: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(raw_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(page for page in pages if page).strip()
            if text:
                return text
        except Exception as exc:  # pragma: no cover - surfaced to API caller as validation error
            pass

        fallback = _extract_pdf_strings(raw_bytes).strip()
        if fallback:
            return fallback
        raise ValueError("Uploaded PDF could not be read or parsed.")

    try:
        return raw_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1").strip()


def build_router(store: DocumentStore) -> APIRouter:
    router = APIRouter(prefix="/api")
    auth_service = AuthService(store.SessionLocal)
    auth_service.bootstrap_user()

    def require_write_access(user: dict = Depends(require_authenticated_user)) -> dict:
        return user

    @router.post("/auth/login")
    def login(payload: LoginRequest, response: Response) -> dict[str, bool]:
        user = auth_service.authenticate(payload.username, payload.password)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=auth_service.issue_token(user),
            max_age=30 * 60,
            httponly=True,
            secure=os.getenv("AUTH_COOKIE_SECURE", "false").lower() == "true",
            samesite="lax",
        )
        return {"authenticated": True}

    @router.post("/auth/logout")
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie(AUTH_COOKIE_NAME)
        return {"authenticated": False}

    @router.get("/auth/me")
    def current_user(user: dict = Depends(require_authenticated_user)) -> dict[str, str]:
        return {"username": str(user.get("sub", "")), "role": str(user.get("role", "operator"))}

    @router.post("/alarms", response_model=Alarm, status_code=201, dependencies=[Depends(require_write_access)])
    def ingest_alarm(payload: AlarmCreate) -> Alarm:
        return store.add_alarm(payload)

    @router.post("/alarms/bulk", response_model=list[Alarm], status_code=201, dependencies=[Depends(require_write_access)])
    def ingest_alarms(payload: list[AlarmCreate]) -> list[Alarm]:
        return [store.add_alarm(alarm) for alarm in payload]

    @router.get("/alarms/recurring", response_model=list[RecurringIssue])
    def recurring_alarms(limit: int = 20) -> list[RecurringIssue]:
        return store.recurring_issues(limit=max(1, min(limit, 100)))

    @router.get("/documents", response_model=list[Document])
    def list_documents() -> list[Document]:
        return store.all()

    @router.delete("/documents/{document_id}", status_code=204, dependencies=[Depends(require_write_access)])
    def delete_document(document_id: str) -> Response:
        if not store.delete(document_id):
            raise HTTPException(status_code=404, detail="Document not found.")
        return Response(status_code=204)

    @router.post("/documents", response_model=Document, status_code=201, dependencies=[Depends(require_write_access)])
    async def ingest_document(payload: DocumentCreate) -> Document:
        embeddings = await embed_texts(chunk_text(payload.content))
        return store.add(payload, embeddings or None)

    @router.post("/documents/upload", response_model=Document, status_code=201, dependencies=[Depends(require_write_access)])
    async def upload_document(
        file: UploadFile = File(...),
        title: str = Form(...),
        equipment: str = Form(...),
        source: str | None = Form(default=None),
    ) -> Document:
        content = await file.read()
        text = extract_uploaded_text(file.filename, content)
        if not text:
            raise ValueError("Uploaded file is empty or not readable as text.")
        payload = DocumentCreate(title=title, equipment=equipment, content=text, source=source)
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
