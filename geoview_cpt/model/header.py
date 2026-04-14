"""
geoview_cpt.model.header
================================
:class:`CPTHeader` + :class:`AcquisitionEvent` (Phase A-2 A2.1).

The header captures every sounding-level metadata field a downstream
parser, deriver, chart builder, or report needs. Three sources feed it:

 - CPeT-IT ``.cpt`` files (most fields, via A2.0)
 - YW Excel / JAKO Excel / field book parsers (A2.2a/b/c)
 - AGS4 ``LOCA`` group for round-trip preservation (A4.0)

Equipment defaults reflect Wave 0 reconnaissance:

 - JACO Korea: 200 mm² base area, 0.7032 area ratio, Gouda WISON-APB
 - HELMS Yawol: 1000 mm² base area, 0.71 area ratio, Geomarine kit

Events are an **append-only** stream — a parser discovers them in order
and ``record_event`` is the only mutation path so an audit log is easy
to produce later.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

__all__ = [
    "SoundingType",
    "EventType",
    "AcquisitionEvent",
    "CPTHeader",
]


SoundingType = Literal["PCPT", "SCPT", "SEABED_FRAME", "DOWNHOLE_WIRELINE", "UNKNOWN"]
"""Type of CPT push — used by QC rules and chart selection."""


EventType = Literal[
    "Thrust",
    "Retract",
    "Deck Baseline",
    "Seabed Baseline",
    "Post Baseline",
    "Cone Up",
    "Max Push Distance Reached",
    "CHANGE CONE",
    "Operator Note",
    "Other",
]
"""CPeT-IT / Gouda WISON acquisition event taxonomy (Wave 0 3rd round)."""


@dataclass(frozen=True)
class AcquisitionEvent:
    """
    One timestamped acquisition event on a sounding.

    Frozen so downstream consumers can cache/display without defensive
    copies. ``timestamp`` is whatever the acquisition source emits; the
    parser normalizes to naive UTC when possible.
    """

    timestamp: datetime
    event_type: EventType
    message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            raise TypeError(
                f"AcquisitionEvent.timestamp must be datetime, got "
                f"{type(self.timestamp).__name__}"
            )
        if not self.event_type:
            raise ValueError("AcquisitionEvent.event_type must not be empty")


@dataclass
class CPTHeader:
    """
    Sounding-level metadata.

    All optional fields default to neutral sentinels (``""``, ``None``,
    ``0.0``) so partially populated headers round-trip cleanly. The QC
    and chart layers decide how strictly to interpret missing data.
    """

    # Identity
    sounding_id: str
    project_name: str = ""
    client: str = ""
    partner_name: str = ""              # "Geoview" / "HELMS" / ...
    operator: str = ""
    vessel: str = ""
    barge: str = ""                     # "G-Star" / "Jack-up Barge 1" / ...

    # Location (WGS84 decimal or local UTM)
    loca_x: float | None = None
    loca_y: float | None = None
    loca_crs: str = ""                  # "UTM 52N (EPSG:32652)"
    water_depth_m: float | None = None
    ground_elev_m: float | None = None

    # Sounding classification
    sounding_type: SoundingType = "UNKNOWN"

    # Equipment (Wave 0 defaults: 200 mm² / 0.7032 JACO; 1000 mm² / 0.71 HELMS)
    equipment_vendor: str = ""
    equipment_model: str = ""
    cone_serial: str = ""
    cone_base_area_mm2: float = 0.0
    cone_area_ratio_a: float = 0.0

    # Timing
    started_at: datetime | None = None
    completed_at: datetime | None = None

    # Wave 0 3rd round additions
    events: list[AcquisitionEvent] = field(default_factory=list)
    end_note: str = ""                  # "End of borehole at depth X m"
    max_push_depth_m: float | None = None

    def __post_init__(self) -> None:
        if not self.sounding_id:
            raise ValueError("CPTHeader.sounding_id must not be empty")
        if self.cone_base_area_mm2 < 0:
            raise ValueError("CPTHeader.cone_base_area_mm2 must be non-negative")
        if not 0.0 <= self.cone_area_ratio_a <= 1.0:
            raise ValueError(
                "CPTHeader.cone_area_ratio_a must be in [0.0, 1.0], got "
                f"{self.cone_area_ratio_a}"
            )
        if (
            self.started_at is not None
            and self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError(
                "CPTHeader.completed_at must be >= started_at"
            )

    # ------------------------------------------------------------------

    def record_event(
        self,
        timestamp: datetime,
        event_type: EventType,
        message: str = "",
    ) -> AcquisitionEvent:
        """Append an :class:`AcquisitionEvent` and return it."""
        event = AcquisitionEvent(
            timestamp=timestamp, event_type=event_type, message=message
        )
        self.events.append(event)
        return event

    @property
    def duration_s(self) -> float | None:
        """Elapsed time between ``started_at`` and ``completed_at`` in seconds."""
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def is_marine(self) -> bool:
        """True when the sounding has a water depth value."""
        return self.water_depth_m is not None and self.water_depth_m > 0

    @property
    def has_equipment_info(self) -> bool:
        return bool(self.equipment_vendor or self.equipment_model or self.cone_serial)
