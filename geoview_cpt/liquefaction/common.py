"""
geoview_cpt.liquefaction.common
================================
Shared dataclasses for the four A2.10/A2.11 triggering modules.

Every method produces a :class:`LiquefactionProfile` — a per-depth
table of (CRR, CSR, FS, label) keyed by method name. Downstream tools
(LPI / LSN aggregators, chart builders, Kingdom AGS4 export) all
consume this shape regardless of which triggering method produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

__all__ = [
    "EarthquakeScenario",
    "LiquefactionCase",
    "LiquefactionProfile",
    "LiquefactionResult",
]


@dataclass(frozen=True)
class EarthquakeScenario:
    """
    Design earthquake inputs for liquefaction triggering.

    Attributes:
        name:              free-form label for the scenario.
        magnitude_mw:      moment magnitude.
        pga_g:             peak ground acceleration at surface, in g.
        groundwater_m:     groundwater level below ground surface (m).
                           Defaults to 0 (seabed / high water table).
        fines_correction:  enable fines-content correction term on
                           Ic-based methods (Robertson & Wride 1998,
                           Youd 2001). Defaults True.
    """

    name: str
    magnitude_mw: float
    pga_g: float
    groundwater_m: float = 0.0
    fines_correction: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("EarthquakeScenario.name must not be empty")
        if not 4.0 <= self.magnitude_mw <= 9.5:
            raise ValueError(
                f"magnitude_mw out of seismological range: {self.magnitude_mw}"
            )
        if self.pga_g <= 0:
            raise ValueError(f"pga_g must be positive, got {self.pga_g}")


LabelLiterals = Literal[
    "liquefiable",
    "marginal",
    "non_liquefiable",
    "clay_like",
    "n/a",
]


@dataclass
class LiquefactionCase:
    """One depth sample's triggering outcome."""

    depth_m: float
    crr: float | None
    csr: float | None
    factor_of_safety: float | None
    label: LabelLiterals = "n/a"


@dataclass
class LiquefactionProfile:
    """
    Full per-depth triggering result from one method.

    Attributes:
        method:     free-form identifier (``"robertson_wride_1998"``, …).
        scenario:   the :class:`EarthquakeScenario` that drove the run.
        depth_m:    depth vector (m).
        crr:        per-depth cyclic resistance ratio.
        csr:        per-depth cyclic stress ratio.
        fs:         per-depth factor of safety (``crr / csr``). ``NaN``
                    where CSR is zero or CRR undefined.
        labels:     parallel list of :data:`LabelLiterals` strings.
        extras:     free-form diagnostic dict (trace data per method).
    """

    method: str
    scenario: EarthquakeScenario
    depth_m: np.ndarray
    crr: np.ndarray
    csr: np.ndarray
    fs: np.ndarray
    labels: list[LabelLiterals]
    extras: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return int(self.depth_m.shape[0])

    def iter_cases(self):
        for i in range(len(self)):
            yield LiquefactionCase(
                depth_m=float(self.depth_m[i]),
                crr=float(self.crr[i]) if np.isfinite(self.crr[i]) else None,
                csr=float(self.csr[i]) if np.isfinite(self.csr[i]) else None,
                factor_of_safety=(
                    float(self.fs[i]) if np.isfinite(self.fs[i]) else None
                ),
                label=self.labels[i],
            )

    @property
    def liquefiable_fraction(self) -> float:
        """Fraction of samples labelled ``"liquefiable"`` or ``"marginal"``."""
        if not self.labels:
            return 0.0
        hits = sum(1 for L in self.labels if L in ("liquefiable", "marginal"))
        return hits / len(self.labels)


@dataclass
class LiquefactionResult:
    """
    Aggregate result from a triggering run + LPI/LSN severity indices.
    """

    profile: LiquefactionProfile
    lpi: float = 0.0
    lsn: float = 0.0
    label: Literal["none", "low", "moderate", "high", "very_high"] = "none"
