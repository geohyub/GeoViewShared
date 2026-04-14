"""Tests for geoview_pyside6.qc_engine.runner — Step 4."""
from __future__ import annotations

import pytest

from geoview_common.qc.common.models import QCDomain, QCIssue, QCStatus

from geoview_pyside6.qc_engine import Rule, RulePack, Severity
from geoview_pyside6.qc_engine.runner import RuleRunner


def _pass_check(target):
    return []


def _warn_check(target):
    return [QCIssue(severity="warning", category="c", description="warn")]


def _fail_check(target):
    return [QCIssue(severity="critical", category="c", description="bad")]


def _raise_check(target):
    raise RuntimeError("boom")


def _bad_return_check(target):
    return "not a list"  # type: ignore[return-value]


def _rule(id: str, check, sev=Severity.INFO, cat="basic") -> Rule:
    return Rule(id=id, title=f"T {id}", severity=sev, category=cat, check=check)


# ---------------------------------------------------------------------------


class TestRuleRunnerBasics:
    def test_empty_pack_returns_na(self):
        runner = RuleRunner(pack=RulePack(name="p", version="1", domain="cpt"))
        result = runner.run(object(), domain=QCDomain.CPT, file_name="f")
        assert result.status is QCStatus.NA
        assert result.total_score == 0.0
        assert result.stages == []
        assert result.extra["rule_total"] == 0

    def test_all_pass(self):
        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[_rule("A", _pass_check), _rule("B", _pass_check)],
        )
        result = RuleRunner(pack=pack).run(object(), domain=QCDomain.CPT, file_name="f")
        assert result.total_score == 100.0
        assert result.status is QCStatus.PASS
        assert all(s.status is QCStatus.PASS for s in result.stages)
        assert result.issues == []
        assert result.extra["rule_passed"] == 2

    def test_mixed_results(self):
        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[
                _rule("A", _pass_check),
                _rule("B", _warn_check, sev=Severity.WARNING),
                _rule("C", _fail_check, sev=Severity.CRITICAL),
                _rule("D", _pass_check),
            ],
        )
        result = RuleRunner(pack=pack).run(object(), domain=QCDomain.CPT, file_name="f")
        assert result.extra["rule_passed"] == 2
        assert result.total_score == 50.0
        statuses = [s.status for s in result.stages]
        assert statuses == [QCStatus.PASS, QCStatus.WARN, QCStatus.FAIL, QCStatus.PASS]
        assert len(result.issues) == 2  # warning + critical issues
        # issue aggregation
        severities = {i.severity for i in result.issues}
        assert severities == {"warning", "critical"}

    def test_exception_converted_to_fail_issue(self):
        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[_rule("A", _raise_check)],
        )
        result = RuleRunner(pack=pack).run(object(), domain=QCDomain.CPT, file_name="f")
        assert result.total_score == 0.0
        stage = result.stages[0]
        assert stage.status is QCStatus.FAIL
        assert stage.detail["crashed"] is True
        assert len(stage.issues) == 1
        assert "RuntimeError" in stage.issues[0].description
        assert "boom" in stage.issues[0].description

    def test_non_list_return_flagged_as_crash(self):
        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[_rule("A", _bad_return_check)],
        )
        result = RuleRunner(pack=pack).run(object(), domain=QCDomain.CPT, file_name="f")
        stage = result.stages[0]
        assert stage.status is QCStatus.FAIL
        assert "expected list[QCIssue]" in stage.issues[0].description

    def test_none_return_treated_as_empty_list(self):
        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[_rule("A", lambda t: None)],  # type: ignore[arg-type]
        )
        result = RuleRunner(pack=pack).run(object(), domain=QCDomain.CPT, file_name="f")
        assert result.stages[0].status is QCStatus.PASS

    def test_extra_merged(self):
        runner = RuleRunner(pack=RulePack(name="p", version="1", domain="cpt"))
        result = runner.run(
            object(), domain=QCDomain.CPT, file_name="f", extra={"source": "test"}
        )
        assert result.extra["source"] == "test"
        assert result.extra["pack_name"] == "p"

    def test_domain_cpt_recognized(self):
        assert QCDomain.CPT.value == "cpt"


class TestRunnerCache:
    def test_cache_hit_skips_check(self):
        calls = {"n": 0}

        def counting_check(target):
            calls["n"] += 1
            return []

        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[_rule("A", counting_check)],
        )
        cache: dict = {}
        runner = RuleRunner(pack=pack, cache=cache)

        runner.run(object(), domain=QCDomain.CPT, file_name="f")
        runner.run(object(), domain=QCDomain.CPT, file_name="f")

        assert calls["n"] == 1
        assert "A" in cache

    def test_crashed_rule_not_cached(self):
        pack = RulePack(
            name="p",
            version="1",
            domain="cpt",
            rules=[_rule("A", _raise_check)],
        )
        cache: dict = {}
        RuleRunner(pack=pack, cache=cache).run(
            object(), domain=QCDomain.CPT, file_name="f"
        )
        assert cache == {}


class TestAutoFix:
    def test_auto_fix_hook_invoked(self):
        calls = {"check": 0, "fix": 0}

        def check(target):
            calls["check"] += 1
            return [QCIssue(severity="warning", category="c", description="w")]

        def fix(target):
            calls["fix"] += 1
            return []

        r = Rule(
            id="A",
            title="t",
            severity=Severity.WARNING,
            category="c",
            check=check,
            auto_fix=fix,
        )
        pack = RulePack(name="p", version="1", domain="cpt", rules=[r])
        runner = RuleRunner(pack=pack)

        result = runner.run(
            object(), domain=QCDomain.CPT, file_name="f", auto_fix=True
        )
        assert calls["fix"] == 1
        assert calls["check"] == 0
        assert result.stages[0].status is QCStatus.PASS
        assert result.stages[0].detail["auto_fix_invoked"] is True
