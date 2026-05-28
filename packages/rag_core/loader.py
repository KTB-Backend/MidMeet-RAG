"""Seed loading and Layer 1 validation for MidMeet RAG."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

REQUIRED_FIELDS = (
    "place_id",
    "name",
    "address",
    "latitude",
    "longitude",
    "atmosphere_text",
    "attributes",
    "source",
)

MIN_LATITUDE = 33.0
MAX_LATITUDE = 38.9
MIN_LONGITUDE = 124.6
MAX_LONGITUDE = 131.9
MIN_ATMOSPHERE_TEXT_LENGTH = 50


@dataclass(frozen=True)
class SeedAttributes:
    """Structured venue attributes from the seed schema."""

    category: str | None = None
    parking: bool | None = None
    wifi: bool | None = None
    noise_level: str | None = None
    seating_type: list[str] | None = None
    outdoor: bool | None = None
    reservation: bool | None = None
    price_range: str | None = None
    operating_hours: str | None = None


@dataclass(frozen=True)
class SeedSource:
    """Provenance fields for a seed record."""

    type: str | None = None
    author: str | None = None
    verified_at: str | None = None
    reference: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class SeedRecord:
    """A single restaurant or cafe seed record."""

    place_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    atmosphere_text: str
    attributes: SeedAttributes
    source: SeedSource


@dataclass(frozen=True)
class ValidationIssue:
    """A hard validation failure found before indexing."""

    place_id: str | None
    field: str
    message: str


class SeedValidationError(ValueError):
    """Raised when seed records contain hard validation failures."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        super().__init__(_format_issues(issues))


def load_seed_directory(seed_dir: str | Path) -> list[SeedRecord]:
    """Load all JSON seed files in a directory and run Layer 1 validation."""

    directory = Path(seed_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Seed directory does not exist: {directory}")

    raw_records: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.json")):
        raw_records.extend(_load_json_records(path))

    return validate_seed_records(raw_records)


def validate_seed_records(raw_records: list[dict[str, object]]) -> list[SeedRecord]:
    """Validate raw seed dictionaries and convert them to dataclasses."""

    issues: list[ValidationIssue] = []
    records: list[SeedRecord] = []
    seen_place_ids: set[str] = set()

    for index, raw_record in enumerate(raw_records):
        record_issues: list[ValidationIssue] = []
        if not isinstance(raw_record, dict):
            record_issues.append(
                ValidationIssue(
                    place_id=None,
                    field="record",
                    message=f"Record at index {index} must be a JSON object.",
                )
            )
            issues.extend(record_issues)
            continue

        place_id = _string_value(raw_record.get("place_id"))
        record_issues.extend(_validate_required_fields(raw_record, place_id))

        if place_id is not None:
            if place_id in seen_place_ids:
                record_issues.append(
                    ValidationIssue(
                        place_id=place_id,
                        field="place_id",
                        message=f"Duplicate place_id: {place_id}",
                    )
                )
            seen_place_ids.add(place_id)

        record_issues.extend(_validate_coordinates(raw_record, place_id))

        atmosphere_text = _string_value(raw_record.get("atmosphere_text"))
        if atmosphere_text is not None and len(atmosphere_text) < MIN_ATMOSPHERE_TEXT_LENGTH:
            logger.warning(
                "Seed %s atmosphere_text is shorter than %d characters.",
                place_id or f"index:{index}",
                MIN_ATMOSPHERE_TEXT_LENGTH,
            )

        if not record_issues:
            records.append(_record_from_dict(raw_record))
        issues.extend(record_issues)

    if issues:
        raise SeedValidationError(issues)

    return records


def _load_json_records(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]

    raise SeedValidationError(
        [
            ValidationIssue(
                place_id=None,
                field="record",
                message=f"{path} must contain a JSON object or a list of objects.",
            )
        ]
    )


def _validate_required_fields(
    raw_record: dict[str, object], place_id: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in REQUIRED_FIELDS:
        if field not in raw_record or raw_record[field] is None:
            issues.append(
                ValidationIssue(
                    place_id=place_id,
                    field=field,
                    message=f"Missing required field: {field}",
                )
            )

    if "place_id" in raw_record and raw_record["place_id"] is not None:
        if not isinstance(raw_record["place_id"], str):
            issues.append(
                ValidationIssue(
                    place_id=place_id,
                    field="place_id",
                    message="place_id must be a string.",
                )
            )

    if "attributes" in raw_record and not isinstance(raw_record["attributes"], dict):
        issues.append(
            ValidationIssue(
                place_id=place_id,
                field="attributes",
                message="attributes must be a JSON object.",
            )
        )

    if "source" in raw_record and not isinstance(raw_record["source"], dict):
        issues.append(
            ValidationIssue(
                place_id=place_id,
                field="source",
                message="source must be a JSON object.",
            )
        )

    return issues


def _validate_coordinates(
    raw_record: dict[str, object], place_id: str | None
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    has_latitude = "latitude" in raw_record and raw_record["latitude"] is not None
    has_longitude = "longitude" in raw_record and raw_record["longitude"] is not None
    latitude = _float_value(raw_record.get("latitude"))
    longitude = _float_value(raw_record.get("longitude"))

    if has_latitude:
        if latitude is None:
            issues.append(
                ValidationIssue(
                    place_id=place_id,
                    field="latitude",
                    message="latitude must be a number.",
                )
            )
        elif not MIN_LATITUDE <= latitude <= MAX_LATITUDE:
            issues.append(
                ValidationIssue(
                    place_id=place_id,
                    field="latitude",
                    message=(
                        f"latitude must be between {MIN_LATITUDE} and {MAX_LATITUDE}: "
                        f"{latitude}"
                    ),
                )
            )

    if has_longitude:
        if longitude is None:
            issues.append(
                ValidationIssue(
                    place_id=place_id,
                    field="longitude",
                    message="longitude must be a number.",
                )
            )
        elif not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
            issues.append(
                ValidationIssue(
                    place_id=place_id,
                    field="longitude",
                    message=(
                        f"longitude must be between {MIN_LONGITUDE} and {MAX_LONGITUDE}: "
                        f"{longitude}"
                    ),
                )
            )

    return issues


def _record_from_dict(raw_record: dict[str, object]) -> SeedRecord:
    attributes = raw_record["attributes"]
    source = raw_record["source"]

    return SeedRecord(
        place_id=str(raw_record["place_id"]),
        name=str(raw_record["name"]),
        address=str(raw_record["address"]),
        latitude=float(raw_record["latitude"]),
        longitude=float(raw_record["longitude"]),
        atmosphere_text=str(raw_record["atmosphere_text"]),
        attributes=SeedAttributes(
            category=attributes.get("category"),
            parking=attributes.get("parking"),
            wifi=attributes.get("wifi"),
            noise_level=attributes.get("noise_level"),
            seating_type=attributes.get("seating_type"),
            outdoor=attributes.get("outdoor"),
            reservation=attributes.get("reservation"),
            price_range=attributes.get("price_range"),
            operating_hours=attributes.get("operating_hours"),
        ),
        source=SeedSource(
            type=source.get("type"),
            author=source.get("author"),
            verified_at=source.get("verified_at"),
            reference=source.get("reference"),
            notes=source.get("notes"),
        ),
    )


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _float_value(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_issues(issues: list[ValidationIssue]) -> str:
    return "; ".join(
        f"{issue.place_id or '<unknown>'}.{issue.field}: {issue.message}"
        for issue in issues
    )
