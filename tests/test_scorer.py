import pytest

from rag_core.retriever import AtmosphereSearchResult
from rag_core.scorer import (
    clamp_atmosphere_score,
    normalize_distance_score,
    score_results,
    weighted_final_score,
)


CENTROID = (37.5000, 127.0000)


def test_distance_score_normalization() -> None:
    assert normalize_distance_score(0.0, 3.0) == 1.0
    assert normalize_distance_score(1.5, 3.0) == 0.5
    assert normalize_distance_score(3.0, 3.0) == 0.0
    assert normalize_distance_score(6.0, 3.0) == 0.0


def test_atmosphere_score_clamps_negative_raw_score_to_zero() -> None:
    assert clamp_atmosphere_score(-0.3) == 0.0
    assert clamp_atmosphere_score(0.8) == 0.8


def test_final_score_within_range() -> None:
    scores = [
        weighted_final_score(0.0, 0.0, 0.7),
        weighted_final_score(1.0, 0.0, 0.7),
        weighted_final_score(0.0, 1.0, 0.7),
        weighted_final_score(1.0, 1.0, 0.7),
    ]

    assert all(0.0 <= score <= 1.0 for score in scores)


def test_closer_venue_wins_when_distance_weight_high() -> None:
    results = [_near_low_atmosphere(), _far_high_atmosphere()]

    scored = score_results(
        results,
        CENTROID,
        max_distance_km=3.0,
        atmosphere_weight=0.2,
        recommend_top_k=2,
    )

    assert scored[0].place_id == "near_low"
    assert scored[0].distance_score > scored[1].distance_score


def test_atmosphere_score_dominates_when_weight_high() -> None:
    results = [_near_low_atmosphere(), _far_high_atmosphere()]

    scored = score_results(
        results,
        CENTROID,
        max_distance_km=3.0,
        atmosphere_weight=0.9,
        recommend_top_k=2,
    )

    assert scored[0].place_id == "far_high"
    assert scored[0].atmosphere_score > scored[1].atmosphere_score


def test_scored_results_include_three_scores_and_sort_by_final_score() -> None:
    results = [
        _result("middle", atmosphere_score=0.5, latitude=37.5010, longitude=127.0010),
        _far_high_atmosphere(),
        _near_low_atmosphere(),
    ]

    scored = score_results(
        results,
        CENTROID,
        max_distance_km=3.0,
        atmosphere_weight=0.7,
        recommend_top_k=3,
    )

    assert len(scored) == 3
    assert [result.final_score for result in scored] == sorted(
        [result.final_score for result in scored],
        reverse=True,
    )
    for result in scored:
        assert 0.0 <= result.atmosphere_score <= 1.0
        assert 0.0 <= result.distance_score <= 1.0
        assert 0.0 <= result.final_score <= 1.0


def test_recommend_top_k_cuts_final_results() -> None:
    scored = score_results(
        [_near_low_atmosphere(), _far_high_atmosphere(), _distant_negative()],
        CENTROID,
        max_distance_km=3.0,
        atmosphere_weight=0.7,
        recommend_top_k=2,
    )

    assert len(scored) == 2


def test_soft_scoring_keeps_candidate_outside_max_distance() -> None:
    scored = score_results(
        [_distant_negative()],
        CENTROID,
        max_distance_km=1.0,
        atmosphere_weight=0.7,
        recommend_top_k=1,
    )

    assert len(scored) == 1
    assert scored[0].distance_km > 1.0
    assert scored[0].distance_score == 0.0
    assert scored[0].atmosphere_score == 0.0


def test_score_results_is_deterministic() -> None:
    results = [_near_low_atmosphere(), _far_high_atmosphere(), _distant_negative()]

    first = score_results(
        results,
        CENTROID,
        max_distance_km=3.0,
        atmosphere_weight=0.7,
        recommend_top_k=3,
    )
    second = score_results(
        results,
        CENTROID,
        max_distance_km=3.0,
        atmosphere_weight=0.7,
        recommend_top_k=3,
    )

    assert first == second


def test_score_results_reads_environment_configuration() -> None:
    scored = score_results(
        [_near_low_atmosphere(), _far_high_atmosphere(), _distant_negative()],
        CENTROID,
        environ={
            "MAX_DISTANCE_KM": "3.0",
            "ATMOSPHERE_WEIGHT": "0.9",
            "RECOMMEND_TOP_K": "1",
        },
    )

    assert [result.place_id for result in scored] == ["far_high"]


def _near_low_atmosphere() -> AtmosphereSearchResult:
    return _result(
        "near_low",
        atmosphere_score=0.2,
        latitude=37.5005,
        longitude=127.0005,
    )


def _far_high_atmosphere() -> AtmosphereSearchResult:
    return _result(
        "far_high",
        atmosphere_score=0.95,
        latitude=37.5572,
        longitude=126.9247,
    )


def _distant_negative() -> AtmosphereSearchResult:
    return _result(
        "distant_negative",
        atmosphere_score=-0.25,
        latitude=37.4500,
        longitude=127.1000,
    )


def _result(
    place_id: str,
    *,
    atmosphere_score: float,
    latitude: float,
    longitude: float,
) -> AtmosphereSearchResult:
    return AtmosphereSearchResult(
        place_id=place_id,
        name=f"{place_id} name",
        address=f"{place_id} address",
        latitude=latitude,
        longitude=longitude,
        attributes='{"category":"카페"}',
        source='{"type":"fixture"}',
        atmosphere_text=f"{place_id} atmosphere",
        atmosphere_score=atmosphere_score,
        distance=1.0 - atmosphere_score,
    )
