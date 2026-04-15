"""
End-to-end YAML-load + RulePack integration — A2.6.

Loads ``cpt_base.yaml`` through the A1.2 loader, runs the 14-rule pack
against a synthetic clean CPTSounding, and asserts the QCResult shape
and per-stage bookkeeping.
"""
from __future__ import annotations

from datetime import datetime

import numpy as np
import pytest

from geoview_common.qc.common.models import QCDomain, QCStatus
from geoview_cpt.model import AcquisitionEvent, CPTChannel, CPTHeader, CPTSounding
from geoview_cpt.qc_rules import CPT_BASE_YAML_PATH, load_cpt_base_pack
from geoview_pyside6.qc_engine.runner import RuleRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clean_sounding() -> CPTSounding:
    s = CPTSounding(handle=1, element_tag="1", name="CPT-SYNTH")
    s.header = CPTHeader(sounding_id="CPT-SYNTH")
    depth = np.linspace(0.0, 20.0, 200)
    s.channels = {
        "depth": CPTChannel(name="depth", unit="m", values=depth),
        "qc":    CPTChannel(name="qc",    unit="MPa", values=np.linspace(0.5, 15.0, 200)),
        "fs":    CPTChannel(name="fs",    unit="kPa", values=np.linspace(5.0, 100.0, 200)),
        "u2":    CPTChannel(name="u2",    unit="kPa", values=np.linspace(10.0, 200.0, 200)),
        "incl":  CPTChannel(name="incl",  unit="deg", values=np.zeros(200) + 0.5),
    }
    return s


def _broken_sounding() -> CPTSounding:
    s = _clean_sounding()
    # Introduce a depth regression
    s.channels["depth"].values[100] = s.channels["depth"].values[99] - 0.5
    # And a huge qc spike
    s.channels["qc"].values[50] = 80.5
    return s


# ---------------------------------------------------------------------------
# Pack load + structure
# ---------------------------------------------------------------------------


class TestLoadPack:
    def test_yaml_exists(self):
        assert CPT_BASE_YAML_PATH.exists()

    def test_loads_14_rules(self):
        pack = load_cpt_base_pack()
        assert pack.name == "cpt_base"
        assert pack.version == "1.0"
        assert pack.domain == "cpt"
        assert len(pack) == 14

    def test_all_rule_ids_unique(self):
        pack = load_cpt_base_pack()
        ids = [r.id for r in pack]
        assert len(set(ids)) == 14

    def test_expected_categories(self):
        pack = load_cpt_base_pack()
        cats = {r.category for r in pack}
        assert cats == {"basic_quality", "termination_event", "drift"}

    def test_pack_filter_by_category(self):
        pack = load_cpt_base_pack()
        assert len(pack.filter(category="basic_quality")) == 5
        assert len(pack.filter(category="termination_event")) == 4
        assert len(pack.filter(category="drift")) == 5


# ---------------------------------------------------------------------------
# Runner integration
# ---------------------------------------------------------------------------


class TestRunnerWithCleanSounding:
    def test_runs_and_returns_qcresult(self):
        pack = load_cpt_base_pack()
        runner = RuleRunner(pack=pack)
        result = runner.run(
            _clean_sounding(), domain=QCDomain.CPT, file_name="synth.cpt"
        )
        assert result.domain is QCDomain.CPT
        assert len(result.stages) == 14
        assert result.extra["rule_total"] == 14

    def test_status_reflects_info_only(self):
        """All info/stub → total score ~100 (pass ratio high)."""
        pack = load_cpt_base_pack()
        result = RuleRunner(pack=pack).run(
            _clean_sounding(), domain=QCDomain.CPT, file_name="synth.cpt"
        )
        # Info-only issues don't fail a stage
        fail_count = sum(1 for s in result.stages if s.status is QCStatus.FAIL)
        assert fail_count == 0


class TestRunnerWithBrokenSounding:
    def test_depth_critical_fires(self):
        pack = load_cpt_base_pack()
        result = RuleRunner(pack=pack).run(
            _broken_sounding(), domain=QCDomain.CPT, file_name="bad.cpt"
        )
        depth_stage = next(s for s in result.stages if s.stage_name == "R_depth_monotonic")
        assert depth_stage.status is QCStatus.FAIL
        assert any(i.severity == "critical" for i in depth_stage.issues)

    def test_spike_warning_fires(self):
        pack = load_cpt_base_pack()
        result = RuleRunner(pack=pack).run(
            _broken_sounding(), domain=QCDomain.CPT, file_name="bad.cpt"
        )
        spike_stage = next(s for s in result.stages if s.stage_name == "R_spike_detection")
        assert spike_stage.status is QCStatus.WARN or spike_stage.status is QCStatus.FAIL


class TestDriftWithEvents:
    def test_drift_stubs_emit_info_without_events(self):
        pack = load_cpt_base_pack()
        result = RuleRunner(pack=pack).run(
            _clean_sounding(), domain=QCDomain.CPT, file_name="synth.cpt"
        )
        # The 5 drift rules emit info-only issues about missing events
        drift_stages = [s for s in result.stages
                        if any("events" in i.description.lower() for i in s.issues)]
        assert len(drift_stages) == 5

    def test_drift_checks_run_with_baseline_events(self):
        """With Deck+Post baseline events present the drift checks run
        the real first-vs-last comparison (Week 11 A2.6 backfill)."""
        pack = load_cpt_base_pack()
        s = _clean_sounding()
        s.header.events.append(
            AcquisitionEvent(timestamp=datetime(2026, 4, 15, 9), event_type="Deck Baseline")
        )
        s.header.events.append(
            AcquisitionEvent(timestamp=datetime(2026, 4, 15, 10), event_type="Post Baseline")
        )
        result = RuleRunner(pack=pack).run(
            s, domain=QCDomain.CPT, file_name="synth.cpt"
        )
        drift_ids = {
            "R_drift_tip_class1", "R_drift_sleeve_class1",
            "R_drift_pore_class1", "R_drift_drill_string_class1",
            "R_class_downgrade",
        }
        drift_stages = [stage for stage in result.stages if stage.stage_name in drift_ids]
        assert len(drift_stages) == 5
        # Backfill is live — none of the drift stages should still emit
        # the "info gap" stub message.
        for stage in drift_stages:
            for issue in stage.issues:
                assert "events empty" not in issue.description.lower()
