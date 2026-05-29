"""Hybrid scoring for atmosphere retrieval results."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from typing import Mapping

from rag_core.geo import haversine_km
from rag_core.retriever import AtmosphereSearchResult


logger = logging.getLogger(__name__)

MAX_DISTANCE_KM_ENV = "MAX_DISTANCE_KM"
ATMOSPHERE_WEIGHT_ENV = "ATMOSPHERE_WEIGHT"
RECOMMEND_TOP_K_ENV = "RECOMMEND_TOP_K"

DEFAULT_MAX_DISTANCE_KM = 3.0
DEFAULT_ATMOSPHERE_WEIGHT = 0.7
DEFAULT_RECOMMEND_TOP_K = 5


@dataclass(frozen=True)
class ScoredResult:
    """A retrieval result with geographic distance and final hybrid score."""

    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    attributes: str
    source: str
    atmosphere_text: str
    atmosphere_score: float
    distance_score: float
    final_score: float
    distance_km: float


def score_results(
    results: list[AtmosphereSearchResult],
    centroid: tuple[float, float],
    *,
    max_distance_km: float | None = None,
    atmosphere_weight: float | None = None,
    recommend_top_k: int | None = None,
    environ: Mapping[str, str] | None = None,
) -> list[ScoredResult]:
    """Score retrieval results by atmosphere and Haversine distance."""

    env = os.environ if environ is None else environ
    resolved_max_distance = (
        max_distance_km
        if max_distance_km is not None
        else _float_from_env(env, MAX_DISTANCE_KM_ENV, DEFAULT_MAX_DISTANCE_KM)
    )
    resolved_weight = (
        atmosphere_weight
        if atmosphere_weight is not None
        else _float_from_env(env, ATMOSPHERE_WEIGHT_ENV, DEFAULT_ATMOSPHERE_WEIGHT)
    )
    resolved_top_k = (
        recommend_top_k
        if recommend_top_k is not None
        else _int_from_env(env, RECOMMEND_TOP_K_ENV, DEFAULT_RECOMMEND_TOP_K)
    )
    _validate_max_distance(resolved_max_distance)
    _validate_weight(resolved_weight)
    _validate_top_k(resolved_top_k)

    scored = [
        _score_single_result(
            result,
            centroid,
            max_distance_km=resolved_max_distance,
            atmosphere_weight=resolved_weight,
        )
        for result in results
    ]
    return sorted(scored, key=lambda result: result.final_score, reverse=True)[
        :resolved_top_k
    ]


def normalize_distance_score(distance_km: float, max_distance_km: float) -> float:
    """Normalize geographic distance into a 0..1 soft score."""

    if distance_km < 0:
        raise ValueError(f"distance_km must be non-negative; got {distance_km}.")
    _validate_max_distance(max_distance_km)
    return max(0.0, 1.0 - distance_km / max_distance_km)


def clamp_atmosphere_score(raw_atmosphere_score: float) -> float:
    """Floor raw cosine similarity at 0 before weighted scoring."""

    return max(0.0, float(raw_atmosphere_score))


def weighted_final_score(
    atmosphere_score: float, distance_score: float, atmosphere_weight: float
) -> float:
    """Combine normalized atmosphere and distance scores."""

    _validate_weight(atmosphere_weight)
    return (
        atmosphere_weight * atmosphere_score
        + (1.0 - atmosphere_weight) * distance_score
    )


def _score_single_result(
    result: AtmosphereSearchResult,
    centroid: tuple[float, float],
    *,
    max_distance_km: float,
    atmosphere_weight: float,
) -> ScoredResult:
    distance_km = haversine_km(centroid, (result.latitude, result.longitude))
    distance_score = normalize_distance_score(distance_km, max_distance_km)
    atmosphere_score = clamp_atmosphere_score(result.atmosphere_score)
    final_score = weighted_final_score(
        atmosphere_score,
        distance_score,
        atmosphere_weight,
    )

    return ScoredResult(
        place_id=result.place_id,
        name=result.name,
        address=result.address,
        latitude=result.latitude,
        longitude=result.longitude,
        attributes=result.attributes,
        source=result.source,
        atmosphere_text=result.atmosphere_text,
        atmosphere_score=atmosphere_score,
        distance_score=distance_score,
        final_score=final_score,
        distance_km=distance_km,
    )


def _float_from_env(env: Mapping[str, str], name: str, default: float) -> float:
    raw_value = env.get(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float; got {raw_value!r}.") from exc


def _int_from_env(env: Mapping[str, str], name: str, default: int) -> int:
    raw_value = env.get(name)
    if raw_value is None or raw_value == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer; got {raw_value!r}.") from exc


def _validate_max_distance(max_distance_km: float) -> None:
    if max_distance_km <= 0:
        raise ValueError(
            f"max_distance_km must be a positive number; got {max_distance_km}."
        )


def _validate_weight(atmosphere_weight: float) -> None:
    if not 0.0 <= atmosphere_weight <= 1.0:
        raise ValueError(
            f"atmosphere_weight must be between 0.0 and 1.0; got {atmosphere_weight}."
        )


def _validate_top_k(top_k: int) -> None:
    if top_k <= 0:
        raise ValueError(f"recommend_top_k must be a positive integer; got {top_k}.")
