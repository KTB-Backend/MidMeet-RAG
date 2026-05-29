import pytest

from rag_core.embedder import (
    DOCUMENT_MODE,
    QUERY_MODE,
    QUERY_PREFIX,
    EmbeddingAdapter,
    _apply_query_prefix,
)


class FakeEmbeddingAdapter(EmbeddingAdapter):
    def embed(self, texts: list[str], mode: str = DOCUMENT_MODE) -> list[list[float]]:
        return [
            [float(len(text)), float(index), 1.0 if mode == QUERY_MODE else 0.0]
            for index, text in enumerate(texts)
        ]


def test_fake_embedding_adapter_returns_vector_for_each_input() -> None:
    adapter = FakeEmbeddingAdapter()

    vectors = adapter.embed(["조용한 카페", "단체 모임 식당"])

    assert len(vectors) == 2
    assert all(isinstance(vector, list) for vector in vectors)
    assert all(isinstance(value, float) for vector in vectors for value in vector)


def test_apply_query_prefix_adds_prefix_for_query_mode() -> None:
    texts = ["조용히 이야기하기 좋은 카페", "주차 가능한 식당"]

    prefixed = _apply_query_prefix(texts, QUERY_MODE)

    assert prefixed == [f"{QUERY_PREFIX}{text}" for text in texts]


def test_apply_query_prefix_leaves_document_mode_unchanged() -> None:
    texts = ["넓은 좌석과 잔잔한 음악", "단체석이 있는 밝은 식당"]

    prefixed = _apply_query_prefix(texts, DOCUMENT_MODE)

    assert prefixed == texts
    assert prefixed is not texts


def test_apply_query_prefix_outputs_differ_between_query_and_document_modes() -> None:
    texts = ["조용히 이야기하기 좋은 카페"]

    query_texts = _apply_query_prefix(texts, QUERY_MODE)
    document_texts = _apply_query_prefix(texts, DOCUMENT_MODE)

    assert query_texts != document_texts
    assert query_texts == [f"{QUERY_PREFIX}{texts[0]}"]
    assert document_texts == texts


def test_apply_query_prefix_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="Unknown embedding mode"):
        _apply_query_prefix(["조용한 카페"], "passage")
