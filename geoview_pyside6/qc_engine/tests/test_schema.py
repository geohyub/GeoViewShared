"""Tests for geoview_pyside6.qc_engine.schema — Step 3."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from geoview_pyside6.qc_engine.schema import RulePackSchema, RuleSchema


def _minimal_rule_dict(**overrides):
    base = {
        "id": "R1",
        "title": "Dummy",
        "severity": "info",
        "category": "basic",
        "check": "pkg.mod.fn",
    }
    base.update(overrides)
    return base


class TestRuleSchema:
    def test_minimal_valid(self):
        r = RuleSchema.model_validate(_minimal_rule_dict())
        assert r.id == "R1"
        assert r.parameters == {}
        assert r.auto_fix is None

    def test_parameters_passthrough(self):
        r = RuleSchema.model_validate(
            _minimal_rule_dict(parameters={"threshold_mpa": 80.0})
        )
        assert r.parameters == {"threshold_mpa": 80.0}

    def test_severity_normalized_lowercase(self):
        r = RuleSchema.model_validate(_minimal_rule_dict(severity="WARNING"))
        assert r.severity == "warning"

    def test_unknown_severity_rejected(self):
        with pytest.raises(ValidationError):
            RuleSchema.model_validate(_minimal_rule_dict(severity="fatal"))

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            RuleSchema.model_validate(_minimal_rule_dict(extra_field=1))

    def test_empty_id_rejected(self):
        with pytest.raises(ValidationError):
            RuleSchema.model_validate(_minimal_rule_dict(id=""))

    def test_empty_check_rejected(self):
        with pytest.raises(ValidationError):
            RuleSchema.model_validate(_minimal_rule_dict(check=""))


class TestRulePackSchema:
    def test_empty_pack(self):
        p = RulePackSchema.model_validate(
            {"name": "p", "version": "1.0", "domain": "cpt"}
        )
        assert p.rules == []

    def test_pack_with_rules(self):
        p = RulePackSchema.model_validate(
            {
                "name": "p",
                "version": "1.0",
                "domain": "cpt",
                "rules": [_minimal_rule_dict(), _minimal_rule_dict(id="R2")],
            }
        )
        assert len(p.rules) == 2

    def test_duplicate_ids_rejected(self):
        with pytest.raises(ValidationError, match="duplicate rule id"):
            RulePackSchema.model_validate(
                {
                    "name": "p",
                    "version": "1.0",
                    "domain": "cpt",
                    "rules": [_minimal_rule_dict(), _minimal_rule_dict()],
                }
            )

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            RulePackSchema.model_validate({"name": "", "version": "1.0", "domain": "cpt"})
