from uuid import uuid4

from backend.models import Document, DocumentCreate
from backend.rag.chunker import chunk_text


class DocumentStore:
    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.chunks: list[dict[str, str]] = []

    def add(self, payload: DocumentCreate) -> Document:
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
        return document

    def all(self) -> list[Document]:
        return list(self.documents.values())
