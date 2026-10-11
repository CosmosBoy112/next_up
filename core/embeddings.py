"""Local sentence embeddings (all-MiniLM-L6-v2, 384 dims). Model loads once."""

from __future__ import annotations

from functools import lru_cache

from core.config import EMBED_MODEL


@lru_cache(maxsize=1)
def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def embed(text: str) -> list[float]:
    return embed_many([text])[0]


def embed_many(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vecs = get_model().encode(texts, normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vecs]
