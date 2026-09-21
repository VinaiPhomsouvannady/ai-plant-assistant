from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    equipment: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=20)
    source: str | None = None


class Document(DocumentCreate):
    id: str
    chunks: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=2)
    equipment: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class TroubleshootRequest(BaseModel):
    equipment: str = Field(min_length=2, max_length=120)
    problem: str = Field(min_length=5)
    limit: int = Field(default=5, ge=1, le=10)


class Source(BaseModel):
    id: str
    title: str
    equipment: str
    excerpt: str
    score: float


class TroubleshootResponse(BaseModel):
    answer: str
    severity: str
    next_checks: list[str]
    sources: list[Source]
    generated_by: str
