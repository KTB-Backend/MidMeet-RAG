import pytest

from rag_core.embedder import (
    EMBEDDING_DIMENSIONS,
    QUERY_MODE,
    SnowflakeArcticEmbedAdapter,
)


def test_snowflake_arctic_embedder_returns_1024_dim_vector() -> None:
    pytest.importorskip("sentence_transformers")

    adapter = SnowflakeArcticEmbedAdapter()
    vectors = adapter.embed(["조용히 이야기하기 좋은 카페"], mode=QUERY_MODE)

    assert len(vectors) == 1
    assert len(vectors[0]) == EMBEDDING_DIMENSIONS
    assert all(isinstance(value, float) for value in vectors[0])
