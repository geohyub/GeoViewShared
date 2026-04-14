"""End-to-end integration test for qc_engine sample pack — Step 5."""
from __future__ import annotations

from pathlib import Path

from geoview_common.qc.common.models import QCDomain, QCStatus

from geoview_pyside6.qc_engine.loader import RuleCheckRegistry, load_yaml
from geoview_pyside6.qc_engine.rules import RulePack, Severity
from geoview_pyside6.qc_engine.runner import RuleRunner
from geoview_pyside6.qc_engine.samples.builtin_rules import (
    build_sample_pack,
    depth_monotonic,
    spike_detection,
    tip_max_reached,
)

SAMPLE_YAML = (
    Path(__file__).resolve().parent.parent / "samples" / "sample_pack.yaml"
)


def _clean_sounding() -> dict:
    return {
        "depths": [0.0, 0.5, 1.0, 1.5, 2.0],
        "qc_mpa": [1.0, 1.2, 1.4, 1.5, 1.6],
    }


def _broken_sounding() -> dict:
    return {
        # depth regresses at index 2
        "depths": [0.0, 0.5, 0.4, 1.0, 1.5],
        # spike between index 1 and 2, and tip sat at the end
        "qc_mpa": [1.0, 1.2, 50.0, 55.0, 80.0],
    }


# ---------------------------------------------------------------------------
# Code-first pack
# ---------------------------------------------------------------------------


class TestCodeFirstPack:
    def test_clean_data_scores_perfect(self):
        pack = build_sample_pack()
        result = RuleRunner(pack=pack).run(
            _clean_sounding(), domain=QCDomain.CPT, file_name="clean.cpt"
        )
        assert result.total_score == 100.0
        assert result.status is QCStatus.PASS
        assert result.issues == []

    def test_broken_data_flags_all_three_rules(self):
        pack = build_sample_pack()
        result = RuleRunner(pack=pack).run(
            _broken_sounding(), domain=QCDomain.CPT, file_name="bad.cpt"
        )
        # depth_monotonic: FAIL, spike_detection: WARN, tip_max_reached: info PASS
        ids_by_status = {s.stage_name: s.status for s in result.stages}
        assert ids_by_status["R_depth_monotonic"] is QCStatus.FAIL
        assert ids_by_status["R_spike_detection"] is QCStatus.WARN
        assert ids_by_status["R_tip_max_reached"] is QCStatus.PASS  # info-only
        assert any(i.severity == "critical" for i in result.issues)
        assert any(i.severity == "warning" for i in result.issues)
        assert any(i.severity == "info" for i in result.issues)

    def test_rules_are_rule_instances(self):
        # @rule decorator should produce Rule, not plain function
        from geoview_pyside6.qc_engine.rules import Rule

        assert isinstance(depth_monotonic, Rule)
        assert isinstance(tip_max_reached, Rule)
        assert isinstance(spike_detection, Rule)
        assert depth_monotonic.severity is Severity.CRITICAL
        assert depth_monotonic.parameters == {"epsilon": 0.001}


# ---------------------------------------------------------------------------
# Data-first pack (YAML)
# ---------------------------------------------------------------------------


class TestDataFirstPack:
    def _registry(self) -> RuleCheckRegistry:
        reg = RuleCheckRegistry()
        reg.register("depth_monotonic", depth_monotonic.check)
        reg.register("tip_max_reached", tip_max_reached.check)
        reg.register("spike_detection", spike_detection.check)
        return reg

    def test_yaml_loads_to_rulepack(self):
        pack = load_yaml(SAMPLE_YAML, registry=self._registry(), allow_import=False)
        assert isinstance(pack, RulePack)
        assert pack.name == "sample_pack"
        assert len(pack) == 3

    def test_yaml_pack_runs_against_target(self):
        pack = load_yaml(SAMPLE_YAML, registry=self._registry(), allow_import=False)
        result = RuleRunner(pack=pack).run(
            _broken_sounding(), domain=QCDomain.CPT, file_name="bad.cpt"
        )
        # Same shape as code-first — data-first / code-first parity
        ids_by_status = {s.stage_name: s.status for s in result.stages}
        assert ids_by_status["R_depth_monotonic"] is QCStatus.FAIL
        assert ids_by_status["R_spike_detection"] is QCStatus.WARN

    def test_code_first_and_data_first_match(self):
        code_pack = build_sample_pack()
        data_pack = load_yaml(
            SAMPLE_YAML, registry=self._registry(), allow_import=False
        )
        target = _broken_sounding()
        a = RuleRunner(pack=code_pack).run(
            target, domain=QCDomain.CPT, file_name="x"
        )
        b = RuleRunner(pack=data_pack).run(
            target, domain=QCDomain.CPT, file_name="x"
        )
        assert a.total_score == b.total_score
        assert a.extra["rule_passed"] == b.extra["rule_passed"]
