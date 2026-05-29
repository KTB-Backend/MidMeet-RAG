import json

import pytest

from rag_core.indexer import (
    CHROMA_HNSW_EF_CONSTRUCTION_ENV,
    CHROMA_HNSW_EF_SEARCH_ENV,
    CHROMA_HNSW_MAX_NEIGHBORS_ENV,
    CollectionModelGuardError,
    build_collection_metadata,
    build_hnsw_config,
    seed_record_to_chroma_payload,
    validate_collection_model_guard,
)
from rag_core.loader import SeedAttributes, SeedRecord, SeedSource


def test_seed_record_to_chroma_payload_serializes_metadata_as_chroma_scalars() -> None:
    record = _seed_record()

    payload = seed_record_to_chroma_payload(record)

    assert payload.id == "idx_001"
    assert payload.document == record.atmosphere_text
    assert payload.metadata["name"] == "인덱스 테스트 카페"
    assert payload.metadata["address"] == "서울 마포구 테스트로 1"
    assert payload.metadata["latitude"] == 37.5573
    assert payload.metadata["longitude"] == 126.9245
    assert all(
        isinstance(value, (str, int, float, bool))
        for value in payload.metadata.values()
    )

    attributes = json.loads(str(payload.metadata["attributes"]))
    source = json.loads(str(payload.metadata["source"]))
    assert attributes == {
        "category": "카페",
        "noise_level": "조용함",
        "operating_hours": "09:00-22:00",
        "outdoor": False,
        "parking": False,
        "price_range": "1인 7000-12000원",
        "reservation": None,
        "seating_type": ["개인석"],
        "wifi": True,
    }
    assert source == {
        "author": "pytest",
        "notes": "deterministic unit test",
        "reference": "test fixture",
        "type": "fixture",
        "verified_at": "2026-05-28",
    }


def test_build_hnsw_config_includes_cosine_space_and_omits_unset_options() -> None:
    assert build_hnsw_config(environ={}) == {"hnsw": {"space": "cosine"}}


def test_build_hnsw_config_includes_set_options() -> None:
    config = build_hnsw_config(
        environ={
            CHROMA_HNSW_EF_CONSTRUCTION_ENV: "200",
            CHROMA_HNSW_MAX_NEIGHBORS_ENV: "32",
            CHROMA_HNSW_EF_SEARCH_ENV: "100",
        }
    )

    assert config == {
        "hnsw": {
            "space": "cosine",
            "ef_construction": 200,
            "max_neighbors": 32,
            "ef_search": 100,
        }
    }


def test_build_hnsw_config_rejects_non_cosine_space() -> None:
    with pytest.raises(ValueError, match="must be 'cosine'"):
        build_hnsw_config(environ={"CHROMA_DISTANCE_SPACE": "l2"})


def test_collection_model_guard_passes_when_model_and_dimension_match() -> None:
    metadata = build_collection_metadata(
        embedding_model="fake-model",
        embedding_dimension=3,
    )

    validate_collection_model_guard(
        metadata,
        embedding_model="fake-model",
        embedding_dimension=3,
    )


def test_collection_model_guard_rejects_model_mismatch() -> None:
    metadata = build_collection_metadata(
        embedding_model="old-model",
        embedding_dimension=3,
    )

    with pytest.raises(CollectionModelGuardError, match="embedding guard mismatch"):
        validate_collection_model_guard(
            metadata,
            embedding_model="new-model",
            embedding_dimension=3,
        )


def test_collection_model_guard_rejects_dimension_mismatch() -> None:
    metadata = build_collection_metadata(
        embedding_model="fake-model",
        embedding_dimension=1024,
    )

    with pytest.raises(CollectionModelGuardError, match="embedding guard mismatch"):
        validate_collection_model_guard(
            metadata,
            embedding_model="fake-model",
            embedding_dimension=768,
        )


def _seed_record() -> SeedRecord:
    return SeedRecord(
        place_id="idx_001",
        name="인덱스 테스트 카페",
        address="서울 마포구 테스트로 1",
        latitude=37.5573,
        longitude=126.9245,
        atmosphere_text=(
            "창가 좌석과 잔잔한 음악이 있어 조용히 대화하기 좋은 분위기다. "
            "좌석 간격이 넓어 2인 대화와 짧은 업무 미팅에 적합하다."
        ),
        attributes=SeedAttributes(
            category="카페",
            parking=False,
            wifi=True,
            noise_level="조용함",
            seating_type=["개인석"],
            outdoor=False,
            reservation=None,
            price_range="1인 7000-12000원",
            operating_hours="09:00-22:00",
        ),
        source=SeedSource(
            type="fixture",
            author="pytest",
            verified_at="2026-05-28",
            reference="test fixture",
            notes="deterministic unit test",
        ),
    )
