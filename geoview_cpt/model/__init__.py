"""
geoview_cpt.model
================================
Canonical CPT domain dataclasses.

A2.0 introduces the minimum shape the CPeT-IT reader needs
(:class:`CPTProject`, :class:`CPTSounding`). A2.1 will extend these with
:class:`CPTHeader`, :class:`CPTChannel`, derived-channel slots, AGS4
source preservation, and event streams.
"""
from __future__ import annotations

from geoview_cpt.model.project import CPTProject, CPTSounding

__all__ = ["CPTProject", "CPTSounding"]
