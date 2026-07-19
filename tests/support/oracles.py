from __future__ import annotations

import json
import math
import re
from hashlib import sha256
from pathlib import Path
from typing import Any

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def parse_json_like_array(raw: Any) -> tuple[Any, str]:
    if raw is None:
        return None, "missing"
    if not isinstance(raw, str):
        return None, "wrong_type"
    stripped = raw.strip()
    if not stripped:
        return None, "missing"
    if stripped in {"null", '"null"'}:
        return None, "null" if stripped == "null" else "null_string"
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return None, "unparseable"
    if not isinstance(parsed, list):
        return None, "wrong_shape"
    return parsed, "parsed"


def coordinate_disposition(latitude: Any, longitude: Any) -> str:
    missing = {None, "", "NA", "N/A", "null"}
    if latitude in missing or longitude in missing:
        return "unparseable_or_missing"
    try:
        lat = float(str(latitude).strip())
        lon = float(str(longitude).strip())
    except (TypeError, ValueError):
        return "unparseable_or_missing"
    if not math.isfinite(lat) or not math.isfinite(lon):
        return "unparseable_or_missing"
    if lat == 0 and lon == 0:
        return "zero_coordinate"
    if 6.5 <= lat <= 39 and 68 <= lon <= 98:
        return "valid"
    return "out_of_envelope"


def parse_nfhs_value(raw: Any) -> dict[str, Any]:
    if raw is None or not str(raw).strip():
        return {"numeric_value": None, "qualifier": None, "parse_status": "missing"}
    value = str(raw).strip()
    if value == "*":
        return {
            "numeric_value": None,
            "qualifier": "suppressed_lt_25",
            "parse_status": "unavailable",
        }
    qualifier = "standard"
    if value.startswith("(") and value.endswith(")"):
        qualifier = "low_sample_25_49"
        value = value[1:-1].strip()
    elif value.startswith("(") or value.endswith(")"):
        return {
            "numeric_value": None,
            "qualifier": "unrecognized",
            "parse_status": "unparseable",
        }
    try:
        numeric = float(value)
    except ValueError:
        return {
            "numeric_value": None,
            "qualifier": "unrecognized",
            "parse_status": "unparseable",
        }
    status = "parsed" if 0 <= numeric <= 100 else "parsed_out_of_range"
    return {"numeric_value": numeric, "qualifier": qualifier, "parse_status": status}


def documentary_support_index(factors: dict[str, float]) -> float:
    return min(100.0, max(0.0, sum(factors.values())))


def support_band(index: float | None, contradiction_state: str = "none") -> str:
    if index is None:
        return "insufficient_evidence"
    if contradiction_state == "confirmed":
        return "contradicted"
    if contradiction_state == "unresolved":
        return "abstain_or_policy_capped"
    if index >= 75:
        return "strongly_supported"
    if index >= 50:
        return "partially_supported"
    if index >= 25:
        return "claim_only_or_weak"
    return "unsupported_or_very_weak"


def verification_priority(values: list[float]) -> float:
    weights = [0.40, 0.25, 0.20, 0.10, 0.05]
    normalized = [min(1.0, max(0.0, value)) for value in values]
    return min(
        1.0,
        max(0.0, sum(v * w for v, w in zip(normalized, weights, strict=True))),
    )


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()
