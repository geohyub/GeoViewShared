"""
geoview_cpt.qc_rules
================================
CPT domain QC rule pack (Phase A-2 A2.6).

Declarative rule definitions consumed by
:mod:`geoview_pyside6.qc_engine` — 14 rules covering the four Wave 0
categories:

    drift           (5)   zero-drift checks for tip, sleeve, pore,
                          drill-string, and aggregate class downgrade
    termination     (4)   sensor limit reached + penetration per push
    basic_quality   (5)   depth monotonic, spike detection, saturation,
                          u₂ response, inclination limit

The canonical pack ships as YAML (``cpt_base.yaml``) so operators can
tune thresholds without touching Python. Check functions live in
:mod:`geoview_cpt.qc_rules.checks` and are referenced from YAML by
dotted path — A1.2 loader resolves the imports at load time.

Helper :func:`load_cpt_base_pack` returns the pack ready-to-run against
a :class:`geoview_cpt.model.CPTSounding` (via
``RuleRunner(pack=...).run(sounding, domain=QCDomain.CPT, ...)``).
"""
from __future__ import annotations

from pathlib import Path

from geoview_cpt.qc_rules.checks import (
    CHECK_REGISTRY,
    class_downgrade,
    depth_monotonic,
    drift_drill_string_class1,
    drift_pore_class1,
    drift_sleeve_class1,
    drift_tip_class1,
    inclination_exceed,
    penetration_per_push,
    pore_max_reached,
    sensor_saturation,
    sleeve_max_reached,
    spike_detection,
    tip_max_reached,
    u2_response,
)

__all__ = [
    "CPT_BASE_YAML_PATH",
    "CHECK_REGISTRY",
    "load_cpt_base_pack",
    # individual checks (for direct import in tests or manual use)
    "depth_monotonic",
    "spike_detection",
    "sensor_saturation",
    "u2_response",
    "inclination_exceed",
    "tip_max_reached",
    "sleeve_max_reached",
    "pore_max_reached",
    "penetration_per_push",
    "drift_tip_class1",
    "drift_sleeve_class1",
    "drift_pore_class1",
    "drift_drill_string_class1",
    "class_downgrade",
]


CPT_BASE_YAML_PATH: Path = Path(__file__).resolve().parent / "cpt_base.yaml"


def load_cpt_base_pack():
    """
    Load the canonical 14-rule CPT base pack as a
    :class:`geoview_pyside6.qc_engine.RulePack`.

    Returns a fresh instance each call so tests can mutate without
    affecting other suites.
    """
    from geoview_pyside6.qc_engine.loader import RuleCheckRegistry, load_yaml

    registry = RuleCheckRegistry()
    for name, fn in CHECK_REGISTRY.items():
        registry.register(name, fn)
    return load_yaml(CPT_BASE_YAML_PATH, registry=registry, allow_import=False)
