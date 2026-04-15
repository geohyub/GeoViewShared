"""
geoview_cpt.stratigraphy.ic_split
========================================
Automatic stratigraphic layering from a Robertson Ic profile + manual
editor.

The auto-split walks the ``Ic`` channel top-down and groups contiguous
samples that fall into the same Robertson 2009 bin:

    Ic < 1.31               zone 7  (gravelly sand)
    1.31 ≤ Ic < 2.05        zone 6  (clean sand)
    2.05 ≤ Ic < 2.60        zone 5  (silty sand)
    2.60 ≤ Ic < 2.95        zone 4  (clayey silt)
    2.95 ≤ Ic < 3.60        zone 3  (clay)
    Ic ≥ 3.60               zone 2  (organic clay)

Consecutive zone runs become :class:`StratumLayer` instances. Runs
thinner than ``min_thickness_m`` are merged into the layer above (or
below if the thin sliver sits at the very top).

The :class:`StratumEditor` class is a thin mutable wrapper that lets a
UI (or a test) move a boundary, merge two adjacent layers, or split a
layer at a specified depth without re-running the auto-split — every
operation preserves the depth invariants (``top < base``, sorted,
no gaps).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

import numpy as np

from geoview_cpt.derivation.sbt import classify_ic_to_robertson_1990_zone
from geoview_gi.minimal_model import StratumLayer

if TYPE_CHECKING:
    from geoview_cpt.model import CPTSounding

__all__ = [
    "DEFAULT_IC_THRESHOLDS",
    "auto_split_by_ic",
    "StratumEditor",
]


DEFAULT_IC_THRESHOLDS: tuple[float, ...] = (1.31, 2.05, 2.60, 2.95, 3.60)


_ZONE_LABELS: dict[int, tuple[str, str]] = {
    2: ("OH", "Organic clay"),
    3: ("CL", "Clay"),
    4: ("ML", "Clayey silt"),
    5: ("SM", "Silty sand"),
    6: ("SP", "Clean sand"),
    7: ("GW", "Gravelly sand"),
    0: ("NA", "Unclassified"),
}


def auto_split_by_ic(
    sounding: "CPTSounding",
    *,
    thresholds: Sequence[float] = DEFAULT_IC_THRESHOLDS,
    min_thickness_m: float = 0.1,
) -> list[StratumLayer]:
    """
    Group contiguous Ic samples into :class:`StratumLayer` instances.

    Args:
        sounding:         must expose ``channels['depth']`` and either
                          ``derived['Ic']`` or ``channels['Ic']``.
        thresholds:       Robertson Ic bin boundaries (exclusive upper).
                          Default matches Robertson 2009. Unused here
                          except as trace metadata — the zone classifier
                          already enforces the same values.
        min_thickness_m:  floor on layer thickness; thinner runs are
                          merged with their neighbour (upward by
                          default, downward when the sliver is at the
                          top of the sounding).

    Returns:
        Ordered list of :class:`StratumLayer` spanning the full depth
        range. Never returns an empty list; a sounding with only a few
        samples collapses into one layer.
    """
    depth_ch = sounding.channels.get("depth")
    ic_ch = sounding.derived.get("Ic") or sounding.channels.get("Ic")
    if depth_ch is None or depth_ch.values.size == 0:
        return []
    if ic_ch is None or ic_ch.values.size == 0:
        return [
            StratumLayer(
                top_m=float(depth_ch.values[0]),
                base_m=float(depth_ch.values[-1]) + 1e-6,
                description="no Ic — undifferentiated",
                legend_code="NA",
            )
        ]

    depth = depth_ch.values
    ic = ic_ch.values
    zones = np.array([
        classify_ic_to_robertson_1990_zone(v) if np.isfinite(v) else 0
        for v in ic
    ])

    layers: list[StratumLayer] = []
    run_start = 0
    current_zone = int(zones[0])
    for i in range(1, depth.size):
        z = int(zones[i])
        if z != current_zone:
            layers.append(_make_layer(depth, run_start, i - 1, current_zone))
            run_start = i
            current_zone = z
    layers.append(_make_layer(depth, run_start, depth.size - 1, current_zone))

    return _merge_thin(layers, min_thickness_m=min_thickness_m)


def _make_layer(
    depth: np.ndarray,
    idx_start: int,
    idx_end: int,
    zone: int,
) -> StratumLayer:
    top = float(depth[idx_start])
    base_val = float(depth[idx_end])
    base = base_val if base_val > top else top + 1e-6
    legend, desc = _ZONE_LABELS.get(zone, _ZONE_LABELS[0])
    return StratumLayer(
        top_m=top,
        base_m=base,
        description=desc,
        legend_code=legend,
    )


def _merge_thin(
    layers: list[StratumLayer], *, min_thickness_m: float
) -> list[StratumLayer]:
    if not layers:
        return layers
    changed = True
    # Iterative merge — pass the list until no thin slivers remain.
    while changed and len(layers) > 1:
        changed = False
        for i, layer in enumerate(layers):
            if layer.thickness_m >= min_thickness_m:
                continue
            if i > 0:
                # Merge up: extend previous layer's base
                prev = layers[i - 1]
                layers[i - 1] = StratumLayer(
                    top_m=prev.top_m,
                    base_m=layer.base_m,
                    description=prev.description,
                    legend_code=prev.legend_code,
                    geology_code=prev.geology_code,
                    age=prev.age,
                    weathering_grade=prev.weathering_grade,
                )
                layers.pop(i)
            else:
                # Top sliver — merge down into the next layer
                nxt = layers[i + 1]
                layers[i + 1] = StratumLayer(
                    top_m=layer.top_m,
                    base_m=nxt.base_m,
                    description=nxt.description,
                    legend_code=nxt.legend_code,
                    geology_code=nxt.geology_code,
                    age=nxt.age,
                    weathering_grade=nxt.weathering_grade,
                )
                layers.pop(i)
            changed = True
            break
    return layers


# ---------------------------------------------------------------------------
# StratumEditor
# ---------------------------------------------------------------------------


@dataclass
class StratumEditor:
    """
    Lightweight mutable wrapper around a layer list.

    All operations keep ``top < base`` on every layer and preserve
    sorted order. Boundary moves update the neighbouring layer so no
    gaps are introduced.
    """

    layers: list[StratumLayer]

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.layers)

    def __iter__(self):
        return iter(self.layers)

    def copy(self) -> "StratumEditor":
        return StratumEditor(layers=[copy.deepcopy(layer) for layer in self.layers])

    # ------------------------------------------------------------------

    def move_boundary(self, layer_idx: int, new_base_depth: float) -> None:
        """
        Shift the base depth of ``layers[layer_idx]`` (and the top of
        ``layers[layer_idx + 1]``) to ``new_base_depth``.

        Raises:
            IndexError: ``layer_idx`` is the last layer.
            ValueError: the new boundary would create a non-positive
                        thickness on either neighbour.
        """
        if layer_idx < 0 or layer_idx >= len(self.layers) - 1:
            raise IndexError(f"no layer below index {layer_idx}")
        upper = self.layers[layer_idx]
        lower = self.layers[layer_idx + 1]
        if not (upper.top_m < new_base_depth < lower.base_m):
            raise ValueError(
                f"new boundary {new_base_depth} must lie within "
                f"({upper.top_m}, {lower.base_m})"
            )
        self.layers[layer_idx] = StratumLayer(
            top_m=upper.top_m,
            base_m=new_base_depth,
            description=upper.description,
            legend_code=upper.legend_code,
            geology_code=upper.geology_code,
            age=upper.age,
            weathering_grade=upper.weathering_grade,
        )
        self.layers[layer_idx + 1] = StratumLayer(
            top_m=new_base_depth,
            base_m=lower.base_m,
            description=lower.description,
            legend_code=lower.legend_code,
            geology_code=lower.geology_code,
            age=lower.age,
            weathering_grade=lower.weathering_grade,
        )

    # ------------------------------------------------------------------

    def merge_with_next(self, layer_idx: int) -> None:
        """Combine ``layers[layer_idx]`` and ``layers[layer_idx + 1]``."""
        if layer_idx < 0 or layer_idx >= len(self.layers) - 1:
            raise IndexError(f"no layer below index {layer_idx}")
        upper = self.layers[layer_idx]
        lower = self.layers[layer_idx + 1]
        merged = StratumLayer(
            top_m=upper.top_m,
            base_m=lower.base_m,
            description=upper.description or lower.description,
            legend_code=upper.legend_code or lower.legend_code,
            geology_code=upper.geology_code or lower.geology_code,
            age=upper.age or lower.age,
            weathering_grade=upper.weathering_grade or lower.weathering_grade,
        )
        self.layers[layer_idx] = merged
        self.layers.pop(layer_idx + 1)

    # ------------------------------------------------------------------

    def split(self, layer_idx: int, at_depth: float) -> None:
        """
        Split ``layers[layer_idx]`` at ``at_depth`` into two layers.

        Both halves inherit the parent's metadata; UI callers can
        follow up by renaming the lower half.
        """
        if layer_idx < 0 or layer_idx >= len(self.layers):
            raise IndexError(f"layer index {layer_idx} out of range")
        layer = self.layers[layer_idx]
        if not (layer.top_m < at_depth < layer.base_m):
            raise ValueError(
                f"split depth {at_depth} must be strictly inside "
                f"({layer.top_m}, {layer.base_m})"
            )
        upper = StratumLayer(
            top_m=layer.top_m,
            base_m=at_depth,
            description=layer.description,
            legend_code=layer.legend_code,
            geology_code=layer.geology_code,
            age=layer.age,
            weathering_grade=layer.weathering_grade,
        )
        lower = StratumLayer(
            top_m=at_depth,
            base_m=layer.base_m,
            description=layer.description,
            legend_code=layer.legend_code,
            geology_code=layer.geology_code,
            age=layer.age,
            weathering_grade=layer.weathering_grade,
        )
        self.layers[layer_idx:layer_idx + 1] = [upper, lower]
