"""Tests for geoview_pyside6.qc_engine.loader — Step 3."""
from __future__ import annotations

from pathlib import Path

import pytest

from geoview_pyside6.qc_engine.loader import (
    LoaderError,
    RuleCheckRegistry,
    load_yaml,
)
from geoview_pyside6.qc_engine.rules import RulePack, Severity


def _check_pass(target):
    return []


def _write_yaml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "pack.yaml"
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# RuleCheckRegistry
# ---------------------------------------------------------------------------


class TestRuleCheckRegistry:
    def test_register_and_get(self):
        reg = RuleCheckRegistry()
        reg.register("depth_monotonic", _check_pass)
        assert reg.get("depth_monotonic") is _check_pass
        assert "depth_monotonic" in reg
        assert len(reg) == 1

    def test_register_rejects_duplicate(self):
        reg = RuleCheckRegistry()
        reg.register("c", _check_pass)
        with pytest.raises(ValueError, match="already registered"):
            reg.register("c", _check_pass)

    def test_register_rejects_non_callable(self):
        reg = RuleCheckRegistry()
        with pytest.raises(TypeError):
            reg.register("c", "not-a-fn")  # type: ignore[arg-type]

    def test_register_rejects_empty_key(self):
        reg = RuleCheckRegistry()
        with pytest.raises(ValueError):
            reg.register("", _check_pass)

    def test_get_missing_returns_none(self):
        assert RuleCheckRegistry().get("nope") is None


# ---------------------------------------------------------------------------
# load_yaml
# ---------------------------------------------------------------------------


VALID_YAML = """\
name: cpt_base
version: "1.0"
domain: cpt
description: "Basic CPT quality checks"
rules:
  - id: R_depth_monotonic
    title: "Depth must be monotonically increasing"
    severity: critical
    category: depth_quality
    check: depth_monotonic
    parameters:
      epsilon: 0.001
  - id: R_tip_max
    title: "Tip resistance max limit reached"
    severity: info
    category: termination_event
    check: tip_max
    parameters:
      threshold_mpa: 80.0
"""


class TestLoadYaml:
    def test_registry_resolution_end_to_end(self, tmp_path):
        path = _write_yaml(tmp_path, VALID_YAML)
        reg = RuleCheckRegistry()
        reg.register("depth_monotonic", _check_pass)
        reg.register("tip_max", _check_pass)

        pack = load_yaml(path, registry=reg, allow_import=False)

        assert isinstance(pack, RulePack)
        assert pack.name == "cpt_base"
        assert pack.version == "1.0"
        assert pack.domain == "cpt"
        assert len(pack) == 2
        r1 = pack.get("R_depth_monotonic")
        assert r1.severity is Severity.CRITICAL
        assert r1.parameters == {"epsilon": 0.001}
        assert r1.check is _check_pass

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(LoaderError, match="not found"):
            load_yaml(tmp_path / "nope.yaml")

    def test_empty_file_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "")
        with pytest.raises(LoaderError, match="empty"):
            load_yaml(p)

    def test_non_mapping_root_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "- just\n- a\n- list\n")
        with pytest.raises(LoaderError, match="mapping"):
            load_yaml(p)

    def test_invalid_yaml_raises(self, tmp_path):
        p = _write_yaml(tmp_path, "name: p\n  bad-indent: true\n :\n")
        with pytest.raises(LoaderError):
            load_yaml(p)

    def test_locked_registry_rejects_unknown_check(self, tmp_path):
        path = _write_yaml(tmp_path, VALID_YAML)
        reg = RuleCheckRegistry()
        reg.register("depth_monotonic", _check_pass)
        # tip_max intentionally missing
        with pytest.raises(LoaderError, match="tip_max"):
            load_yaml(path, registry=reg, allow_import=False)

    def test_dotted_import_fallback(self, tmp_path):
        body = """\
name: p
version: "1.0"
domain: cpt
rules:
  - id: R1
    title: "Dummy"
    severity: info
    category: basic
    check: geoview_pyside6.qc_engine.tests.test_loader._check_pass
"""
        path = _write_yaml(tmp_path, body)
        pack = load_yaml(path)  # allow_import default True
        assert pack.get("R1").check is _check_pass

    def test_dotted_import_unknown_module_raises(self, tmp_path):
        body = """\
name: p
version: "1.0"
domain: cpt
rules:
  - id: R1
    title: "Dummy"
    severity: info
    category: basic
    check: no_such_module.nope
"""
        path = _write_yaml(tmp_path, body)
        with pytest.raises(LoaderError, match="cannot import"):
            load_yaml(path)

    def test_schema_violation_propagates(self, tmp_path):
        body = """\
name: p
version: "1.0"
domain: cpt
rules:
  - id: R1
    title: "Dummy"
    severity: fatal
    category: basic
    check: x
"""
        path = _write_yaml(tmp_path, body)
        # ValidationError (not LoaderError) — schema layer
        with pytest.raises(Exception):
            load_yaml(path)
