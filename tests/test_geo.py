import pytest

from rag_core.geo import compute_centroid, haversine_km


def test_compute_centroid_returns_arithmetic_mean() -> None:
    coords = [
        (37.5572, 126.9247),
        (37.4979, 127.0276),
        (37.5495, 126.9149),
    ]

    centroid = compute_centroid(coords)

    assert centroid == pytest.approx((37.5348666667, 126.9557333333))


def test_compute_centroid_returns_single_coordinate() -> None:
    coord = (37.5572, 126.9247)

    assert compute_centroid([coord]) == coord


def test_compute_centroid_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="At least one coordinate"):
        compute_centroid([])


def test_compute_centroid_rejects_out_of_range_coordinate() -> None:
    with pytest.raises(ValueError, match="latitude must be between"):
        compute_centroid([(32.9, 126.9247)])


def test_haversine_km_returns_zero_for_same_coordinate() -> None:
    coord = (37.4979, 127.0276)

    assert haversine_km(coord, coord) == 0.0


def test_haversine_km_matches_known_gangnam_to_hongdae_distance() -> None:
    gangnam_station = (37.4979, 127.0276)
    hongdae_station = (37.5572, 126.9247)

    assert haversine_km(gangnam_station, hongdae_station) == pytest.approx(
        11.2,
        abs=0.5,
    )


def test_haversine_km_is_symmetric() -> None:
    gangnam_station = (37.4979, 127.0276)
    hongdae_station = (37.5572, 126.9247)

    assert haversine_km(gangnam_station, hongdae_station) == pytest.approx(
        haversine_km(hongdae_station, gangnam_station)
    )
