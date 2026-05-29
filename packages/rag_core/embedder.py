"""Embedding adapters for MidMeet RAG."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
import os
from typing import Any


logger = logging.getLogger(__name__)

EMBEDDING_MODEL_ENV = "EMBEDDING_MODEL_NAME"
DEFAULT_EMBEDDING_MODEL_NAME = "dragonkue/snowflake-arctic-embed-l-v2.0-ko"

DOCUMENT_MODE = "document"
QUERY_MODE = "query"
QUERY_PREFIX = "query: "

EMBEDDING_DIMENSIONS = 1024
# Model card facts for visibility only; keep the SentenceTransformer config as-is.
MAX_SEQUENCE_LENGTH = 8192
MODEL_TRAINING_TOKEN_WINDOW = 1300
DEFAULT_BATCH_SIZE = 32


class EmbeddingAdapter(ABC):
    """Abstract embedding model boundary for indexing and query flows."""

    @abstractmethod
    def embed(self, texts: list[str], mode: str = DOCUMENT_MODE) -> list[list[float]]:
        """Convert texts into embedding vectors."""


@dataclass
class SnowflakeArcticEmbedAdapter(EmbeddingAdapter):
    """SentenceTransformers adapter for snowflake-arctic Korean embeddings.

    Model card facts: 1024-dim output, CLS pooling, max sequence length 8192
    with training up to 1300 tokens. MidMeet Korean seed texts are expected to
    be roughly 50-400 characters, so they should not be truncated.
    """

    model_name: str | None = None
    batch_size: int = DEFAULT_BATCH_SIZE
    _model: Any | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.model_name is None:
            self.model_name = os.environ.get(
                EMBEDDING_MODEL_ENV, DEFAULT_EMBEDDING_MODEL_NAME
            )

    def embed(self, texts: list[str], mode: str = DOCUMENT_MODE) -> list[list[float]]:
        """Embed texts with query/document prefix handling."""

        if not texts:
            return []

        prefixed_texts = _apply_query_prefix(texts, mode)
        model = self._load_model()
        embeddings = model.encode(
            prefixed_texts,
            batch_size=self.batch_size,
            convert_to_numpy=True,
        )

        return _to_float_vectors(embeddings)

    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)

        return self._model


def _apply_query_prefix(texts: list[str], mode: str) -> list[str]:
    """Apply model-specific query prefixing without loading the model."""

    if mode == DOCUMENT_MODE:
        return list(texts)
    if mode == QUERY_MODE:
        return [f"{QUERY_PREFIX}{text}" for text in texts]

    raise ValueError(
        f"Unknown embedding mode: {mode}. Expected '{DOCUMENT_MODE}' or '{QUERY_MODE}'."
    )


def _to_float_vectors(embeddings: Any) -> list[list[float]]:
    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    return [[float(value) for value in vector] for vector in embeddings]
