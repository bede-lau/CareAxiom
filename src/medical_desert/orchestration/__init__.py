"""Deterministic orchestration for Medical Desert Planner data products."""

from .contracts import PipelineContext, StageDefinition, StageResult
from .registry import STAGES, get_stage

__all__ = [
    "PipelineContext",
    "StageDefinition",
    "StageResult",
    "STAGES",
    "get_stage",
]
