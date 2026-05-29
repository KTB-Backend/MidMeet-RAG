"""Chroma indexing for validated MidMeet seed records."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
from typing import Any, Mapping

from rag_core.embedder import DOCUMENT_MODE, EmbeddingAdapter
from rag_core.loader import SeedRecord


logger = logging.getLogger(__name__)

CHROMA_PATH_ENV = "CHROMA_PATH"
CHROMA_COLLECTION_ENV = "CHROMA_COLLECTION"
CHROMA_DISTANCE_SPACE_ENV = "CHROMA_DISTANCE_SPACE"
CHROMA_HNSW_EF_CONSTRUCTION_ENV = "CHROMA_HNSW_EF_CONSTRUCTION"
CHROMA_HNSW_MAX_NEIGHBORS_ENV = "CHROMA_HNSW_MAX_NEIGHBORS"
CHROMA_HNSW_EF_SEARCH_ENV = "CHROMA_HNSW_EF_SEARCH"

DEFAULT_CHROMA_PATH = "data/chroma/"
DEFAULT_CHROMA_COLLECTION = "venues"
DEFAULT_CHROMA_DISTANCE_SPACE = "cosine"

EMBEDDING_MODEL_METADATA_KEY = "embedding_model"
EMBEDDING_DIMENSION_METADATA_KEY = "embedding_dimension"
DISTANCE_SPACE_METADATA_KEY = "distance_space"

_HNSW_ENV_TO_CONFIG_KEY = {
    CHROMA_HNSW_EF_CONSTRUCTION_ENV: "ef_construction",
    CHROMA_HNSW_MAX_NEIGHBORS_ENV: "max_neighbors",
    CHROMA_HNSW_EF_SEARCH_ENV: "ef_search",
}

ChromaMetadataValue = str | int | float | bool


@dataclass(frozen=True)
class ChromaSeedPayload:
    """A seed record normalized into Chroma upsert inputs."""

    id: str
    document: str
    metadata: dict[str, ChromaMetadataValue]


@dataclass(frozen=True)
class ChromaIndexResult:
    """Summary returned after a Chroma indexing run."""

    collection_name: str
    chroma_path: str
    indexed_count: int
    collection_count: int
    used_legacy_hnsw_config: bool = False


class ChromaIndexError(RuntimeError):
    """Raised when Chroma indexing cannot proceed safely."""


class CollectionModelGuardError(ChromaIndexError):
    """Raised when an existing Chroma collection was built with another model."""


def index_seed_records(
    records: list[SeedRecord],
    embedder: EmbeddingAdapter,
    *,
    chroma_path: str | Path | None = None,
    collection_name: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ChromaIndexResult:
    """Embed seed records in document mode and upsert them into Chroma."""

    if not records:
        raise ValueError("No seed records to index.")

    env = os.environ if environ is None else environ
    resolved_path = str(chroma_path or env.get(CHROMA_PATH_ENV, DEFAULT_CHROMA_PATH))
    resolved_collection = collection_name or env.get(
        CHROMA_COLLECTION_ENV, DEFAULT_CHROMA_COLLECTION
    )

    payloads = [seed_record_to_chroma_payload(record) for record in records]
    documents = [payload.document for payload in payloads]
    embeddings = embedder.embed(documents, mode=DOCUMENT_MODE)
    embedding_dimension = _validate_embeddings(embeddings, len(records))
    embedding_model = _embedding_model_name(embedder)

    hnsw_config = build_hnsw_config(environ=env)
    distance_space = hnsw_config["hnsw"]["space"]
    collection_metadata = build_collection_metadata(
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
        distance_space=distance_space,
    )

    chromadb = _import_chromadb()
    client = chromadb.PersistentClient(path=resolved_path)
    collection, used_legacy_hnsw_config = _get_or_create_collection(
        client=client,
        name=resolved_collection,
        metadata=collection_metadata,
        hnsw_config=hnsw_config,
    )
    _ensure_collection_model_guard(
        collection=collection,
        expected_metadata=collection_metadata,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
    )

    collection.upsert(
        ids=[payload.id for payload in payloads],
        embeddings=embeddings,
        documents=documents,
        metadatas=[payload.metadata for payload in payloads],
    )

    return ChromaIndexResult(
        collection_name=resolved_collection,
        chroma_path=resolved_path,
        indexed_count=len(payloads),
        collection_count=collection.count(),
        used_legacy_hnsw_config=used_legacy_hnsw_config,
    )


def seed_record_to_chroma_payload(record: SeedRecord) -> ChromaSeedPayload:
    """Convert a validated seed record into Chroma id/document/metadata fields."""

    return ChromaSeedPayload(
        id=record.place_id,
        document=record.atmosphere_text,
        metadata={
            "place_id": record.place_id,
            "name": record.name,
            "address": record.address,
            "latitude": float(record.latitude),
            "longitude": float(record.longitude),
            "attributes": _json_metadata(record.attributes),
            "source": _json_metadata(record.source),
        },
    )


def build_hnsw_config(
    *, environ: Mapping[str, str] | None = None
) -> dict[str, dict[str, str | int]]:
    """Build Chroma HNSW configuration from environment variables."""

    env = os.environ if environ is None else environ
    distance_space = env.get(
        CHROMA_DISTANCE_SPACE_ENV, DEFAULT_CHROMA_DISTANCE_SPACE
    ).strip()
    if distance_space != DEFAULT_CHROMA_DISTANCE_SPACE:
        raise ValueError(
            "CHROMA_DISTANCE_SPACE must be 'cosine' to match atmosphere scoring; "
            f"got {distance_space!r}."
        )

    hnsw: dict[str, str | int] = {"space": distance_space}
    for env_name, config_key in _HNSW_ENV_TO_CONFIG_KEY.items():
        raw_value = env.get(env_name)
        if raw_value is None or raw_value == "":
            continue
        hnsw[config_key] = _positive_int_env(env_name, raw_value)

    return {"hnsw": hnsw}


def build_collection_metadata(
    *,
    embedding_model: str,
    embedding_dimension: int,
    distance_space: str = DEFAULT_CHROMA_DISTANCE_SPACE,
) -> dict[str, ChromaMetadataValue]:
    """Build collection metadata used to guard safe reindexing."""

    return {
        EMBEDDING_MODEL_METADATA_KEY: embedding_model,
        EMBEDDING_DIMENSION_METADATA_KEY: int(embedding_dimension),
        DISTANCE_SPACE_METADATA_KEY: distance_space,
    }


def validate_collection_model_guard(
    collection_metadata: Mapping[str, object] | None,
    *,
    embedding_model: str,
    embedding_dimension: int,
) -> None:
    """Reject collections created with a different embedding model or dimension."""

    if not collection_metadata:
        raise CollectionModelGuardError(
            "Chroma collection is missing embedding guard metadata. "
            "Use an empty collection, a different CHROMA_COLLECTION, or recreate the index."
        )

    stored_model = collection_metadata.get(EMBEDDING_MODEL_METADATA_KEY)
    stored_dimension = _metadata_int(
        collection_metadata.get(EMBEDDING_DIMENSION_METADATA_KEY)
    )
    if stored_model is None or stored_dimension is None:
        raise CollectionModelGuardError(
            "Chroma collection is missing embedding_model or embedding_dimension "
            "metadata. Use an empty collection, a different CHROMA_COLLECTION, "
            "or recreate the index."
        )

    if str(stored_model) != embedding_model or stored_dimension != embedding_dimension:
        raise CollectionModelGuardError(
            "Chroma collection embedding guard mismatch: "
            f"stored embedding_model={stored_model!r}, "
            f"embedding_dimension={stored_dimension}; "
            f"current embedding_model={embedding_model!r}, "
            f"embedding_dimension={embedding_dimension}. "
            "Use a different CHROMA_COLLECTION/CHROMA_PATH or recreate the index."
        )


def _json_metadata(value: object) -> str:
    return json.dumps(asdict(value), ensure_ascii=False, sort_keys=True)


def _positive_int_env(env_name: str, raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{env_name} must be an integer; got {raw_value!r}.") from exc

    if parsed <= 0:
        raise ValueError(f"{env_name} must be a positive integer; got {parsed}.")
    return parsed


def _metadata_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validate_embeddings(
    embeddings: list[list[float]], expected_count: int
) -> int:
    if len(embeddings) != expected_count:
        raise ChromaIndexError(
            f"Embedding count mismatch: expected {expected_count}, got {len(embeddings)}."
        )
    if not embeddings:
        raise ChromaIndexError("No embeddings were returned.")

    first_dimension = len(embeddings[0])
    if first_dimension <= 0:
        raise ChromaIndexError("Embedding vectors must not be empty.")

    for index, vector in enumerate(embeddings):
        if len(vector) != first_dimension:
            raise ChromaIndexError(
                "Embedding dimension mismatch within batch: "
                f"vector 0 has {first_dimension}, vector {index} has {len(vector)}."
            )
        if not all(isinstance(value, (float, int)) for value in vector):
            raise ChromaIndexError(f"Embedding vector {index} contains a non-number.")

    return first_dimension


def _embedding_model_name(embedder: EmbeddingAdapter) -> str:
    model_name = getattr(embedder, "model_name", None)
    if not model_name:
        raise ChromaIndexError(
            "Embedding adapter must expose a non-empty model_name for Chroma "
            "reindexing guards."
        )
    return str(model_name)


def _import_chromadb() -> Any:
    try:
        import chromadb
    except ImportError as exc:
        raise ChromaIndexError(
            "chromadb is required for indexing. Install with "
            'pip install -e ".[vectorstore]" or ".[dev,vectorstore]".'
        ) from exc

    return chromadb


def _get_or_create_collection(
    *,
    client: Any,
    name: str,
    metadata: dict[str, ChromaMetadataValue],
    hnsw_config: dict[str, dict[str, str | int]],
) -> tuple[Any, bool]:
    try:
        return (
            client.get_or_create_collection(
                name=name,
                metadata=metadata,
                configuration=hnsw_config,
                embedding_function=None,
            ),
            False,
        )
    except (TypeError, ValueError) as exc:
        if not _looks_like_configuration_error(exc):
            raise

    logger.warning(
        "Installed chromadb does not support collection configuration; "
        "falling back to legacy hnsw:space metadata."
    )
    legacy_metadata = dict(metadata)
    legacy_metadata["hnsw:space"] = hnsw_config["hnsw"]["space"]
    return (
        client.get_or_create_collection(
            name=name,
            metadata=legacy_metadata,
            embedding_function=None,
        ),
        True,
    )


def _looks_like_configuration_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "configuration",
            "hnsw",
            "ef_construction",
            "ef_search",
            "max_neighbors",
        )
    )


def _ensure_collection_model_guard(
    *,
    collection: Any,
    expected_metadata: dict[str, ChromaMetadataValue],
    embedding_model: str,
    embedding_dimension: int,
) -> None:
    metadata = getattr(collection, "metadata", None) or {}
    if _has_model_guard(metadata):
        validate_collection_model_guard(
            metadata,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
        )
        return

    if collection.count() != 0:
        raise CollectionModelGuardError(
            "Existing Chroma collection has rows but no embedding guard metadata. "
            "Use a different CHROMA_COLLECTION/CHROMA_PATH or recreate the index."
        )

    merged_metadata = dict(metadata)
    merged_metadata.update(expected_metadata)
    collection.modify(metadata=merged_metadata)
    validate_collection_model_guard(
        merged_metadata,
        embedding_model=embedding_model,
        embedding_dimension=embedding_dimension,
    )


def _has_model_guard(metadata: Mapping[str, object]) -> bool:
    return (
        EMBEDDING_MODEL_METADATA_KEY in metadata
        and EMBEDDING_DIMENSION_METADATA_KEY in metadata
    )
