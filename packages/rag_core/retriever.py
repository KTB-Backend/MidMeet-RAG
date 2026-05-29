"""Atmosphere vector retrieval from Chroma."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
from typing import Any, Mapping

from rag_core.embedder import QUERY_MODE, EmbeddingAdapter
from rag_core.indexer import (
    CHROMA_COLLECTION_ENV,
    CHROMA_PATH_ENV,
    DEFAULT_CHROMA_COLLECTION,
    DEFAULT_CHROMA_PATH,
    validate_collection_model_guard,
)


logger = logging.getLogger(__name__)

RETRIEVAL_TOP_K_ENV = "RETRIEVAL_TOP_K"
DEFAULT_RETRIEVAL_TOP_K = 10


@dataclass(frozen=True)
class AtmosphereSearchResult:
    """A Chroma match with only atmosphere retrieval scores attached."""

    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    attributes: str
    source: str
    atmosphere_text: str
    atmosphere_score: float
    distance: float


class ChromaRetrievalError(RuntimeError):
    """Raised when Chroma retrieval cannot proceed."""


def search_atmosphere(
    query_text: str,
    embedder: EmbeddingAdapter,
    *,
    top_k: int | None = None,
    chroma_path: str | Path | None = None,
    collection_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[AtmosphereSearchResult]:
    """Embed an atmosphere query in query mode and search Chroma."""

    env = os.environ if environ is None else environ
    resolved_top_k = top_k if top_k is not None else _top_k_from_env(env)
    _validate_top_k(resolved_top_k)

    resolved_path = str(chroma_path or env.get(CHROMA_PATH_ENV, DEFAULT_CHROMA_PATH))
    resolved_collection = collection_name or env.get(
        CHROMA_COLLECTION_ENV, DEFAULT_CHROMA_COLLECTION
    )

    chromadb = _import_chromadb()
    client = chromadb.PersistentClient(path=resolved_path)
    collection = _get_collection(
        client=client,
        name=resolved_collection,
        chromadb_module=chromadb,
    )
    if collection.count() == 0:
        return []

    query_embedding = _embed_query(query_text, embedder)
    validate_collection_model_guard(
        getattr(collection, "metadata", None),
        embedding_model=_embedding_model_name(embedder),
        embedding_dimension=len(query_embedding),
    )

    response = collection.query(
        query_embeddings=[query_embedding],
        n_results=resolved_top_k,
        include=["documents", "metadatas", "distances"],
    )
    return chroma_query_response_to_results(response)


def distance_to_atmosphere_score(distance: float) -> float:
    """Convert Chroma cosine distance to similarity without clamping."""

    # Cosine similarity can theoretically fall outside 0..1; S5 decides any
    # normalization or clamp policy. S4 exposes the raw 1 - distance value.
    return 1.0 - float(distance)


def chroma_query_response_to_results(
    response: Mapping[str, Any]
) -> list[AtmosphereSearchResult]:
    """Map Chroma's nested query response dict into retrieval results."""

    ids = _first_query_row(response.get("ids"))
    documents = _first_query_row(response.get("documents"))
    metadatas = _first_query_row(response.get("metadatas"))
    distances = _first_query_row(response.get("distances"))

    results: list[AtmosphereSearchResult] = []
    for index, raw_id in enumerate(ids):
        metadata = _metadata_at(metadatas, index)
        distance = float(distances[index])
        results.append(
            AtmosphereSearchResult(
                place_id=_metadata_str(metadata, "place_id", fallback=str(raw_id)),
                name=_metadata_str(metadata, "name"),
                address=_metadata_str(metadata, "address"),
                latitude=_metadata_float(metadata, "latitude"),
                longitude=_metadata_float(metadata, "longitude"),
                attributes=_metadata_str(metadata, "attributes"),
                source=_metadata_str(metadata, "source"),
                atmosphere_text=str(documents[index]),
                atmosphere_score=distance_to_atmosphere_score(distance),
                distance=distance,
            )
        )

    return results


def _top_k_from_env(env: Mapping[str, str]) -> int:
    raw_value = env.get(RETRIEVAL_TOP_K_ENV)
    if raw_value is None or raw_value == "":
        return DEFAULT_RETRIEVAL_TOP_K

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"{RETRIEVAL_TOP_K_ENV} must be an integer; got {raw_value!r}."
        ) from exc


def _validate_top_k(top_k: int) -> None:
    if top_k <= 0:
        raise ValueError(f"top_k must be a positive integer; got {top_k}.")


def _embed_query(query_text: str, embedder: EmbeddingAdapter) -> list[float]:
    embeddings = embedder.embed([query_text], mode=QUERY_MODE)
    if len(embeddings) != 1:
        raise ChromaRetrievalError(
            f"Query embedding count mismatch: expected 1, got {len(embeddings)}."
        )
    if not embeddings[0]:
        raise ChromaRetrievalError("Query embedding vector must not be empty.")
    return [float(value) for value in embeddings[0]]


def _embedding_model_name(embedder: EmbeddingAdapter) -> str:
    model_name = getattr(embedder, "model_name", None)
    if not model_name:
        raise ChromaRetrievalError(
            "Embedding adapter must expose a non-empty model_name for Chroma "
            "retrieval guards."
        )
    return str(model_name)


def _import_chromadb() -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise ChromaRetrievalError(
            "chromadb is required for retrieval. Install with "
            'pip install -e ".[vectorstore]" or ".[dev,vectorstore]".'
        ) from exc

    return chromadb


def _get_collection(*, client: Any, name: str, chromadb_module: Any) -> Any:
    try:
        return client.get_collection(name=name, embedding_function=None)
    except Exception as exc:
        not_found_error = getattr(
            getattr(chromadb_module, "errors", None), "NotFoundError", None
        )
        if not_found_error is not None and isinstance(exc, not_found_error):
            raise ChromaRetrievalError(
                f"Chroma collection {name!r} was not found. Run seed indexing first."
            ) from exc
        if _looks_like_missing_collection_error(exc):
            raise ChromaRetrievalError(
                f"Chroma collection {name!r} was not found. Run seed indexing first."
            ) from exc
        raise


def _looks_like_missing_collection_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "does not exist" in message or "not found" in message


def _first_query_row(value: object) -> list[Any]:
    if not value:
        return []
    if not isinstance(value, list):
        raise ChromaRetrievalError("Chroma query response must contain nested lists.")
    first = value[0]
    if first is None:
        return []
    if not isinstance(first, list):
        raise ChromaRetrievalError("Chroma query response must contain nested lists.")
    return first


def _metadata_at(metadatas: list[Any], index: int) -> Mapping[str, object]:
    if index >= len(metadatas) or metadatas[index] is None:
        return {}
    metadata = metadatas[index]
    if not isinstance(metadata, Mapping):
        raise ChromaRetrievalError("Chroma metadata entries must be mappings.")
    return metadata


def _metadata_str(
    metadata: Mapping[str, object], key: str, *, fallback: str = ""
) -> str:
    value = metadata.get(key)
    if value is None:
        return fallback
    return str(value)


def _metadata_float(metadata: Mapping[str, object], key: str) -> float:
    value = metadata.get(key)
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ChromaRetrievalError(
            f"Chroma metadata field {key!r} must be numeric; got {value!r}."
        ) from exc
