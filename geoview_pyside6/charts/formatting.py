"""
geoview_pyside6.charts.formatting
================================
Number formatting for charts, readouts, and reports.

Rules (feedback_number_format.md):
 - **Thousands comma separator** by default.
 - **No scientific notation** unless the caller opts in — raw
   ``f"{v:.2e}"`` output is a UX failure.
 - Integers print without trailing zeros; floats respect ``decimals``.
 - ``NaN`` / ``inf`` print as ``"NaN"`` / ``"∞"`` so they never leak
   raw Python repr into a chart label.

``format_axis_label`` is a thin wrapper used by :class:`ChartAxisItem`
to render tick strings consistently across all GeoView charts.
"""
from __future__ import annotations

import math
from typing import Iterable

__all__ = [
    "NumberFormatError",
    "format_number",
    "format_axis_label",
]


class NumberFormatError(ValueError):
    """Raised when a value cannot be formatted (e.g. complex)."""


def _is_intlike(v: float) -> bool:
    return math.isfinite(v) and float(v).is_integer()


def format_number(
    value: float | int,
    *,
    decimals: int = 2,
    allow_scientific: bool = False,
    unit: str = "",
) -> str:
    """
    Return a human-readable string for ``value``.

    Examples::

        format_number(1234567)          -> "1,234,567"
        format_number(1234.5)           -> "1,234.50"
        format_number(1234.5, decimals=1) -> "1,234.5"
        format_number(0.000123)         -> "0.00"        (truncates by default)
        format_number(0.000123, decimals=6) -> "0.000123"
        format_number(12.5, unit="m")   -> "12.50 m"

    Args:
        value:            numeric input (int or float).
        decimals:         digits after the decimal point. Ignored when the
                          value is integer-like.
        allow_scientific: if True, values with absolute magnitude < 1e-4 or
                          ≥ 1e12 fall back to ``{:.{decimals}e}``. Off by
                          default — call sites must opt in.
        unit:             optional trailing unit appended with a space.
    """
    if isinstance(value, bool):
        raise NumberFormatError("bool is not a valid numeric input")
    if not isinstance(value, (int, float)):
        raise NumberFormatError(
            f"expected int or float, got {type(value).__name__}"
        )
    if decimals < 0:
        raise NumberFormatError(f"decimals must be >= 0, got {decimals}")

    if isinstance(value, float):
        if math.isnan(value):
            return _with_unit("NaN", unit)
        if math.isinf(value):
            return _with_unit("-∞" if value < 0 else "∞", unit)

    if allow_scientific and isinstance(value, float) and value != 0.0:
        mag = abs(value)
        if mag < 1e-4 or mag >= 1e12:
            return _with_unit(f"{value:.{decimals}e}", unit)

    if isinstance(value, int) or _is_intlike(value):
        return _with_unit(f"{int(value):,}", unit)

    return _with_unit(f"{value:,.{decimals}f}", unit)


def _with_unit(body: str, unit: str) -> str:
    return f"{body} {unit}".rstrip() if unit else body


def format_axis_label(values: Iterable[float], *, decimals: int = 2) -> list[str]:
    """Format a sequence of tick values for a chart axis."""
    return [format_number(v, decimals=decimals) for v in values]
