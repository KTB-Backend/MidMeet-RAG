from pathlib import Path

from rag_core.loader import load_seed_directory


def test_committed_fixtures_load_without_hard_failures() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    records = load_seed_directory(repo_root / "data" / "seeds" / "fixtures")
    banned_atmosphere_tokens = ("합성", "시드", "검증", "대조군", "픽스처", "실험")

    assert len(records) >= 5
    assert all(record.source.type == "fixture" for record in records)
    assert any(record.attributes.noise_level == "조용함" for record in records)
    assert any(record.attributes.noise_level == "시끄러움" for record in records)
    assert any(
        "단체석" in (record.attributes.seating_type or []) for record in records
    )
    assert {"카페", "식당"}.issubset(
        {record.attributes.category for record in records}
    )
    assert all(
        token not in record.atmosphere_text
        for record in records
        for token in banned_atmosphere_tokens
    )
    assert (
        sum(
            record.attributes.category == "카페"
            and record.attributes.noise_level == "조용함"
            for record in records
        )
        >= 2
    )
