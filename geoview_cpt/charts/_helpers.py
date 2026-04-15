"""
geoview_cpt.charts._helpers
================================
Shared utilities for the A2.7 chart builders.

Keeps the per-chart modules focused on layout — extraction of channel
arrays, derived-channel lookup, and common axis formatting all live
here.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from geoview_cpt.correction.units import UnitError, to_kpa, to_mpa
from geoview_cpt.model import CPTChannel, CPTSounding

__all__ = [
    "MissingChannelError",
    "get_raw",
    "get_derived",
    "get_either",
    "depth_array",
    "to_mpa_array",
    "to_kpa_array",
    "format_depth_axis",
    "branding_footer",
]


class MissingChannelError(KeyError):
    """Raised when a chart builder cannot find a required channel."""


def get_raw(sounding: CPTSounding, name: str) -> CPTChannel:
    ch = sounding.channels.get(name)
    if ch is None:
        raise MissingChannelError(
            f"raw channel {name!r} missing on sounding {sounding.name!r}"
        )
    return ch


def get_derived(sounding: CPTSounding, name: str) -> CPTChannel:
    ch = sounding.derived.get(name)
    if ch is None:
        raise MissingChannelError(
            f"derived channel {name!r} missing on sounding {sounding.name!r}"
        )
    return ch


def get_either(sounding: CPTSounding, name: str) -> CPTChannel:
    ch = sounding.channels.get(name) or sounding.derived.get(name)
    if ch is None:
        raise MissingChannelError(
            f"channel {name!r} missing from raw or derived on "
            f"sounding {sounding.name!r}"
        )
    return ch


def depth_array(sounding: CPTSounding) -> np.ndarray:
    return get_raw(sounding, "depth").values


def to_mpa_array(channel: CPTChannel) -> np.ndarray:
    """Unit-safe conversion helper that swallows UnitError with a clearer message."""
    try:
        return to_mpa(channel)
    except UnitError as exc:
        raise MissingChannelError(
            f"cannot convert channel {channel.name!r} to MPa: {exc}"
        ) from exc


def to_kpa_array(channel: CPTChannel) -> np.ndarray:
    try:
        return to_kpa(channel)
    except UnitError as exc:
        raise MissingChannelError(
            f"cannot convert channel {channel.name!r} to kPa: {exc}"
        ) from exc


def format_depth_axis(ax: Any, *, invert: bool = True) -> None:
    """Standard depth-axis treatment: invert, label ``Depth (m)``, grid."""
    if invert:
        ax.invert_yaxis()
    ax.set_ylabel("Depth (m)")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.7)


def branding_footer(
    project_name: str,
    *,
    partner_brand: str = "Geoview",
    partner_url: str = "http://www.geoview.co.kr",
) -> str:
    """One-line footer string rendered at the bottom of deliverable charts."""
    return f"{project_name}  ·  {partner_brand}  ·  {partner_url}"
