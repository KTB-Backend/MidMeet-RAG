"""Geographic helpers for MidMeet scoring."""

from __future__ import annotations

import logging
import math

from rag_core.loader import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
)


logger = logging.getLogger(__name__)

EARTH_RADIUS_KM = 6371.0088


def compute_centroid(coords: list[tuple[float, float]]) -> tuple[float, float]:
    """Return the arithmetic latitude/longitude centroid for Korean coordinates."""

    if not coords:
        raise ValueError("At least one coordinate is required to compute centroid.")

    for coord in coords:
        _validate_coordinate(coord)

    latitude = sum(coord[0] for coord in coords) / len(coords)
    longitude = sum(coord[1] for coord in coords) / len(coords)
    centroid = (latitude, longitude)
    _validate_coordinate(centroid)
    return centroid


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Calculate great-circle distance between two coordinates in kilometers."""

    _validate_coordinate(a)
    _validate_coordinate(b)
    if a == b:
        return 0.0

    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    central_angle = 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return EARTH_RADIUS_KM * central_angle


def _validate_coordinate(coord: tuple[float, float]) -> None:
    latitude, longitude = coord
    if not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
        raise ValueError(
            f"latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}: {latitude}"
        )
    if not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise ValueError(
            f"longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}: {longitude}"
        )
