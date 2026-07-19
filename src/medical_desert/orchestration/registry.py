from __future__ import annotations

from .contracts import StageDefinition

STAGES: tuple[StageDefinition, ...] = (
    StageDefinition(
        0,
        "profile_source",
        "Freeze source manifest and profile.",
        "pipelines/sql/00_profile_source.sql",
    ),
    StageDefinition(
        1,
        "snapshot_bronze",
        "Conserve all source rows in bronze.",
        "pipelines/sql/01_snapshot_bronze.sql",
        (0,),
    ),
    StageDefinition(
        2,
        "validate_facility_rows",
        "Classify quarantine and exact duplicates.",
        "pipelines/sql/02_validate_facility_rows.sql",
        (1,),
    ),
    StageDefinition(
        3,
        "normalize_facilities",
        "Normalize canonical facility entities and fields.",
        "pipelines/sql/03_normalize_facilities.sql",
        (2,),
    ),
    StageDefinition(
        4,
        "build_postal_geography",
        "Validate offices and build PIN reference origins.",
        "pipelines/sql/04_build_postal_geography.sql",
        (1,),
    ),
    StageDefinition(
        5,
        "normalize_nfhs_context",
        "Parse NFHS observations and qualifiers.",
        "pipelines/sql/05_normalize_nfhs_context.sql",
        (1,),
    ),
    StageDefinition(
        6,
        "build_district_crosswalk",
        "Build deterministic state and district identity mappings.",
        "pipelines/sql/06_build_district_crosswalk.sql",
        (3, 4, 5),
    ),
    StageDefinition(
        7,
        "extract_evidence",
        "Build deterministic claims, evidence spans, and documents.",
        "pipelines/sql/07_extract_evidence.sql",
        (3,),
    ),
    StageDefinition(
        8,
        "validate_claims",
        "Apply deterministic evidence and attribution validators.",
        "pipelines/sql/08_validate_claims.sql",
        (7,),
    ),
    StageDefinition(
        9,
        "verify_high_impact",
        "Publish bounded external-verification candidates.",
        "pipelines/sql/09_verify_high_impact.sql",
        (8,),
    ),
    StageDefinition(
        10,
        "score_documentary_support",
        "Score capability-specific documentary support.",
        "pipelines/sql/10_score_documentary_support.sql",
        (8, 9),
    ),
    StageDefinition(
        11,
        "build_regional_evidence",
        "Build distances, regional summaries, and survey profiles.",
        "pipelines/sql/11_build_regional_evidence.sql",
        (4, 6, 10),
    ),
    StageDefinition(
        12,
        "build_verification_queue",
        "Rank verification and planning-priority candidates.",
        "pipelines/sql/12_build_verification_queue.sql",
        (11,),
    ),
)

_BY_NUMBER = {stage.number: stage for stage in STAGES}
_BY_ID = {stage.stage_id: stage for stage in STAGES}


def get_stage(value: int | str) -> StageDefinition:
    if isinstance(value, int) or str(value).isdigit():
        number = int(value)
        if number not in _BY_NUMBER:
            raise KeyError(f"Unknown pipeline stage: {value}")
        return _BY_NUMBER[number]
    if value not in _BY_ID:
        raise KeyError(f"Unknown pipeline stage: {value}")
    return _BY_ID[value]
