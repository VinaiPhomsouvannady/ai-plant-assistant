import logging
import os

from backend.models import Source

logger = logging.getLogger(__name__)


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
