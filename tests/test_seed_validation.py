import json
import logging

import pytest

from rag_core.loader import (
    SeedRecord,
    SeedValidationError,
    load_seed_directory,
    validate_seed_records,
)


def test_load_seed_directory_returns_seed_records(tmp_path) -> None:
    (tmp_path / "b.json").write_text(
        json.dumps([_valid_seed("hd_002")], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "a.json").write_text(
        json.dumps(_valid_seed("hd_001"), ensure_ascii=False),
        encoding="utf-8",
    )

    records = load_seed_directory(tmp_path)

    assert [record.place_id for record in records] == ["hd_001", "hd_002"]
    assert all(isinstance(record, SeedRecord) for record in records)
    assert records[0].attributes.category == "카페"
    assert records[0].source.type == "fixture"


def test_missing_required_field_is_hard_failure() -> None:
    seed = _valid_seed()
    del seed["address"]

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    assert exc_info.value.issues[0].field == "address"
    assert "Missing required field: address" in str(exc_info.value)


def test_missing_coordinate_is_hard_failure_without_range_error() -> None:
    seed = _valid_seed()
    del seed["latitude"]

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    assert [issue.field for issue in exc_info.value.issues] == ["latitude"]
    assert "Missing required field: latitude" in str(exc_info.value)


def test_coordinate_out_of_korea_range_is_hard_failure() -> None:
    seed = _valid_seed(latitude=39.0)

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    assert exc_info.value.issues[0].field == "latitude"
    assert "between 33.0 and 38.9" in str(exc_info.value)


def test_missing_source_is_hard_failure() -> None:
    seed = _valid_seed()
    del seed["source"]

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    assert exc_info.value.issues[0].field == "source"
    assert "Missing required field: source" in str(exc_info.value)


def test_duplicate_place_id_is_hard_failure() -> None:
    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([_valid_seed("hd_001"), _valid_seed("hd_001")])

    assert exc_info.value.issues[0].field == "place_id"
    assert "Duplicate place_id: hd_001" in str(exc_info.value)


def test_short_atmosphere_text_warns_but_loads(caplog) -> None:
    seed = _valid_seed(atmosphere_text="짧은 분위기 설명")

    with caplog.at_level(logging.WARNING, logger="rag_core.loader"):
        records = validate_seed_records([seed])

    assert [record.place_id for record in records] == ["hd_001"]
    assert "atmosphere_text is shorter than 50 characters" in caplog.text


def test_non_string_place_id_is_hard_failure() -> None:
    seed = _valid_seed(place_id=123)

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    assert any(issue.field == "place_id" for issue in exc_info.value.issues)
    assert "must be a string" in str(exc_info.value)


def test_longitude_out_of_korea_range_is_hard_failure() -> None:
    seed = _valid_seed(longitude=132.0)

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    assert exc_info.value.issues[0].field == "longitude"
    assert "between 124.6 and 131.9" in str(exc_info.value)


def test_multiple_hard_failures_are_reported_together() -> None:
    seed = _valid_seed(place_id=123, longitude=132.0)

    with pytest.raises(SeedValidationError) as exc_info:
        validate_seed_records([seed])

    fields = [issue.field for issue in exc_info.value.issues]
    assert len(fields) >= 2
    assert "place_id" in fields
    assert "longitude" in fields


def test_duplicate_place_id_across_files_is_hard_failure(tmp_path) -> None:
    (tmp_path / "a.json").write_text(
        json.dumps(_valid_seed("hd_001"), ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "b.json").write_text(
        json.dumps(_valid_seed("hd_001"), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(SeedValidationError) as exc_info:
        load_seed_directory(tmp_path)

    assert any(issue.field == "place_id" for issue in exc_info.value.issues)
    assert "Duplicate" in str(exc_info.value)


def _valid_seed(
    place_id: str = "hd_001",
    latitude: float = 37.5573,
    longitude: float = 126.9245,
    atmosphere_text: str = (
        "통유리창으로 햇볕이 잘 들어오고 좌석 간격이 넓어 대화하기 좋다. "
        "배경 음악이 잔잔해 조용히 이야기 나누기에 적합하다."
    ),
) -> dict:
    return {
        "place_id": place_id,
        "name": "카페 예시",
        "address": "서울 마포구 홍대입구역 인근",
        "latitude": latitude,
        "longitude": longitude,
        "atmosphere_text": atmosphere_text,
        "attributes": {
            "category": "카페",
            "parking": False,
            "wifi": True,
            "noise_level": "조용함",
            "seating_type": ["개인석"],
            "outdoor": False,
            "reservation": None,
            "price_range": "1인 7,000-12,000원",
            "operating_hours": "09:00-22:00",
        },
        "source": {
            "type": "fixture",
            "author": "pytest",
            "verified_at": "2026-05-28",
            "reference": "deterministic unit test",
            "notes": "synthetic test seed",
        },
    }
