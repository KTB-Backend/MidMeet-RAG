import sys

import pytest

from rag_core.embedder import DOCUMENT_MODE, QUERY_MODE, EmbeddingAdapter
from rag_core.retriever import (
    chroma_query_response_to_results,
    distance_to_atmosphere_score,
    search_atmosphere,
)


def test_retriever_import_does_not_require_optional_dependencies() -> None:
    assert "chromadb" not in sys.modules
    assert "sentence_transformers" not in sys.modules


def test_distance_to_atmosphere_score_uses_one_minus_distance() -> None:
    assert distance_to_atmosphere_score(0.0) == 1.0
    assert distance_to_atmosphere_score(1.0) == 0.0
    assert distance_to_atmosphere_score(0.25) == 0.75


def test_chroma_query_response_to_results_maps_response_in_chroma_order() -> None:
    response = {
        "ids": [["place_1", "place_2"]],
        "documents": [["조용한 분위기", "활기찬 분위기"]],
        "metadatas": [
            [
                {
                    "place_id": "place_1",
                    "name": "조용한 카페",
                    "address": "서울 마포구",
                    "latitude": 37.5573,
                    "longitude": 126.9245,
                    "attributes": '{"noise_level":"조용함"}',
                    "source": '{"type":"fixture"}',
                },
                {
                    "place_id": "place_2",
                    "name": "활기찬 식당",
                    "address": "서울 강남구",
                    "latitude": 37.4979,
                    "longitude": 127.0276,
                    "attributes": '{"noise_level":"시끄러움"}',
                    "source": '{"type":"fixture"}',
                },
            ]
        ],
        "distances": [[0.1, 0.7]],
    }

    results = chroma_query_response_to_results(response)

    assert len(results) == 2
    assert [result.place_id for result in results] == ["place_1", "place_2"]
    assert [result.name for result in results] == ["조용한 카페", "활기찬 식당"]
    assert results[0].address == "서울 마포구"
    assert results[0].latitude == 37.5573
    assert results[0].longitude == 126.9245
    assert results[0].attributes == '{"noise_level":"조용함"}'
    assert results[0].source == '{"type":"fixture"}'
    assert results[0].atmosphere_text == "조용한 분위기"
    assert results[0].distance == 0.1
    assert results[0].atmosphere_score == pytest.approx(0.9)
    assert results[1].atmosphere_score == pytest.approx(0.3)
    assert results[0].atmosphere_score > results[1].atmosphere_score


def test_chroma_query_response_to_results_returns_empty_list_for_no_matches() -> None:
    response = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }

    assert chroma_query_response_to_results(response) == []


def test_search_atmosphere_requires_chromadb_only_when_called(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "chromadb", None)

    with pytest.raises(RuntimeError, match="chromadb is required"):
        search_atmosphere("조용한 카페", FakeEmbeddingAdapter())


class FakeEmbeddingAdapter(EmbeddingAdapter):
    model_name = "fake-retriever-unit"

    def embed(self, texts: list[str], mode: str = DOCUMENT_MODE) -> list[list[float]]:
        assert mode == QUERY_MODE
        return [[float(len(texts[0])), 0.0, 1.0]]
