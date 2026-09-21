import re

from sqlalchemy import select

from backend.database.store import DocumentStore
from backend.models import Source
from backend.database.tables import DocumentChunkRow, DocumentRow

STOP_WORDS = {
    "a", "an", "and", "are", "for", "from", "in", "is", "of", "on", "or",
    "the", "to", "with", "when", "what", "why", "how", "this", "that",
}


def tokenize(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP_WORDS}


def retrieve(store: DocumentStore, query: str, equipment: str | None, limit: int) -> list[Source]:
    query_terms = tokenize(query)
    ranked: list[tuple[float, Source]] = []

    for chunk in store.chunks:
        document = store.documents[chunk["document_id"]]
        if equipment and equipment.lower() not in document.equipment.lower():
            continue
        content_terms = tokenize(f"{document.title} {document.equipment} {chunk['text']}")
        overlap = len(query_terms & content_terms)
        equipment_boost = 0.25 if equipment and equipment.lower() in document.equipment.lower() else 0
        score = min(0.99, (overlap / max(len(query_terms), 1)) + equipment_boost)
        if score > 0:
            ranked.append((score, Source(
                id=document.id,
                title=document.title,
                equipment=document.equipment,
                excerpt=chunk["text"],
                score=round(score, 3),
            )))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [source for _, source in ranked[:limit]]


def vector_retrieve(
    store: DocumentStore,
    query_embedding: list[float],
    equipment: str | None,
    limit: int,
) -> list[Source]:
    if not store.SessionLocal:
        return []
    with store.SessionLocal() as session:
        distance = DocumentChunkRow.embedding.cosine_distance(query_embedding).label("distance")
        statement = (
            select(DocumentChunkRow, DocumentRow, distance)
            .join(DocumentRow, DocumentRow.id == DocumentChunkRow.document_id)
            .where(DocumentChunkRow.embedding.is_not(None))
        )
        if equipment:
            statement = statement.where(DocumentRow.equipment.ilike(f"%{equipment}%"))
        rows = session.execute(
            statement.order_by(DocumentChunkRow.embedding.cosine_distance(query_embedding)).limit(limit)
        ).all()
    return [
        Source(
            id=document.id,
            title=document.title,
            equipment=document.equipment,
            excerpt=chunk.text,
            score=round(max(0.0, 1.0 - float(distance)), 3),
        )
        for chunk, document, distance in rows
    ]
