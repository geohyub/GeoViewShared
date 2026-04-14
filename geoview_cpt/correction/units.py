"""
geoview_cpt.correction.units
================================
Unit-aware pressure helpers for the A2.5 derivation pipeline.

Wave 0 ``cpt_formulas_and_qc_catalog.md`` (commit 2f4280c ⚠️ block) makes
unit handling explicit: parsers ship ``qc`` in MPa and ``fs``/``u2`` in
kPa, so every formula must convert through :func:`to_mpa` /
:func:`to_kpa` rather than assume a fixed unit.

Why public symbols (no leading underscore): every deriver in
``geoview_cpt.derivation`` and any future custom expression in B3.10
needs the same converters. Hiding them behind ``_`` would just push
callers to ``from ._units import ...`` which is worse for IDE tooling.
"""
from __future__ import annotations

import numpy as np

from geoview_cpt.model import CPTChannel

__all__ = ["UnitError", "to_mpa", "to_kpa"]


_MPA_ALIASES = {"mpa", "MPa", "MPA"}
_KPA_ALIASES = {"kpa", "kPa", "KPA"}


class UnitError(ValueError):
    """Raised when a pressure :class:`CPTChannel` carries an unknown unit."""

    def __init__(self, channel_name: str, unit: str) -> None:
        super().__init__(
            f"unexpected unit {unit!r} on channel {channel_name!r}; "
            f"expected one of MPa / kPa"
        )
        self.channel_name = channel_name
        self.unit = unit


def to_mpa(channel: CPTChannel) -> np.ndarray:
    """Return ``channel.values`` in MPa, converting from kPa if needed."""
    unit = (channel.unit or "").strip()
    if unit in _MPA_ALIASES:
        return channel.values
    if unit in _KPA_ALIASES:
        return channel.values / 1000.0
    raise UnitError(channel.name, channel.unit)


def to_kpa(channel: CPTChannel) -> np.ndarray:
    """Return ``channel.values`` in kPa, converting from MPa if needed."""
    unit = (channel.unit or "").strip()
    if unit in _KPA_ALIASES:
        return channel.values
    if unit in _MPA_ALIASES:
        return channel.values * 1000.0
    raise UnitError(channel.name, channel.unit)
