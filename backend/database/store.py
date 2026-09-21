from uuid import uuid4

from sqlalchemy import select

from backend.models import Document, DocumentCreate
from backend.rag.chunker import chunk_text
from backend.database.postgres import build_database, initialize_schema
from backend.database.tables import DocumentChunkRow, DocumentRow


class DocumentStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.documents: dict[str, Document] = {}
        self.chunks: list[dict[str, str]] = []
        self.engine = None
        self.SessionLocal = None
        if database_url:
            self.engine, self.SessionLocal = build_database(database_url)
            initialize_schema(self.engine)
            self._load_from_database()

    def add(self, payload: DocumentCreate, embeddings: list[list[float]] | None = None) -> Document:
        document_id = str(uuid4())
        document = Document(
            id=document_id,
            title=payload.title,
            equipment=payload.equipment,
            content=payload.content,
            source=payload.source,
            chunks=len(chunk_text(payload.content)),
        )
        self.documents[document_id] = document
        for index, text in enumerate(chunk_text(payload.content)):
            self.chunks.append({"document_id": document_id, "chunk_id": str(index), "text": text})
        if self.SessionLocal:
            with self.SessionLocal.begin() as session:
                row = DocumentRow(
                    id=document_id,
                    title=payload.title,
                    equipment=payload.equipment,
                    content=payload.content,
                    source=payload.source,
                )
                row.chunks = [
                    DocumentChunkRow(
                        document_id=document_id,
                        chunk_id=str(index),
                        text=text,
                        embedding=embeddings[index] if embeddings else None,
                    )
                    for index, text in enumerate(chunk_text(payload.content))
                ]
                session.add(row)
        return document

    def set_embeddings(self, document_id: str, embeddings: list[list[float]]) -> None:
        if not self.SessionLocal:
            return
        with self.SessionLocal.begin() as session:
            rows = session.scalars(
                select(DocumentChunkRow)
                .where(DocumentChunkRow.document_id == document_id)
                .order_by(DocumentChunkRow.chunk_id)
            ).all()
            for row, embedding in zip(rows, embeddings):
                row.embedding = embedding

    def all(self) -> list[Document]:
        return list(self.documents.values())

    def _load_from_database(self) -> None:
        with self.SessionLocal() as session:
            rows = session.scalars(select(DocumentRow).order_by(DocumentRow.created_at)).all()
            for row in rows:
                document = Document(
                    id=row.id,
                    title=row.title,
                    equipment=row.equipment,
                    content=row.content,
                    source=row.source,
                    chunks=len(row.chunks),
                )
                self.documents[row.id] = document
                self.chunks.extend(
                    {"document_id": row.id, "chunk_id": chunk.chunk_id, "text": chunk.text}
                    for chunk in row.chunks
                )
