"""
geoview_gi
================================
Ground Investigation domain package (Phase A-2 Wave 0 3rd round).

Adjacent to :mod:`geoview_cpt`, this package holds everything that
isn't specific to cone penetration — boreholes, strata, SPT, lab
samples, Tables 27-33 classifiers, physical logging, in-situ tests,
and external lab parsers.

Both packages stay off of :mod:`geoview_pyside6` / :mod:`geoview_common`
so the shared UI layer remains CPT/GI-agnostic.

Public sub-modules (populated as A2 epics land):

    minimal_model      A2.19 — Borehole / StratumLayer / SPTTest / LabSample
    classification     A2.17 — Tables 27-33 classifiers
    physical_logging   A2.15 — density + PS-wave logs
    in_situ            A2.16 — LLT / Pressuremeter
    lab/sa_geolab      A2.18 — SA Geolab PDF summary parser
"""
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
