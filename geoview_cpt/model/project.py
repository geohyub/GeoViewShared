"""
geoview_cpt.model.project
================================
Minimum :class:`CPTProject` / :class:`CPTSounding` shape consumed by the
Phase A-2 A2.0 CPeT-IT reader.

A2.0 is intentionally conservative: we only capture what the reader can
extract losslessly from a CPeT-IT ``.cpt`` file. A2.1 extends with
:class:`CPTHeader`, :class:`CPTChannel`, derived channels, strata, and
AGS4 round-trip state. Fields introduced here MUST remain stable so A2.1
can layer on without breakage.

Round-trip philosophy: store the canonical fields a Python consumer
cares about **and** keep the original inflated XML bytes around so the
A2.0c writer (future epic) can do in-place value replacement without
losing the 2,077 chart-axis metadata tags CPeT-IT relies on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["CPTProject", "CPTSounding"]


@dataclass
class CPTSounding:
    """
    One CPeT-IT sounding — a ``<NNNNN>`` block inside ``<CPTFiles>``.

    A2.0 stores what the reader needs to round-trip without committing
    to the full canonical channel model (that lands in A2.1).

    Attributes:
        handle:         ``<Handle>`` — the integer matching the element tag
                        name (e.g. 87616).
        element_tag:    Original tag name as it appears in the XML
                        (``"87616"``). Kept verbatim so the writer can emit
                        the same structure.
        name:           ``<CPTName>`` — display name (e.g. ``"CPT-01"``).
        file_name:      ``<CPTFileName>`` — original external filename (may
                        be empty for CPeT-IT–authored projects).
        input_count:    ``<InputCount>`` — raw sample count.
        output_count:   ``<OutputCount>`` — processed sample count.
        max_depth_m:    ``<MaxDepth>``.
        unit_system:    ``<UnitSystem>`` (0 = SI, 1 = Imperial).
        cone_corrected: ``<ConeCorrected>`` — True when CPeT-IT already
                        applied qt correction.
        properties:     ``<CPTProperties>`` flattened to ``{tag: text}``.
                        This covers Nkt, Alpha, Elevation, GWT, Kocr,
                        coordinates and the other per-sounding knobs.
                        Preserved as strings so the round-trip writer can
                        replace values without round-trip drift on floats.
        chart_config_raw: ``{"left": lxml.Element, "bottom": lxml.Element}``
                        (serialized to strings by the reader — see below).
                        Stored as XML bytes to keep 2,077 chart axis tags
                        intact.
        blob_b64:       Raw text of the ``<NNNNN>`` element **up to the
                        first child** — this is the base64 payload. Stored
                        as a str so the writer can round-trip it. May be
                        empty for soundings that carry no inline binary.
        extras:         Every other immediate child of ``<NNNNN>`` stored
                        as ``{tag: xml_bytes}`` so future parsers
                        (``Samples``, ``PileData``, ``CustomCalculationData``
                        etc.) can interpret them without the reader itself
                        knowing how.
    """

    handle: int
    element_tag: str
    name: str = ""
    file_name: str = ""
    input_count: int = 0
    output_count: int = 0
    max_depth_m: float = 0.0
    unit_system: int = 0
    cone_corrected: bool = False
    properties: dict[str, str] = field(default_factory=dict)
    chart_config_raw: dict[str, bytes] = field(default_factory=dict)
    blob_b64: str = ""
    extras: dict[str, bytes] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience accessors — read-only, strongly typed where it's safe.
    # ------------------------------------------------------------------

    @property
    def nkt(self) -> float | None:
        return _float_or_none(self.properties.get("Nkt"))

    @property
    def alpha(self) -> float | None:
        return _float_or_none(self.properties.get("Alpha"))

    @property
    def elevation_m(self) -> float | None:
        return _float_or_none(self.properties.get("Elevation"))

    @property
    def gwt_m(self) -> float | None:
        return _float_or_none(self.properties.get("GWT"))

    @property
    def depth_interval_m(self) -> float | None:
        return _float_or_none(self.properties.get("DepthInterval"))


@dataclass
class CPTProject:
    """
    Top-level CPeT-IT project.

    Populated by :func:`geoview_cpt.parsers.cpet_it_v30.read_cpt_v30`. Every
    field corresponds directly to the XML layout so writers can round-trip.

    Attributes:
        source_path:       ``.cpt`` file the project was read from (empty
                           when the caller hands us raw bytes directly).
        handle:            ``<Various>/<Handle>``.
        name:              ``<Various>/<Project>``.
        project_id:        ``<Various>/<ProjectID>``.
        location:          ``<Various>/<Location>``.
        comments:          ``<Various>/<Comments>``.
        partner_brand:     ``<Various>/<First>``  — branding line 1.
        partner_description: ``<Various>/<Second>`` — branding line 2.
        partner_address:   ``<Various>/<Third>``  — branding line 3.
        partner_url:       ``<Various>/<Forth>``  — branding line 4.
        partner_logo_path: ``<Various>/<Path>``   — absolute path on the
                           author's machine. May be invalid on ours;
                           consumers should treat as hint, not truth.
        unit_system:       0 = SI, 1 = Imperial.
        vertical_plot:     ``<Various>/<Vertical_Plot>`` as bool.
        display_image:     ``<Various>/<DisplayImage>`` as bool.
        font_name:         Global font.
        font_size:         Global font size.
        custom_sbtn_desc:  ``<CustomSBTnDesc>`` parsed from the
                           ``";"``-separated 10-slot list.
        various_raw:       Raw bytes of ``<Various>`` (writer uses this).
        soundings:         One :class:`CPTSounding` per ``<CPTFiles>``
                           child (13 for JACO samples).
        cptfiles_raw:      ``{element_tag: base64_decoded_bytes}`` —
                           convenience mapping used by A2.0b when the
                           binary blob format is reverse-engineered.
        xml_plain:         Original inflated XML bytes (pre-mangle), for
                           byte-exact round-trip when the writer lands.
        raw_compressed:    Original zlib-compressed file bytes, kept for
                           debugging and round-trip diffing.
        extra_sections:    Other top-level children of ``<CPT>`` like
                           ``WebGMap``, ``OverlayProps``, ``CustomData1``
                           stored as ``{tag: xml_bytes}``.
    """

    source_path: Path = field(default_factory=Path)
    # Various block
    handle: int = 0
    name: str = ""
    project_id: str = ""
    location: str = ""
    comments: str = ""
    partner_brand: str = ""
    partner_description: str = ""
    partner_address: str = ""
    partner_url: str = ""
    partner_logo_path: str = ""
    unit_system: int = 0
    vertical_plot: bool = False
    display_image: bool = True
    font_name: str = ""
    font_size: int = 0
    custom_sbtn_desc: list[str] = field(default_factory=list)
    # Raw preservation for round-trip
    various_raw: bytes = b""
    soundings: list[CPTSounding] = field(default_factory=list)
    cptfiles_raw: dict[str, bytes] = field(default_factory=dict)
    xml_plain: bytes = b""
    raw_compressed: bytes = b""
    extra_sections: dict[str, bytes] = field(default_factory=dict)

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.soundings)

    def __iter__(self):
        return iter(self.soundings)

    def get_sounding(self, name_or_handle: str | int) -> CPTSounding:
        """Lookup by :attr:`CPTSounding.name` or :attr:`CPTSounding.handle`."""
        for s in self.soundings:
            if s.name == name_or_handle or s.handle == name_or_handle:
                return s
        raise KeyError(f"sounding {name_or_handle!r} not found")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _float_or_none(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None
