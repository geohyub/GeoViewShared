"""
geoview_cpt.derivation.strength
================================
Undrained shear strength + relative density — A2.5c.

Two formulas, two very different unit philosophies:

 - :func:`compute_su` is **unit-aware**. Eq 2 ``Su = (qt − σ_v0) / N_kt``
   evaluates in kPa regardless of the input channel units. Callers
   typically pass multiple ``N_kt`` values (15 and 30 is the Wave 0
   default pair) to plot both bounds on the same chart.

 - :func:`compute_dr_jamiolkowski` is **unit-hardcoded**. Eq 5 Dr uses
   a mixed-unit formula that the master plan (``cpt_formulas_and_qc_catalog.md``
   §2 Eq 5 ⚠️ block) pins explicitly: ``qc`` must arrive in MPa and
   ``σ'_v0`` in kPa. The Jamiolkowski 2001 constants (``141``, ``0.55``,
   ``2.9``) are only valid in that convention — running them through a
   unit-aware converter would silently break the numbers. The function
   therefore *refuses* any other unit with a ``ValueError`` so a
   miscalibrated caller fails loudly.
"""
from __future__ import annotations

from typing import Sequence, Union

import numpy as np

from geoview_cpt.correction.units import to_kpa
from geoview_cpt.model import CPTChannel

__all__ = ["compute_su", "compute_dr_jamiolkowski"]


# ---------------------------------------------------------------------------
# Eq 2 — Undrained shear strength
# ---------------------------------------------------------------------------


DEFAULT_NKT: tuple[float, ...] = (15.0, 30.0)
"""Wave 0 default Nkt pair — lower and upper bound curves on the Su plot."""


def compute_su(
    qt: CPTChannel,
    sigma_v0: CPTChannel,
    *,
    nkt: Union[float, Sequence[float]] = DEFAULT_NKT,
) -> dict[float, CPTChannel]:
    """
    Compute Su from net cone resistance.

        Su = (qt − σ_v0) / N_kt

    Args:
        qt:       corrected cone resistance (MPa or kPa accepted).
        sigma_v0: total vertical stress (MPa or kPa accepted).
        nkt:      single value or iterable of Nkt cone factors. Returns a
                  dict keyed by Nkt so callers can iterate for the plot.

    Returns:
        ``dict[float, CPTChannel]`` with one ``"Su_Nkt{N}"`` channel per
        requested N. Unit = ``"kPa"``.
    """
    qt_kpa = to_kpa(qt)
    sv0_kpa = to_kpa(sigma_v0)
    if qt_kpa.shape != sv0_kpa.shape:
        raise ValueError(
            f"qt / sigma_v0 shape mismatch: {qt_kpa.shape} vs {sv0_kpa.shape}"
        )

    if isinstance(nkt, (int, float)):
        nkt_list: list[float] = [float(nkt)]
    else:
        nkt_list = [float(n) for n in nkt]
    if not nkt_list:
        raise ValueError("nkt must be non-empty")
    for n in nkt_list:
        if n <= 0:
            raise ValueError(f"Nkt must be positive, got {n}")

    qnet = qt_kpa - sv0_kpa
    result: dict[float, CPTChannel] = {}
    for n in nkt_list:
        su = qnet / n
        # Channel name rounds 15.0 → "15" but keeps 14.5 as "14.5"
        label = str(int(n)) if n == int(n) else str(n)
        result[n] = CPTChannel(name=f"Su_Nkt{label}", unit="kPa", values=su)
    return result


# ---------------------------------------------------------------------------
# Eq 5 — Jamiolkowski 2001 Relative Density
# ---------------------------------------------------------------------------


_MPA_ALIASES = {"MPa", "mpa", "MPA"}
_KPA_ALIASES = {"kPa", "kpa", "KPA"}


def compute_dr_jamiolkowski(
    qc: CPTChannel,
    sigma_prime_v0: CPTChannel,
) -> CPTChannel:
    """
    Jamiolkowski 2001 relative density.

        Dr = (1 / 2.9) × ln[ qc / (141 × σ'_v0^0.55) ]

    **Hard-coded mixed units** — ``qc`` MUST be in MPa and ``σ'_v0`` MUST
    be in kPa. The empirical constants in the equation are only valid
    under that convention. The function refuses any other unit with
    :class:`ValueError` to keep callers honest.

    Clipping:
      - ``σ'_v0`` is floored at 0.01 kPa before raising to 0.55 to avoid
        log-of-zero at the very first sample.
      - The ratio inside ``ln`` is floored at ``1e-9`` so the result stays
        finite when qc is zero.

    Returns:
        :class:`CPTChannel` named ``"Dr"`` with unit ``"-"`` (ratio form —
        callers that want percent multiply by 100).
    """
    if qc.unit not in _MPA_ALIASES:
        raise ValueError(
            f"compute_dr_jamiolkowski requires qc.unit == 'MPa' "
            f"(hardcoded Jamiolkowski 2001 convention); got {qc.unit!r}"
        )
    if sigma_prime_v0.unit not in _KPA_ALIASES:
        raise ValueError(
            f"compute_dr_jamiolkowski requires sigma_prime_v0.unit == 'kPa' "
            f"(hardcoded Jamiolkowski 2001 convention); got {sigma_prime_v0.unit!r}"
        )

    qc_mpa = qc.values
    spv0_kpa = sigma_prime_v0.values
    if qc_mpa.shape != spv0_kpa.shape:
        raise ValueError(
            f"qc / sigma_prime_v0 shape mismatch: "
            f"{qc_mpa.shape} vs {spv0_kpa.shape}"
        )

    spv0_safe = np.clip(spv0_kpa, 0.01, None)
    denom = 141.0 * np.power(spv0_safe, 0.55)
    ratio = np.clip(qc_mpa / denom, 1e-9, None)
    dr = (1.0 / 2.9) * np.log(ratio)
    return CPTChannel(name="Dr", unit="-", values=dr)
