from __future__ import annotations

from dataclasses import replace
import json

import pytest

from rag_core.embedder import DOCUMENT_MODE, EmbeddingAdapter
from rag_core.indexer import index_seed_records
from rag_core.loader import SeedAttributes, SeedRecord, SeedSource


chromadb = pytest.importorskip("chromadb")


class FakeEmbeddingAdapter(EmbeddingAdapter):
    model_name = "fake-indexer-smoke"

    def embed(self, texts: list[str], mode: str = DOCUMENT_MODE) -> list[list[float]]:
        assert mode == DOCUMENT_MODE
        return [_vector_for_text(text) for text in texts]


def test_chroma_indexer_upserts_and_round_trips_metadata(tmp_path) -> None:
    chroma_path = tmp_path / "chroma"
    collection_name = "venues_smoke"
    records = _seed_records()
    embedder = FakeEmbeddingAdapter()

    result = index_seed_records(
        records,
        embedder,
        chroma_path=chroma_path,
        collection_name=collection_name,
        environ={},
    )

    assert result.indexed_count == 3
    assert result.collection_count == 3

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_collection(name=collection_name, embedding_function=None)
    query = collection.query(
        query_embeddings=[embedder.embed([records[0].atmosphere_text])[0]],
        n_results=1,
        include=["documents", "metadatas", "distances"],
    )

    assert query["ids"][0][0] == records[0].place_id
    assert query["documents"][0][0] == records[0].atmosphere_text
    metadata = query["metadatas"][0][0]
    assert metadata["name"] == records[0].name
    assert json.loads(metadata["attributes"])["category"] == "카페"
    assert json.loads(metadata["source"])["type"] == "fixture"

    updated_record = replace(records[0], name="업데이트된 조용한 카페")
    updated_result = index_seed_records(
        [updated_record],
        embedder,
        chroma_path=chroma_path,
        collection_name=collection_name,
        environ={},
    )

    assert updated_result.indexed_count == 1
    assert updated_result.collection_count == 3
    stored = collection.get(
        ids=[updated_record.place_id],
        include=["documents", "metadatas"],
    )
    assert stored["metadatas"][0]["name"] == "업데이트된 조용한 카페"


def _vector_for_text(text: str) -> list[float]:
    if "조용" in text:
        return [1.0, 0.0, 0.0]
    if "단체" in text:
        return [0.0, 1.0, 0.0]
    return [0.0, 0.0, 1.0]


def _seed_records() -> list[SeedRecord]:
    return [
        _seed_record(
            place_id="smoke_001",
            name="스모크 조용한 카페",
            atmosphere_text=(
                "창가 좌석과 잔잔한 음악이 있어 조용히 대화하기 좋은 카페다. "
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
        ),
        _seed_record(
            place_id="smoke_002",
            name="스모크 단체 식당",
            atmosphere_text=(
                "예약 가능한 단체석과 넓은 테이블이 있어 여러 명이 앉기 좋은 식당이다. "
                "저녁 모임과 회식 전에 식사하기 좋은 활기 있는 분위기다."
            ),
            attributes=SeedAttributes(
                category="식당",
                parking=True,
                wifi=None,
                noise_level="보통",
                seating_type=["단체석"],
                outdoor=None,
                reservation=True,
                price_range="1인 15000-30000원",
                operating_hours="17:00-22:00",
            ),
        ),
        _seed_record(
            place_id="smoke_003",
            name="스모크 역앞 펍",
            atmosphere_text=(
                "역 앞에서 짧게 들르기 좋은 저녁 장소다. 바 좌석과 일반 테이블이 있고 "
                "대화 소리가 적당히 섞여 편안하게 머물 수 있다."
            ),
            attributes=SeedAttributes(
                category="술집",
                parking=False,
                wifi=None,
                noise_level="보통",
                seating_type=["바 좌석"],
                outdoor=None,
                reservation=False,
                price_range="1인 15000-25000원",
                operating_hours="18:00-24:00",
            ),
        ),
    ]


def _seed_record(
    *,
    place_id: str,
    name: str,
    atmosphere_text: str,
    attributes: SeedAttributes,
) -> SeedRecord:
    return SeedRecord(
        place_id=place_id,
        name=name,
        address="서울 마포구 스모크 테스트로 1",
        latitude=37.5573,
        longitude=126.9245,
        atmosphere_text=atmosphere_text,
        attributes=attributes,
        source=SeedSource(
            type="fixture",
            author="pytest",
            verified_at="2026-05-29",
            reference="indexer smoke test",
            notes="synthetic eval fixture",
        ),
    )
