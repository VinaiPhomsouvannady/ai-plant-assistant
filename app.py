from __future__ import annotations

import os
import re
import logging
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv


load_dotenv()


logger = logging.getLogger(__name__)


STOP_WORDS = {
	"a", "an", "and", "are", "for", "from", "in", "is", "of", "on", "or",
	"the", "to", "with", "when", "what", "why", "how", "this", "that",
}


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


documents: dict[str, Document] = {}
chunks: list[dict[str, str]] = []


SEED_DOCUMENTS = [
	DocumentCreate(
		title="Centrifugal Pump P-204: Low Discharge Pressure",
		equipment="Centrifugal pump",
		source="Pump maintenance procedure 04-22",
		content=(
			"If discharge pressure is low, verify suction valve position and check the suction "
			"strainer for blockage. Confirm the pump is rotating in the correct direction and "
			"inspect the mechanical seal for leakage. Do not operate below minimum flow. If the "
			"strainer differential pressure is high, isolate and clean it under the lockout/tagout "
			"procedure before restarting."
		),
	),
	DocumentCreate(
		title="Heat Exchanger E-101: Outlet Temperature Drift",
		equipment="Heat exchanger",
		source="Utilities operating standard 11-08",
		content=(
			"For an outlet temperature drift, compare inlet temperatures and flow rates against "
			"the operating log. Check the control valve position and verify the temperature sensor "
			"calibration. Fouling on the process side can reduce heat transfer. Escalate if outlet "
			"temperature exceeds the trip limit or if pressure drop rises unexpectedly."
		),
	),
	DocumentCreate(
		title="Compressor K-301: High Vibration Response",
		equipment="Compressor",
		source="Rotating equipment alarm response 07-14",
		content=(
			"A high vibration alarm requires confirmation from the local indicator and control-room "
			"trend. Check bearing temperature, lube-oil pressure, and recent process changes. Keep "
			"clear of the coupling and rotating equipment. If vibration continues to rise, reduce "
			"load and notify the shift supervisor for a controlled shutdown assessment."
		),
	),
]


def tokenize(text: str) -> set[str]:
	return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP_WORDS}


def chunk_text(text: str, words_per_chunk: int = 55) -> list[str]:
	words = text.split()
	return [" ".join(words[index:index + words_per_chunk]) for index in range(0, len(words), words_per_chunk)]


def add_document(payload: DocumentCreate) -> Document:
	document_id = str(uuid4())
	document = Document(
		id=document_id,
		title=payload.title,
		equipment=payload.equipment,
		content=payload.content,
		source=payload.source,
		chunks=len(chunk_text(payload.content)),
	)
	documents[document_id] = document
	for index, text in enumerate(chunk_text(payload.content)):
		chunks.append({"document_id": document_id, "chunk_id": str(index), "text": text})
	return document


def retrieve(query: str, equipment: str | None, limit: int) -> list[Source]:
	query_terms = tokenize(query)
	ranked: list[tuple[float, Source]] = []
	for chunk in chunks:
		document = documents[chunk["document_id"]]
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


def fallback_answer(equipment: str, problem: str, sources: list[Source]) -> tuple[str, str, list[str]]:
	text = problem.lower()
	if any(term in text for term in ("vibration", "trip", "leak", "smoke", "overheat")):
		severity = "high"
	elif any(term in text for term in ("pressure", "temperature", "flow", "alarm")):
		severity = "medium"
	else:
		severity = "low"
	checks = [
		f"Confirm the {equipment} tag, current operating state, and alarm timestamp.",
		"Compare local readings with the control-room trend and the last known good value.",
		"Follow the cited procedure and apply lockout/tagout before hands-on inspection.",
	]
	if sources:
		answer = f"Start with the checks in {sources[0].title}. The reported condition is most consistent with a procedure-driven inspection of the affected equipment."
	else:
		answer = "No matching procedure was found. Keep the equipment in a known safe state and escalate to the shift supervisor for an approved troubleshooting procedure."
	return answer, severity, checks


async def generate_answer(equipment: str, problem: str, sources: list[Source]) -> tuple[str, str]:
	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key or not sources:
		return fallback_answer(equipment, problem, sources)[0], "retrieval-fallback"
	try:
		from openai import AsyncOpenAI

		context = "\n\n".join(f"[{source.title}] {source.excerpt}" for source in sources)
		client = AsyncOpenAI(api_key=api_key)
		response = await client.responses.create(
			model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
			instructions="You are a cautious plant operations assistant. Use only the provided context. Never invent a procedure. Mention source titles in the answer and recommend escalation for unsafe conditions.",
			input=f"Equipment: {equipment}\nProblem: {problem}\nContext:\n{context}",
		)
		return response.output_text, "openai"
	except Exception as error:
		logger.warning("OpenAI generation failed: %s: %s", type(error).__name__, error)
		return fallback_answer(equipment, problem, sources)[0], "retrieval-fallback"


@asynccontextmanager
async def lifespan(_: FastAPI):
	if not documents:
		for seed in SEED_DOCUMENTS:
			add_document(seed)
	yield


app = FastAPI(title="Plant Operations Assistant", version="0.1.0", lifespan=lifespan)
app.add_middleware(
	CORSMiddleware,
	allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
	return FileResponse("frontend/index.html")


@app.get("/health")
def health() -> dict[str, Any]:
	return {"status": "ok", "documents": len(documents), "chunks": len(chunks)}


@app.get("/api/documents", response_model=list[Document])
def list_documents() -> list[Document]:
	return list(documents.values())


@app.post("/api/documents", response_model=Document, status_code=201)
def ingest_document(payload: DocumentCreate) -> Document:
	return add_document(payload)


@app.post("/api/search", response_model=list[Source])
def search_documents(payload: SearchRequest) -> list[Source]:
	return retrieve(payload.query, payload.equipment, payload.limit)


@app.post("/api/troubleshoot", response_model=TroubleshootResponse)
async def troubleshoot(payload: TroubleshootRequest) -> TroubleshootResponse:
	sources = retrieve(f"{payload.equipment} {payload.problem}", payload.equipment, payload.limit)
	answer, generated_by = await generate_answer(payload.equipment, payload.problem, sources)
	_, severity, next_checks = fallback_answer(payload.equipment, payload.problem, sources)
	return TroubleshootResponse(
		answer=answer,
		severity=severity,
		next_checks=next_checks,
		sources=sources,
		generated_by=generated_by,
	)
