"""
geoview_cpt.synthesis
================================
Multi-source layer-property reconciliation (Phase A-2 A2.9).

Combines CPT-derived channels, lab samples, physical logging (density
and PS-wave), in-situ LLT results, adjacent SPT values, and narrative
annotations into a single :class:`SynthesizedValue` per property per
stratum. Every downstream consumer (Kingdom AGS4 ``GEOL`` export,
B3.11 CPT+Lab composite viewer, report writers) reads
``StratumLayer.synthesized_properties`` instead of re-implementing the
priority logic.

Public API:

    SynthesizedValue        frozen dataclass (value, source, confidence,
                             trace)
    PropertySource          Literal alias for the seven priority
                             sources + ``"missing"``
    PropertyConfidence      Literal alias for ``"high" / "medium" /
                             "low" / "unknown"``
    LayerSynthesizer        orchestrator — feed it the source list,
                             call :meth:`synthesize` to populate each
                             :class:`StratumLayer.synthesized_properties`
"""
from __future__ import annotations

from geoview_cpt.synthesis.layer_properties import (
    LayerSynthesizer,
    PropertyConfidence,
    PropertySource,
    SynthesizedValue,
)

__all__ = [
    "SynthesizedValue",
    "PropertySource",
    "PropertyConfidence",
    "LayerSynthesizer",
]
