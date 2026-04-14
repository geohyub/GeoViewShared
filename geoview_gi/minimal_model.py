"""
geoview_gi.minimal_model
================================
Minimal ground-investigation data model (Phase A-2 A2.19).

Four core dataclasses the rest of Wave 2 builds on:

    :class:`Borehole`      — a single drill location (AGS4 ``LOCA`` peer)
    :class:`StratumLayer`  — one geology layer (AGS4 ``GEOL`` peer)
    :class:`SPTTest`       — one SPT blow-count test (AGS4 ``ISPT`` peer)
    :class:`LabSample`     — a 17-field lab sample (AGS4 ``SAMP`` peer with
                             consolidated test-result slots)

Design:
 - All dataclasses are **mutable** — consumers add layers and tests
   incrementally during parsing.
 - Identifier field names mirror AGS4 group/column conventions where the
   mapping is 1:1, so an AGS4 round-trip in Phase A-4 can be a shallow
   rename.
 - Floating-point fields default to ``None`` rather than ``0.0`` so the
   AGS4 writer can distinguish "not measured" from "measured as zero".
 - ``LabSample`` carries **17 fields** as called out in the master plan:
   AGS4 identity (4), depth/recovery (3), sample state (3), index props
   (3), strength (3), failure code (1). The count is enforced by the
   test suite so the contract doesn't drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

__all__ = [
    "Borehole",
    "StratumLayer",
    "SPTTest",
    "LabSample",
    "SampleType",
    "FailureCode",
]


SampleType = Literal["U", "D", "B", "W", "C", "P", "PC", "KN", "OTHER"]
"""
AGS4 ``SAMP_TYPE`` enumeration (trimmed to what we actually ingest):

 - ``U`` undisturbed tube
 - ``D`` disturbed bag
 - ``B`` bulk
 - ``W`` water
 - ``C`` core
 - ``P`` piston
 - ``PC`` / ``KN`` vendor-specific (JAKO SA Geolab)
 - ``OTHER`` anything unmapped — parsers should prefer this over raising.
"""


FailureCode = Literal["A", "B", "C", "D", "N/A"]
"""SA Geolab failure type per Wave 0 3rd-round PDF reconnaissance."""


# ---------------------------------------------------------------------------
# Borehole
# ---------------------------------------------------------------------------


@dataclass
class Borehole:
    """
    One drill location — AGS4 ``LOCA`` peer.

    Coordinates default to ``None`` so the downstream writer can emit an
    empty AGS4 cell rather than a misleading ``0,0``.
    """

    loca_id: str
    project_name: str = ""
    client: str = ""
    easting_m: float | None = None
    northing_m: float | None = None
    crs: str = ""                       # e.g. "UTM 52N (EPSG:32652)"
    ground_level_m: float | None = None
    final_depth_m: float | None = None
    water_depth_m: float | None = None  # seabed elevation for marine holes
    start_date: date | None = None
    end_date: date | None = None
    method: str = ""                    # "Rotary Core" / "Percussion" / ...
    remarks: str = ""
    strata: list["StratumLayer"] = field(default_factory=list)
    spt_tests: list["SPTTest"] = field(default_factory=list)
    samples: list["LabSample"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.loca_id:
            raise ValueError("Borehole.loca_id must not be empty")

    # Convenience
    @property
    def total_strata(self) -> int:
        return len(self.strata)

    def add_stratum(self, layer: "StratumLayer") -> None:
        if layer.top_m < 0:
            raise ValueError("StratumLayer.top_m must be >= 0")
        if layer.base_m <= layer.top_m:
            raise ValueError("StratumLayer.base_m must exceed top_m")
        self.strata.append(layer)

    def add_spt(self, spt: "SPTTest") -> None:
        self.spt_tests.append(spt)

    def add_sample(self, sample: "LabSample") -> None:
        self.samples.append(sample)


# ---------------------------------------------------------------------------
# Stratum
# ---------------------------------------------------------------------------


@dataclass
class StratumLayer:
    """
    One stratigraphic layer — AGS4 ``GEOL`` peer.

    Fields follow AGS4 column conventions: ``top_m`` → ``GEOL_TOP``,
    ``base_m`` → ``GEOL_BASE``, ``description`` → ``GEOL_DESC``,
    ``legend_code`` → ``GEOL_LEG``, ``geology_code`` → ``GEOL_GEOL``,
    ``age`` → ``GEOL_GEO2``, ``weathering_grade`` → ``GEOL_STAT``.
    """

    top_m: float
    base_m: float
    description: str = ""
    legend_code: str = ""            # short symbol, e.g. "SM", "CL"
    geology_code: str = ""           # USCS or local classification
    age: str = ""                    # e.g. "Quaternary alluvium"
    weathering_grade: int | None = None  # Table 33 — 0..5

    def __post_init__(self) -> None:
        if self.top_m < 0:
            raise ValueError("StratumLayer.top_m must be >= 0")
        if self.base_m <= self.top_m:
            raise ValueError(
                f"StratumLayer.base_m ({self.base_m}) must exceed top_m ({self.top_m})"
            )
        if self.weathering_grade is not None and not 0 <= self.weathering_grade <= 5:
            raise ValueError(
                f"weathering_grade must be 0-5, got {self.weathering_grade}"
            )

    @property
    def thickness_m(self) -> float:
        return self.base_m - self.top_m

    @property
    def midpoint_m(self) -> float:
        return (self.top_m + self.base_m) / 2


# ---------------------------------------------------------------------------
# SPT
# ---------------------------------------------------------------------------


@dataclass
class SPTTest:
    """
    One Standard Penetration Test — AGS4 ``ISPT`` peer.

    Fields: ``top_m`` → ``ISPT_TOP``, ``seat_blows`` → ``ISPT_SEAT``,
    ``main_blows`` → ``ISPT_MAIN``, ``n_value`` → ``ISPT_NVAL``,
    ``method`` → ``ISPT_NMET``, ``refusal`` → ``ISPT_REF``.
    """

    top_m: float
    seat_blows: int | None = None         # 15 cm seating drive
    main_blows: int | None = None         # 30 cm main drive total
    n_value: int | None = None            # combined N (normally main_blows)
    method: str = "SPT"                   # "SPT" | "SPT(C)" | "Chisel"
    refusal: bool = False                 # True if rod could not advance
    remarks: str = ""

    def __post_init__(self) -> None:
        if self.top_m < 0:
            raise ValueError("SPTTest.top_m must be >= 0")
        if self.n_value is None and self.main_blows is not None:
            self.n_value = self.main_blows


# ---------------------------------------------------------------------------
# Lab sample — 17 fields
# ---------------------------------------------------------------------------


@dataclass
class LabSample:
    """
    Lab sample with consolidated test-result slots — 17 fields.

    Contract: the public field count is enforced by
    :func:`test_minimal_model.test_lab_sample_has_17_fields` so downstream
    AGS4/Excel writers can rely on the layout.

    Field groups:

     1. AGS4 identity (4):      ``loca_id``, ``sample_id``, ``sample_type``,
                                ``sample_ref``
     2. Depth / recovery (3):   ``top_m``, ``base_m``, ``recovery_pct``
     3. State (3):              ``moisture_content_pct``, ``bulk_density_t_m3``,
                                ``void_ratio``
     4. Index (3):              ``liquid_limit_pct``, ``plastic_limit_pct``,
                                ``fines_pct``
     5. Strength (3):           ``undrained_shear_strength_kpa``,
                                ``effective_friction_angle_deg``,
                                ``effective_cohesion_kpa``
     6. Failure code (1):       ``failure_code`` (SA Geolab A/B/C/D/N/A)
    """

    # 1. Identity
    loca_id: str
    sample_id: str
    sample_type: SampleType = "OTHER"
    sample_ref: str = ""

    # 2. Depth
    top_m: float = 0.0
    base_m: float | None = None
    recovery_pct: float | None = None

    # 3. State
    moisture_content_pct: float | None = None
    bulk_density_t_m3: float | None = None
    void_ratio: float | None = None

    # 4. Index
    liquid_limit_pct: float | None = None
    plastic_limit_pct: float | None = None
    fines_pct: float | None = None

    # 5. Strength
    undrained_shear_strength_kpa: float | None = None
    effective_friction_angle_deg: float | None = None
    effective_cohesion_kpa: float | None = None

    # 6. Failure
    failure_code: FailureCode = "N/A"

    def __post_init__(self) -> None:
        if not self.loca_id:
            raise ValueError("LabSample.loca_id must not be empty")
        if not self.sample_id:
            raise ValueError("LabSample.sample_id must not be empty")
        if self.top_m < 0:
            raise ValueError("LabSample.top_m must be >= 0")
        if self.base_m is not None and self.base_m < self.top_m:
            raise ValueError(
                f"LabSample.base_m ({self.base_m}) must be >= top_m ({self.top_m})"
            )
        if self.recovery_pct is not None and not 0 <= self.recovery_pct <= 100:
            raise ValueError(
                f"recovery_pct must be 0-100, got {self.recovery_pct}"
            )
