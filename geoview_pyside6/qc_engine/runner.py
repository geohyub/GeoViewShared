"""
geoview_pyside6.qc_engine.runner
================================
Executes a :class:`RulePack` against a target object and produces a
:class:`geoview_common.qc.common.models.QCResult`.

Design decisions:
 - **One stage per rule**: each rule becomes a :class:`QCStageResult` so
   per-rule pass/fail is traceable in downstream reporting. Stages inherit
   a simple pass/fail score (``max_score`` on pass, 0 on fail); richer
   scoring lives in ``geoview_common.qc.common.scoring``.
 - **Exception swallowing**: if a check raises, the runner catches it and
   synthesizes a critical :class:`QCIssue` describing the failure
   (MagQC 교훈 #22 — 단일 경로로 score/issue 생성). The rule's stage is
   marked FAIL, but the overall run continues.
 - **Optional cache hook**: ``cache`` is a dict-like mapping ``rule_id →
   list[QCIssue]`` used to short-circuit repeated runs against the same
   target (SeismicQC #14 / SonarQC #14). The runner only reads the cache
   and writes successful results back; failures are never cached.
 - **Total score**: ``PASS ratio * 100`` (simple, transparent). Callers that
   need weighted scoring can post-process or swap to ``compute_score``
   with a ``ScoringProfile`` later.
 - The runner never imports CPT symbols — domain binding happens via the
   ``domain`` argument on :meth:`RuleRunner.run`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, MutableMapping

from geoview_common.qc.common.models import (
    QCDomain,
    QCIssue,
    QCResult,
    QCStageResult,
    QCStatus,
)
from geoview_common.qc.common.scoring import assign_grade

from geoview_pyside6.qc_engine.rules import Rule, RulePack, Severity

__all__ = ["RuleRunner", "RunnerCache"]


# Cache: rule_id → list[QCIssue]. Pluggable — pass any MutableMapping.
RunnerCache = MutableMapping[str, list[QCIssue]]


def _issue_from_exception(rule: Rule, exc: BaseException) -> QCIssue:
    return QCIssue(
        severity=Severity.CRITICAL.value,
        category=rule.category,
        description=(
            f"rule {rule.id!r} raised {type(exc).__name__}: {exc}"
        ),
        location=rule.id,
        suggestion="fix the check implementation",
    )


def _stage_status(rule: Rule, issues: list[QCIssue]) -> QCStatus:
    if not issues:
        return QCStatus.PASS
    severities = {i.severity for i in issues}
    if Severity.CRITICAL.value in severities:
        return QCStatus.FAIL
    if Severity.WARNING.value in severities:
        return QCStatus.WARN
    return QCStatus.PASS  # info-only — still passes the stage


@dataclass
class RuleRunner:
    """Runs a RulePack against a target and builds a QCResult."""

    pack: RulePack
    cache: RunnerCache | None = None

    def run(
        self,
        target: Any,
        *,
        domain: QCDomain,
        file_name: str,
        line_name: str = "",
        auto_fix: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> QCResult:
        """
        Execute every rule in the pack against ``target``.

        Args:
            target:     Domain payload the checks operate on.
            domain:     QCDomain to stamp the result with.
            file_name:  Source file label for the QCResult.
            line_name:  Optional survey-line identifier.
            auto_fix:   If True and a rule has ``auto_fix`` set, it is invoked
                        *instead* of :attr:`Rule.check`.
            extra:      Optional dict merged into ``QCResult.extra``.
        """
        stages: list[QCStageResult] = []
        all_issues: list[QCIssue] = []
        t0 = time.perf_counter()
        passed = 0

        for idx, r in enumerate(self.pack.rules):
            stage = self._run_one(r, target, idx=idx, auto_fix=auto_fix)
            stages.append(stage)
            all_issues.extend(stage.issues)
            if stage.status is QCStatus.PASS:
                passed += 1

        total = len(self.pack.rules)
        total_score = (passed / total * 100.0) if total else 0.0
        grade = assign_grade(total_score)
        status = QCStatus.from_score(total_score) if total else QCStatus.NA

        return QCResult(
            domain=domain,
            file_name=file_name,
            line_name=line_name,
            analysis_type="rule_pack",
            total_score=round(total_score, 2),
            grade=grade,
            status=status,
            stages=stages,
            issues=all_issues,
            duration_ms=(time.perf_counter() - t0) * 1000.0,
            record_count=total,
            extra={
                "pack_name": self.pack.name,
                "pack_version": self.pack.version,
                "pack_domain": self.pack.domain,
                "rule_passed": passed,
                "rule_total": total,
                **(extra or {}),
            },
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _run_one(
        self,
        r: Rule,
        target: Any,
        *,
        idx: int,
        auto_fix: bool,
    ) -> QCStageResult:
        cache_hit = False
        cached: list[QCIssue] | None = None
        if self.cache is not None and not auto_fix:
            cached = self.cache.get(r.id)
            if cached is not None:
                cache_hit = True

        t_stage = time.perf_counter()
        if cache_hit:
            issues = list(cached or [])
            crashed = False
        else:
            issues, crashed = self._invoke_check(r, target, auto_fix=auto_fix)

        duration = (time.perf_counter() - t_stage) * 1000.0
        status = QCStatus.FAIL if crashed else _stage_status(r, issues)
        score = 0.0 if status is QCStatus.FAIL else (
            10.0 if status is QCStatus.PASS else 5.0
        )

        if (
            self.cache is not None
            and not cache_hit
            and not crashed
            and not auto_fix
        ):
            self.cache[r.id] = list(issues)

        return QCStageResult(
            stage_name=r.id,
            stage_index=idx,
            score=score,
            max_score=10.0,
            status=status,
            issues=issues,
            detail={
                "title": r.title,
                "category": r.category,
                "severity": r.severity.value,
                "cache_hit": cache_hit,
                "crashed": crashed,
                "auto_fix_invoked": auto_fix and r.auto_fix is not None,
            },
            duration_ms=duration,
        )

    def _invoke_check(
        self,
        r: Rule,
        target: Any,
        *,
        auto_fix: bool,
    ) -> tuple[list[QCIssue], bool]:
        fn = r.auto_fix if (auto_fix and r.auto_fix is not None) else r.check
        try:
            raw = fn(target)
        except Exception as exc:  # noqa: BLE001 — intentional catch-all
            return [_issue_from_exception(r, exc)], True
        if raw is None:
            return [], False
        if not isinstance(raw, list):
            return (
                [
                    QCIssue(
                        severity=Severity.CRITICAL.value,
                        category=r.category,
                        description=(
                            f"rule {r.id!r} returned {type(raw).__name__}, "
                            "expected list[QCIssue]"
                        ),
                        location=r.id,
                    )
                ],
                True,
            )
        return list(raw), False
