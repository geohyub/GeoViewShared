"""
geoview_pyside6.qc_engine.schema
================================
pydantic v2 schemas for YAML-declared RulePacks (Phase A-1 A1.2 Step 3).

YAML authors reference check functions by dotted name; the loader resolves
those names through a :class:`RuleCheckRegistry`. This file only handles
validation of the YAML shape — name resolution lives in ``loader.py``.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from geoview_pyside6.qc_engine.rules import Severity

__all__ = ["RuleSchema", "RulePackSchema"]


class RuleSchema(BaseModel):
    """YAML representation of a single rule."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    severity: str
    category: str = Field(min_length=1)
    check: str = Field(min_length=1, description="Dotted import path or registry key")
    description: str = ""
    auto_fix: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, v: str) -> str:
        Severity.coerce(v)  # raises ValueError if unknown
        return v.lower()


class RulePackSchema(BaseModel):
    """YAML representation of a rule pack."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    description: str = ""
    rules: list[RuleSchema] = Field(default_factory=list)

    @field_validator("rules")
    @classmethod
    def _unique_ids(cls, v: list[RuleSchema]) -> list[RuleSchema]:
        seen: set[str] = set()
        for r in v:
            if r.id in seen:
                raise ValueError(f"duplicate rule id {r.id!r}")
            seen.add(r.id)
        return v
