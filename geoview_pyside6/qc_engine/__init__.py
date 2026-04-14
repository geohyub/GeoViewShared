"""
geoview_pyside6.qc_engine
================================
Declarative QC rule harness (Phase A-1 A1.2).

선언형 QC 룰 DSL — target (CPTSounding, MagLine, ...) 을 받아
`geoview_common.qc.common.QCResult` 를 생성하는 domain-agnostic 엔진.

Public API:
    Severity              critical | warning | info enum
    Rule                  frozen dataclass (id, title, severity, category, check, ...)
    RulePack              mutable collection (get/filter)
    rule                  @rule decorator (code-first definition)
    RuleCheckRegistry     name → check-function registry (for YAML loader)
    RulePackSchema        pydantic v2 schema (data-first)
    RuleSchema
    load_yaml             YAML → RulePack
    RuleRunner            RulePack + target → QCResult

Design decisions (A1.1 원칙 유지):
    1. Rule 은 frozen dataclass
    2. RulePack 은 mutable (filter/get)
    3. Check 는 순수 함수. 예외는 runner 가 swallow → fail issue
    4. YAML + @rule decorator 양립
    5. geoview_common.qc.common.models 재사용 (QCResult/QCIssue 확장 없음)
    6. pydantic v2
    7. 도메인 격리 — CPT 심볼 zero

Consumers (Wave 2+):
    geoview_cpt.qc_rules.cpt_base.yaml (14 rules from cpt_formulas_and_qc_catalog §4)
    geoview_cpt.qc_checks.*             (CPT 전용 check 함수)
"""
from __future__ import annotations

from geoview_pyside6.qc_engine.rules import (
    Rule,
    RulePack,
    RuleCheck,
    RuleAutoFix,
    Severity,
    rule,
)

__all__ = [
    "Rule",
    "RulePack",
    "RuleCheck",
    "RuleAutoFix",
    "Severity",
    "rule",
]
