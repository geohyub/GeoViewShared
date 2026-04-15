"""
geoview_cpt.seabed.landing_detection
========================================
Multi-signal seabed landing detection (Wave 0 R5 relaxed rule).

The detector walks the depth profile and evaluates four independent
conditions at every sample:

    C1 — qc excursion      qc ≥ qc_trigger_mpa
    C2 — depth reached      depth ≥ min_search_depth_m
    C3 — u₂ jump            |u₂ − u₂₀| ≥ u2_trigger_kpa
    C4 — altimeter contact  altimeter ≤ altimeter_trigger_m
                            (skipped when the altimeter channel is absent)

"Landing" is declared at the first sample where **at least k of the
available conditions hold** (``k = 3`` default). Missing channels
reduce both numerator and denominator: with no altimeter we look for
``3-of-3`` instead of ``3-of-4``.

The routine always returns a :class:`LandingResult`; when nothing
qualifies ``detected`` is False and the caller should fall back to a
manual depth override (Phase B UI).

Parameters live on a small :class:`LandingRules` dataclass so a
project can override them from a YAML profile without mutating the
detector internals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from geoview_cpt.model import CPTSounding

__all__ = [
    "LandingCondition",
    "LandingResult",
    "LandingRules",
    "DEFAULT_LANDING_RULES",
    "detect_seabed_landing",
]


# ---------------------------------------------------------------------------
# Rule + result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LandingRules:
    """Thresholds for the 4-condition detector."""

    qc_trigger_mpa: float = 0.3
    u2_trigger_kpa: float = 5.0
    altimeter_trigger_m: float = 0.5
    min_search_depth_m: float = 0.02
    k_required: int = 3
    u2_baseline_samples: int = 5


DEFAULT_LANDING_RULES = LandingRules()


@dataclass
class LandingCondition:
    """One condition's first-true sample index (or None if never satisfied)."""

    name: str
    available: bool
    first_true_index: int | None
    trace: dict = field(default_factory=dict)


@dataclass
class LandingResult:
    """
    Outcome of :func:`detect_seabed_landing`.

    Attributes:
        detected:        True when at least ``k`` conditions fire on the
                         same sample.
        depth_m:         depth at the landing sample (or ``None``).
        index:           0-based sample index (or ``None``).
        conditions:      per-condition trace (see :class:`LandingCondition`).
        k_required:      k taken from the active :class:`LandingRules`.
        k_satisfied:     number of conditions satisfied at the landing
                         sample (0 when not detected).
        available_count: number of channels actually available.
    """

    detected: bool
    depth_m: float | None
    index: int | None
    conditions: list[LandingCondition]
    k_required: int
    k_satisfied: int
    available_count: int


# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------


def detect_seabed_landing(
    sounding: "CPTSounding",
    *,
    rules: LandingRules = DEFAULT_LANDING_RULES,
) -> LandingResult:
    """
    Scan ``sounding`` for the first depth where ``k_required`` landing
    conditions fire simultaneously.

    Required channel:
        ``depth`` — mandatory; returns an empty result when missing.

    Optional channels (any that are present contribute a condition):
        ``qc``         (MPa) — tip resistance excursion
        ``u2``         (MPa/kPa, unit honoured) — pore pressure jump
        ``altimeter``  (m) — seabed frame altimeter reading
    """
    depth_ch = sounding.channels.get("depth")
    if depth_ch is None or depth_ch.values.size == 0:
        return LandingResult(
            detected=False,
            depth_m=None,
            index=None,
            conditions=[],
            k_required=rules.k_required,
            k_satisfied=0,
            available_count=0,
        )
    depth = np.asarray(depth_ch.values, dtype=np.float64)

    # --- per-condition masks ------------------------------------------------

    conditions: list[LandingCondition] = []
    masks: list[np.ndarray] = []

    # C2 — depth reached (always available if depth exists)
    c2_mask = depth >= rules.min_search_depth_m
    conditions.append(
        LandingCondition(
            name="depth_reached",
            available=True,
            first_true_index=_first_true(c2_mask),
            trace={"min_search_depth_m": rules.min_search_depth_m},
        )
    )
    masks.append(c2_mask)

    # C1 — qc excursion
    qc_ch = sounding.channels.get("qc")
    if qc_ch is not None and qc_ch.values.size == depth.size:
        qc_mpa = _to_mpa(qc_ch)
        c1_mask = qc_mpa >= rules.qc_trigger_mpa
        conditions.append(
            LandingCondition(
                name="qc_excursion",
                available=True,
                first_true_index=_first_true(c1_mask),
                trace={"qc_trigger_mpa": rules.qc_trigger_mpa},
            )
        )
        masks.append(c1_mask)
    else:
        conditions.append(
            LandingCondition(name="qc_excursion", available=False, first_true_index=None)
        )

    # C3 — u2 jump vs baseline of first N samples
    u2_ch = sounding.channels.get("u2")
    if u2_ch is not None and u2_ch.values.size == depth.size:
        u2_kpa = _to_kpa(u2_ch)
        n_base = min(rules.u2_baseline_samples, max(1, u2_kpa.size // 10))
        baseline = float(np.nanmean(u2_kpa[:n_base])) if u2_kpa.size else 0.0
        c3_mask = np.abs(u2_kpa - baseline) >= rules.u2_trigger_kpa
        conditions.append(
            LandingCondition(
                name="u2_jump",
                available=True,
                first_true_index=_first_true(c3_mask),
                trace={
                    "u2_trigger_kpa": rules.u2_trigger_kpa,
                    "baseline_kpa": baseline,
                },
            )
        )
        masks.append(c3_mask)
    else:
        conditions.append(
            LandingCondition(name="u2_jump", available=False, first_true_index=None)
        )

    # C4 — altimeter contact
    alt_ch = sounding.channels.get("altimeter")
    if alt_ch is not None and alt_ch.values.size == depth.size:
        alt_m = np.asarray(alt_ch.values, dtype=np.float64)
        c4_mask = alt_m <= rules.altimeter_trigger_m
        conditions.append(
            LandingCondition(
                name="altimeter_contact",
                available=True,
                first_true_index=_first_true(c4_mask),
                trace={"altimeter_trigger_m": rules.altimeter_trigger_m},
            )
        )
        masks.append(c4_mask)
    else:
        conditions.append(
            LandingCondition(name="altimeter_contact", available=False, first_true_index=None)
        )

    # --- k-of-N aggregation ------------------------------------------------

    available_count = len(masks)
    if available_count == 0:
        return LandingResult(
            detected=False,
            depth_m=None,
            index=None,
            conditions=conditions,
            k_required=rules.k_required,
            k_satisfied=0,
            available_count=0,
        )

    k_required = min(rules.k_required, available_count)

    stacked = np.stack(masks, axis=0)   # (n_conditions, n_samples)
    hits_per_sample = stacked.sum(axis=0)
    qualifying = np.where(hits_per_sample >= k_required)[0]
    if qualifying.size == 0:
        return LandingResult(
            detected=False,
            depth_m=None,
            index=None,
            conditions=conditions,
            k_required=k_required,
            k_satisfied=int(hits_per_sample.max()) if hits_per_sample.size else 0,
            available_count=available_count,
        )

    idx = int(qualifying[0])
    return LandingResult(
        detected=True,
        depth_m=float(depth[idx]),
        index=idx,
        conditions=conditions,
        k_required=k_required,
        k_satisfied=int(hits_per_sample[idx]),
        available_count=available_count,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _first_true(mask: np.ndarray) -> int | None:
    if mask.size == 0:
        return None
    hits = np.where(mask)[0]
    return int(hits[0]) if hits.size else None


def _to_mpa(ch) -> np.ndarray:
    unit = (ch.unit or "").strip()
    if unit in {"MPa", "mpa", "MPA"}:
        return np.asarray(ch.values, dtype=np.float64)
    if unit in {"kPa", "kpa", "KPA"}:
        return np.asarray(ch.values, dtype=np.float64) / 1000.0
    return np.asarray(ch.values, dtype=np.float64)


def _to_kpa(ch) -> np.ndarray:
    unit = (ch.unit or "").strip()
    if unit in {"kPa", "kpa", "KPA"}:
        return np.asarray(ch.values, dtype=np.float64)
    if unit in {"MPa", "mpa", "MPA"}:
        return np.asarray(ch.values, dtype=np.float64) * 1000.0
    return np.asarray(ch.values, dtype=np.float64)
