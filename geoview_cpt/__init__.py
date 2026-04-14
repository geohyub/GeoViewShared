"""
geoview_cpt
================================
Cone Penetration Test domain package (Phase A-2).

This package owns every CPT-specific symbol — parsers, canonical model,
QC rules, derived channels, chart builders, interpretation engines.
``geoview_pyside6/`` and ``geoview_common/`` stay CPT-agnostic.

Public sub-packages (populated as Phase A-2 epics land):

    model/       canonical dataclasses (A2.1)
    parsers/     format readers (CPeT-IT v30 — A2.0, Excel YW/JAKO/야장,
                 AGS4, GEF, CSV)
    qc_checks/   domain check functions consumed by geoview_pyside6.qc_engine
                 (A2.6)
    derivation/  correction + derivation formulas (A2.5)
    charts/      CPT-specific chart builders (A2.7)
    ...
"""
from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
