import os
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.embeddings.create(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as error:
        logger.warning("Embedding generation failed: %s: %s", type(error).__name__, error)
        return []
