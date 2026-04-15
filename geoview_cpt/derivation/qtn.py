"""
geoview_cpt.derivation.qtn
================================
Robertson 2009 iterative stress-normalised cone resistance ``Qtn``.

Closes open question Q36. Week 4's linear :func:`compute_qt_normalized`
is Robertson 1990's ``Qt1 = (qt − σ_v0) / σ'_v0`` — dimensionally
consistent but only accurate in normally-consolidated clay. Robertson
2009 introduced a stress-exponent normalisation that tracks the
actual stress level::

    Qtn = ((qt − σ_v0) / p_a) × (p_a / σ'_v0)^n
    n   = 0.381 × Ic + 0.05 × (σ'_v0 / p_a) − 0.15
    Ic  = √[(3.47 − log₁₀ Qtn)² + (log₁₀ Fr + 1.22)²]

The exponent ``n`` and the soil-behaviour index ``Ic`` are mutually
dependent, so we iterate. Wave 4 R2 tolerance harness confirmed
CPeT-IT uses this iterative form — feeding CPeT-IT's ``Qtn`` column
directly to :func:`geoview_cpt.derivation.ic.compute_ic` reproduces
the CPeT-IT ``Ic`` exactly.

This module is the deriver version: it starts from raw channels and
converges to (``Qtn``, ``Ic``) on its own. The default tolerance and
iteration cap match Robertson 2009's guidance (``n`` changing by less
than 0.01 between iterations, typically 3–5 sweeps).

The companion :func:`compute_ic_robertson_2009` is a convenience that
chains Qtn + ``compute_ic`` so the common "raw → Ic" path is one call.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from geoview_cpt.correction.units import to_kpa
from geoview_cpt.derivation.ic import compute_ic
from geoview_cpt.model import CPTChannel

__all__ = [
    "DEFAULT_PA_KPA",
    "DEFAULT_N_INIT",
    "DEFAULT_N_MIN",
    "DEFAULT_N_MAX",
    "DEFAULT_MAX_ITER",
    "DEFAULT_N_TOL",
    "QtnIterationResult",
    "compute_qtn_iterative",
    "compute_ic_robertson_2009",
]


DEFAULT_PA_KPA: float = 100.0     # atmospheric pressure reference
DEFAULT_N_INIT: float = 1.0       # Robertson 2009 seed
DEFAULT_N_MIN: float = 0.5        # clip for sand
DEFAULT_N_MAX: float = 1.0        # clip for clay
DEFAULT_MAX_ITER: int = 10
DEFAULT_N_TOL: float = 0.01


@dataclass
class QtnIterationResult:
    """Diagnostic bundle for one call to :func:`compute_qtn_iterative`."""

    qtn: CPTChannel
    ic: CPTChannel
    n: np.ndarray
    iterations: int
    converged: bool


# ---------------------------------------------------------------------------
# Iterative Qtn
# ---------------------------------------------------------------------------


def compute_qtn_iterative(
    qt: CPTChannel,
    fs: CPTChannel,
    sigma_v0: CPTChannel,
    sigma_prime_v0: CPTChannel,
    *,
    pa_kpa: float = DEFAULT_PA_KPA,
    n_init: float = DEFAULT_N_INIT,
    n_min: float = DEFAULT_N_MIN,
    n_max: float = DEFAULT_N_MAX,
    max_iter: int = DEFAULT_MAX_ITER,
    tol: float = DEFAULT_N_TOL,
) -> QtnIterationResult:
    """
    Iteratively compute Robertson 2009 Qtn and Ic.

    Args:
        qt:              corrected cone resistance channel (MPa or kPa).
        fs:              sleeve friction channel (MPa or kPa).
        sigma_v0:        total vertical stress (MPa or kPa).
        sigma_prime_v0:  effective vertical stress (MPa or kPa).
        pa_kpa:          atmospheric reference pressure (kPa).
        n_init:          initial guess for the stress exponent ``n``
                         (Robertson 2009 recommends 1.0 → clay-like).
        n_min / n_max:   clamp bounds for ``n`` (0.5..1.0 typical).
        max_iter:        hard cap on the sweep count.
        tol:             convergence when ``max(|Δn|) < tol`` at every
                         sample.

    Returns:
        :class:`QtnIterationResult` with the converged ``Qtn`` and
        ``Ic`` channels, the per-sample final ``n`` vector, the
        iteration count, and a convergence flag.
    """
    qt_kpa = to_kpa(qt)
    fs_kpa = to_kpa(fs)
    sv0 = to_kpa(sigma_v0)
    spv0 = to_kpa(sigma_prime_v0)

    shape = qt_kpa.shape
    if not (fs_kpa.shape == sv0.shape == spv0.shape == shape):
        raise ValueError(
            "compute_qtn_iterative inputs must share shape: "
            f"qt={shape} fs={fs_kpa.shape} sv0={sv0.shape} spv0={spv0.shape}"
        )

    qnet = qt_kpa - sv0
    spv0_safe = np.clip(spv0, 1e-3, None)
    qnet_pa = qnet / pa_kpa

    # Seed n and Fr (Fr is independent of n)
    with np.errstate(divide="ignore", invalid="ignore"):
        fr = np.where(
            qnet > 1.0,
            fs_kpa / qnet * 100.0,
            0.0,
        )
    fr = np.clip(fr, 1e-3, None)

    n = np.full(shape, float(n_init), dtype=np.float64)
    qtn = np.zeros(shape, dtype=np.float64)
    ic = np.zeros(shape, dtype=np.float64)
    converged = False
    iteration = 0

    for iteration in range(1, max_iter + 1):
        qtn = qnet_pa * np.power(pa_kpa / spv0_safe, n)
        qtn_clip = np.clip(qtn, 1e-3, None)
        a = 3.47 - np.log10(qtn_clip)
        b = np.log10(fr) + 1.22
        ic = np.sqrt(a * a + b * b)

        n_new = 0.381 * ic + 0.05 * (spv0_safe / pa_kpa) - 0.15
        n_new = np.clip(n_new, n_min, n_max)

        delta = np.abs(n_new - n)
        n = n_new
        if np.max(delta) < tol:
            converged = True
            break

    # Samples with qnet ≤ 0 (at very shallow depth) stay at zero — the
    # calling code should filter them out.
    qtn = np.where(qnet > 0, qtn, 0.0)

    return QtnIterationResult(
        qtn=CPTChannel(name="Qtn", unit="-", values=qtn),
        ic=CPTChannel(name="Ic", unit="-", values=ic),
        n=n,
        iterations=iteration,
        converged=converged,
    )


def compute_ic_robertson_2009(
    qt: CPTChannel,
    fs: CPTChannel,
    sigma_v0: CPTChannel,
    sigma_prime_v0: CPTChannel,
    **kwargs,
) -> CPTChannel:
    """
    Convenience wrapper returning just the Robertson 2009 ``Ic`` channel.

    Equivalent to ``compute_qtn_iterative(...).ic`` — use this when you
    don't need the diagnostic bundle. Supports the same iteration
    knobs via ``**kwargs``.
    """
    result = compute_qtn_iterative(qt, fs, sigma_v0, sigma_prime_v0, **kwargs)
    return result.ic
