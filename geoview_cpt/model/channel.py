"""
geoview_cpt.model.channel
================================
:class:`CPTChannel` — one named time/depth series on a :class:`CPTSounding`.

Raw channels come straight from the parser (``qc``, ``fs``, ``u2``,
``depth``, ``inclination``). Derived channels are produced by
:mod:`geoview_cpt.derivation` and include ``qt``, ``Rf``, ``Bq``,
``Qt``, ``Fr``, ``Ic``, ``SBTn``, ``γ``, ``σv``, ``σ'v``, ``Su``, ``Dr``.

This module purposely keeps the type thin: a name, a unit, and a numpy
array. Higher-level operations (resample, window, align) live elsewhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

__all__ = ["CPTChannel"]


@dataclass
class CPTChannel:
    """
    One named channel on a :class:`CPTSounding`.

    Attributes:
        name:   identifier (``"qc"``, ``"fs"``, ``"u2"``, ``"depth"`` …).
        unit:   SI unit string (``"MPa"``, ``"kPa"``, ``"m"`` …).
        values: numpy array of samples, shape ``(N,)``.

    Construction coerces ``values`` into a ``np.float64`` 1D array so every
    downstream deriver can assume the contract.
    """

    name: str
    unit: str = ""
    values: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float64))

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("CPTChannel.name must not be empty")
        arr = np.asarray(self.values, dtype=np.float64)
        if arr.ndim > 1:
            raise ValueError(
                f"CPTChannel.values must be 1-D, got shape {arr.shape}"
            )
        self.values = arr

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return int(self.values.shape[0])

    def __iter__(self) -> Iterable[float]:
        return iter(self.values.tolist())

    @property
    def is_empty(self) -> bool:
        return self.values.size == 0

    def min(self) -> float:
        return float(self.values.min()) if not self.is_empty else float("nan")

    def max(self) -> float:
        return float(self.values.max()) if not self.is_empty else float("nan")

    def mean(self) -> float:
        return float(self.values.mean()) if not self.is_empty else float("nan")
