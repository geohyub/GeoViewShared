"""
geoview_cpt.scpt.first_break_picking
========================================
Automatic first-break picker + interval velocity helpers for SCPT.

First-break picker: STA/LTA characteristic function on the absolute
amplitude envelope. For each trace we compute

    STA[i] = mean(|x[i − n_sta + 1 .. i]|)
    LTA[i] = mean(|x[i − n_lta + 1 .. i]|)
    CF[i]  = STA[i] / max(LTA[i], ε)

and declare the first index where ``CF`` crosses the threshold (default
3.0) as the first-arrival sample. The function returns one
:class:`FirstBreakPick` per trace with a normalized confidence score
derived from the crossing margin.

Interval velocities:

    pseudo_interval_velocity   straight-line ray-path, one receiver
        V = ΔR / Δt
        where ΔR = √((z₂ − z_src)² + x²) − √((z₁ − z_src)² + x²)

    true_interval_velocity     ray-path at two adjacent receivers
        Assumes vertical propagation between receivers (common SCPT
        approximation at x ≪ z):
        V_int = (z₂ − z₁) / (t₂ − t₁)

Both are pure functions; callers can mix picked times with their own
geometry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

__all__ = [
    "DEFAULT_STA_WINDOW_MS",
    "DEFAULT_LTA_WINDOW_MS",
    "DEFAULT_THRESHOLD",
    "FirstBreakPick",
    "pick_first_breaks",
    "pseudo_interval_velocity",
    "true_interval_velocity",
]


DEFAULT_STA_WINDOW_MS: float = 2.0
DEFAULT_LTA_WINDOW_MS: float = 20.0
DEFAULT_THRESHOLD: float = 3.0


@dataclass(frozen=True)
class FirstBreakPick:
    """
    One auto-picked first break.

    Attributes:
        trace_index:    row index in the seismogram matrix.
        depth_m:        receiver depth (same length as the seismogram's
                        depth axis).
        time_ms:        picked first-arrival time (ms).
        sample_index:   integer index into the trace.
        confidence:     crossing margin ``0..1`` (clipped).
        trace_info:     open dict — STA/LTA window etc. for diagnostics.
    """

    trace_index: int
    depth_m: float
    time_ms: float
    sample_index: int
    confidence: float
    trace_info: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# STA/LTA picker
# ---------------------------------------------------------------------------


def _running_mean(x: np.ndarray, window: int) -> np.ndarray:
    """Causal running mean via cumulative sum (O(n))."""
    if window <= 1:
        return np.abs(x)
    cs = np.cumsum(np.abs(x), dtype=np.float64)
    out = np.empty_like(cs)
    out[:window] = cs[:window] / np.arange(1, window + 1)
    out[window:] = (cs[window:] - cs[:-window]) / window
    return out


def pick_first_breaks(
    seismogram: np.ndarray,
    depths_m: Sequence[float],
    sample_rate_hz: float,
    *,
    sta_window_ms: float = DEFAULT_STA_WINDOW_MS,
    lta_window_ms: float = DEFAULT_LTA_WINDOW_MS,
    threshold: float = DEFAULT_THRESHOLD,
    eps: float = 1e-9,
) -> list[FirstBreakPick]:
    """
    Pick first breaks on every trace of ``seismogram``.

    Args:
        seismogram:     2-D array shape ``(n_traces, n_samples)``.
        depths_m:       receiver depths (m), one per trace.
        sample_rate_hz: sampling rate in Hz.
        sta_window_ms:  short-term average window length (ms).
        lta_window_ms:  long-term average window length (ms).
        threshold:      STA/LTA ratio that declares a first break.
        eps:            LTA floor to avoid division by zero on the leading
                        samples.

    Returns:
        List of :class:`FirstBreakPick` — one per trace that crosses the
        threshold. Traces that never cross are omitted so downstream
        callers can count picks vs traces to audit picking quality.
    """
    data = np.asarray(seismogram, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError(f"seismogram must be 2-D, got shape {data.shape}")
    n_traces, n_samples = data.shape
    if len(depths_m) != n_traces:
        raise ValueError(
            f"depths_m length {len(depths_m)} != n_traces {n_traces}"
        )
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")

    dt_ms = 1000.0 / sample_rate_hz
    n_sta = max(1, int(round(sta_window_ms / dt_ms)))
    n_lta = max(n_sta + 1, int(round(lta_window_ms / dt_ms)))

    picks: list[FirstBreakPick] = []
    for i, depth in enumerate(depths_m):
        trace = data[i]
        sta = _running_mean(trace, n_sta)
        lta = _running_mean(trace, n_lta)
        cf = sta / np.maximum(lta, eps)
        # Require at least one full LTA window before we trust the ratio
        cf[:n_lta] = 0.0
        crossings = np.where(cf >= threshold)[0]
        if crossings.size == 0:
            continue
        idx = int(crossings[0])
        picks.append(
            FirstBreakPick(
                trace_index=i,
                depth_m=float(depth),
                time_ms=float(idx * dt_ms),
                sample_index=idx,
                confidence=float(min(1.0, cf[idx] / (threshold * 2.0))),
                trace_info={
                    "n_sta": n_sta,
                    "n_lta": n_lta,
                    "threshold": threshold,
                    "dt_ms": dt_ms,
                },
            )
        )
    return picks


# ---------------------------------------------------------------------------
# Interval velocities
# ---------------------------------------------------------------------------


def pseudo_interval_velocity(
    pick_a: FirstBreakPick,
    pick_b: FirstBreakPick,
    *,
    source_offset_x_m: float = 1.0,
    source_depth_m: float = 0.0,
) -> float:
    """
    Straight-ray pseudo-interval velocity between two receiver depths.

        V = ΔR / Δt
        R(z) = √((z − z_src)² + x²)

    Args:
        pick_a:            shallower pick (``pick_a.depth_m < pick_b.depth_m``).
        pick_b:            deeper pick.
        source_offset_x_m: horizontal source offset (m).
        source_depth_m:    source depth below sea surface (m). Defaults
                           to 0 — surface-source SCPT.

    Returns:
        Velocity in m/s. Returns 0 when the pair is degenerate
        (zero travel-time difference or identical depths).
    """
    if pick_b.depth_m <= pick_a.depth_m:
        return 0.0
    dt_s = (pick_b.time_ms - pick_a.time_ms) / 1000.0
    if dt_s <= 0:
        return 0.0
    r_a = np.hypot(pick_a.depth_m - source_depth_m, source_offset_x_m)
    r_b = np.hypot(pick_b.depth_m - source_depth_m, source_offset_x_m)
    return float((r_b - r_a) / dt_s)


def true_interval_velocity(
    pick_a: FirstBreakPick,
    pick_b: FirstBreakPick,
) -> float:
    """
    True interval velocity assuming vertical propagation between two
    adjacent receivers::

        V_int = (z_b − z_a) / (t_b − t_a)

    Valid when the source-to-receiver horizontal offset is small
    compared with depth (standard SCPT assumption).
    """
    dz = pick_b.depth_m - pick_a.depth_m
    dt_s = (pick_b.time_ms - pick_a.time_ms) / 1000.0
    if dt_s <= 0 or dz <= 0:
        return 0.0
    return float(dz / dt_s)
