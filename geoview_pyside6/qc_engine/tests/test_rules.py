"""Tests for geoview_pyside6.qc_engine.rules — Phase A-1 A1.2 Step 2."""
from __future__ import annotations

import pytest

from geoview_pyside6.qc_engine import Rule, RulePack, Severity, rule


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------


class TestSeverity:
    def test_enum_values(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_coerce_from_enum(self):
        assert Severity.coerce(Severity.CRITICAL) is Severity.CRITICAL

    def test_coerce_from_lowercase_string(self):
        assert Severity.coerce("warning") is Severity.WARNING

    def test_coerce_from_uppercase_string(self):
        assert Severity.coerce("INFO") is Severity.INFO

    def test_coerce_rejects_unknown_string(self):
        with pytest.raises(ValueError, match="Unknown severity"):
            Severity.coerce("fatal")

    def test_coerce_rejects_non_string_type(self):
        with pytest.raises(TypeError):
            Severity.coerce(3)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Rule
# ---------------------------------------------------------------------------


def _noop(target) -> list:
    return []


class TestRule:
    def test_valid_construction(self):
        r = Rule(
            id="R1",
            title="Dummy",
            severity=Severity.INFO,
            category="basic",
            check=_noop,
        )
        assert r.id == "R1"
        assert r.severity is Severity.INFO
        assert r.parameters == {}
        assert r.auto_fix is None

    def test_frozen_rejects_mutation(self):
        r = Rule(id="R1", title="t", severity=Severity.INFO, category="c", check=_noop)
        with pytest.raises(Exception):
            r.id = "R2"  # type: ignore[misc]

    def test_severity_string_is_coerced(self):
        r = Rule(id="R1", title="t", severity="warning", category="c", check=_noop)  # type: ignore[arg-type]
        assert r.severity is Severity.WARNING

    def test_empty_id_rejected(self):
        with pytest.raises(ValueError, match="Rule.id"):
            Rule(id="", title="t", severity=Severity.INFO, category="c", check=_noop)

    def test_empty_title_rejected(self):
        with pytest.raises(ValueError, match="Rule.title"):
            Rule(id="R1", title="", severity=Severity.INFO, category="c", check=_noop)

    def test_empty_category_rejected(self):
        with pytest.raises(ValueError, match="Rule.category"):
            Rule(id="R1", title="t", severity=Severity.INFO, category="", check=_noop)

    def test_non_callable_check_rejected(self):
        with pytest.raises(TypeError, match="callable"):
            Rule(id="R1", title="t", severity=Severity.INFO, category="c", check=42)  # type: ignore[arg-type]

    def test_auto_fix_must_be_callable_or_none(self):
        with pytest.raises(TypeError):
            Rule(
                id="R1",
                title="t",
                severity=Severity.INFO,
                category="c",
                check=_noop,
                auto_fix="not-callable",  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# RulePack
# ---------------------------------------------------------------------------


def _rule(id: str, sev: Severity = Severity.INFO, cat: str = "basic") -> Rule:
    return Rule(id=id, title=f"Title {id}", severity=sev, category=cat, check=_noop)


class TestRulePack:
    def test_construction_and_len(self):
        pack = RulePack(
            name="p",
            version="1.0",
            domain="cpt",
            rules=[_rule("A"), _rule("B")],
        )
        assert len(pack) == 2
        assert list(pack) == pack.rules

    def test_duplicate_id_rejected(self):
        with pytest.raises(ValueError, match="duplicate rule id"):
            RulePack(name="p", version="1.0", domain="cpt", rules=[_rule("A"), _rule("A")])

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError, match="RulePack.name"):
            RulePack(name="", version="1.0", domain="cpt")

    def test_get_existing(self):
        pack = RulePack(name="p", version="1.0", domain="cpt", rules=[_rule("A")])
        assert pack.get("A").id == "A"

    def test_get_missing_raises(self):
        pack = RulePack(name="p", version="1.0", domain="cpt")
        with pytest.raises(KeyError):
            pack.get("nope")

    def test_filter_by_severity(self):
        pack = RulePack(
            name="p",
            version="1.0",
            domain="cpt",
            rules=[
                _rule("A", Severity.CRITICAL),
                _rule("B", Severity.WARNING),
                _rule("C", Severity.CRITICAL),
            ],
        )
        crit = pack.filter(severity=Severity.CRITICAL)
        assert [r.id for r in crit] == ["A", "C"]
        assert crit.name == "p:filtered"
        # source pack untouched
        assert len(pack) == 3

    def test_filter_by_category(self):
        pack = RulePack(
            name="p",
            version="1.0",
            domain="cpt",
            rules=[_rule("A", cat="depth"), _rule("B", cat="noise")],
        )
        assert [r.id for r in pack.filter(category="noise")] == ["B"]

    def test_filter_by_severity_and_category(self):
        pack = RulePack(
            name="p",
            version="1.0",
            domain="cpt",
            rules=[
                _rule("A", Severity.CRITICAL, cat="depth"),
                _rule("B", Severity.CRITICAL, cat="noise"),
                _rule("C", Severity.WARNING, cat="depth"),
            ],
        )
        result = pack.filter(severity="critical", category="depth")
        assert [r.id for r in result] == ["A"]

    def test_add_rule(self):
        pack = RulePack(name="p", version="1.0", domain="cpt")
        pack.add(_rule("A"))
        assert len(pack) == 1

    def test_add_duplicate_rejected(self):
        pack = RulePack(name="p", version="1.0", domain="cpt", rules=[_rule("A")])
        with pytest.raises(ValueError, match="already present"):
            pack.add(_rule("A"))


# ---------------------------------------------------------------------------
# @rule decorator
# ---------------------------------------------------------------------------


class TestRuleDecorator:
    def test_decorator_returns_rule(self):
        @rule(id="R1", title="Dummy", severity=Severity.INFO, category="basic")
        def my_check(target):
            return []

        assert isinstance(my_check, Rule)
        assert my_check.id == "R1"
        assert my_check.check.__name__ == "my_check" or callable(my_check.check)

    def test_decorator_accepts_string_severity(self):
        @rule(id="R1", title="Dummy", severity="critical", category="basic")
        def my_check(target):
            return []

        assert my_check.severity is Severity.CRITICAL

    def test_decorator_captures_parameters(self):
        @rule(
            id="R_tip",
            title="Tip",
            severity="info",
            category="termination",
            threshold_mpa=80.0,
            lookback=3,
        )
        def tip_check(target):
            return []

        assert tip_check.parameters == {"threshold_mpa": 80.0, "lookback": 3}

    def test_decorator_defaults_description_to_docstring(self):
        @rule(id="R1", title="Dummy", severity="info", category="basic")
        def my_check(target):
            """Checks nothing."""
            return []

        assert my_check.description == "Checks nothing."

    def test_decorator_rejects_non_callable(self):
        deco = rule(id="R1", title="t", severity="info", category="c")
        with pytest.raises(TypeError):
            deco("not-a-function")  # type: ignore[arg-type]

    def test_decorated_rule_runs_check(self):
        sentinel = object()

        @rule(id="R1", title="t", severity="info", category="c")
        def my_check(target):
            return [target]

        assert my_check.check(sentinel) == [sentinel]
