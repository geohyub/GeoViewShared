"""
Kingdom LAS exporter — Phase A-4 Week 17 A4.1.

Emits a depth-domain LAS 2.0 file per CPT sounding so Kingdom can
overlay the cone curves on its well-log section view. The exporter
sits **next to** ``ags_convert.converters.las_fmt`` (which round-trips
an entire AGS bundle through SCPT for in-format conversion) — this
module is Kingdom-specific and synthesises the LAS ``~W`` (Well
Information) section from the CPT header so the file slots straight
into ``09_kingdom/LAS/<LOCA_ID>.las``.

Curves emitted by default:

    DEPT (m)   reference depth   — always first per LAS 2.0 spec
    QT   (MPa) corrected cone resistance (sounding.derived['qt'])
    FS   (kPa) sleeve friction (sounding.channels['fs'])
    U2   (kPa) pore pressure u₂ (sounding.channels['u2'])
    IC   ( - ) Robertson Soil Behaviour Type Index
    SBT  ( - ) Robertson 9-zone classification (when available)

The caller can override the curve list via ``curves=`` — the function
silently skips curves whose source channel is missing.

``lasio`` is a hard requirement for this exporter. When not
installed, importing the module is fine (the lasio import is
deferred), but calling :func:`build_kingdom_las` raises
:class:`AgsConvertError` with the install hint
``pip install geoview-common[las]``.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Sequence

import numpy as np

from geoview_cpt.ags_convert.wrapper import AgsConvertError

if TYPE_CHECKING:
    from geoview_cpt.model import CPTSounding

__all__ = [
    "DEFAULT_CURVES",
    "build_kingdom_las",
]


# Each entry: (LAS mnemonic, source slot, channel name, unit, description)
# source slot ∈ {"depth", "raw", "derived"}.
_CurveSpec = tuple[str, str, str, str, str]

DEFAULT_CURVES: tuple[_CurveSpec, ...] = (
    ("DEPT", "depth",   "depth", "m",   "Depth"),
    ("QT",   "derived", "qt",    "MPa", "Corrected cone resistance"),
    ("FS",   "raw",     "fs",    "kPa", "Sleeve friction"),
    ("U2",   "raw",     "u2",    "kPa", "Pore pressure u2"),
    ("IC",   "derived", "Ic",    "",    "Robertson SBT Index"),
    ("SBT",  "derived", "SBT",   "",    "Robertson SBT zone"),
)


def _require_lasio():
    try:
        import lasio  # type: ignore[import-untyped]
    except ImportError as exc:
        raise AgsConvertError(
            "Kingdom LAS exporter requires lasio — "
            "install with `pip install geoview-common[las]`"
        ) from exc
    return lasio


def build_kingdom_las(
    sounding: "CPTSounding",
    path: str | Path,
    *,
    curves: Sequence[_CurveSpec] | None = None,
    project_client: str = "",
) -> Path:
    """
    Write ``sounding`` to a LAS 2.0 file at ``path``.

    Args:
        sounding:       A-2 :class:`CPTSounding` with depth + raw qc/fs/u₂
                        channels, ideally with derived qt / Ic / SBT
                        already populated.
        path:           output path (parent directories auto-created).
                        Per the Week 16 folder layout the file lives in
                        ``09_kingdom/LAS/<LOCA_ID>.las``.
        curves:         optional override for the curve list; defaults
                        to :data:`DEFAULT_CURVES`. Curves whose source
                        channel is missing are silently skipped — the
                        DEPT entry must always be present.
        project_client: optional COMP value for the ~W section. When
                        blank we leave the field empty.

    Returns:
        Resolved output path.

    Raises:
        AgsConvertError: when lasio is not installed or the sounding
                         has no depth channel.
    """
    lasio = _require_lasio()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    spec = list(curves) if curves is not None else list(DEFAULT_CURVES)
    if not spec or spec[0][0] != "DEPT":
        raise AgsConvertError(
            "LAS curve list must start with DEPT (LAS 2.0 spec)"
        )

    depth = _resolve_channel(sounding, spec[0])
    if depth is None or depth.size == 0:
        raise AgsConvertError(
            "sounding has no depth channel — cannot build LAS"
        )

    las = lasio.LASFile()
    las.well.STRT.value = float(np.nanmin(depth))
    las.well.STOP.value = float(np.nanmax(depth))
    step = float(depth[1] - depth[0]) if depth.size >= 2 else 0.0
    las.well.STEP.value = step
    las.well.NULL.value = -999.25

    header = sounding.header
    las.well.WELL.value = str(sounding.name or "")
    if header is not None:
        loc_bits = []
        if header.loca_x is not None:
            loc_bits.append(f"E{header.loca_x:.2f}")
        if header.loca_y is not None:
            loc_bits.append(f"N{header.loca_y:.2f}")
        if header.loca_crs:
            loc_bits.append(str(header.loca_crs))
        if loc_bits:
            las.well.LOC.value = " ".join(loc_bits)
        if header.water_depth_m is not None:
            # ELEV is not a default LAS 2.0 well section item — add it
            # explicitly via HeaderItem so lasio writes a fresh row.
            las.well["ELEV"] = lasio.HeaderItem(
                mnemonic="ELEV",
                unit="m",
                value=float(header.water_depth_m),
                descr="Surface elevation (water depth proxy)",
            )
        if header.started_at is not None:
            las.well.DATE.value = header.started_at.date().isoformat()
    if project_client:
        las.well.COMP.value = str(project_client)

    # DEPT first
    las.append_curve("DEPT", depth, unit="m", descr="Depth")

    for mnemonic, source, name, unit, descr in spec[1:]:
        values = _resolve_channel(sounding, (mnemonic, source, name, unit, descr))
        if values is None:
            continue
        # Pad/truncate to depth length so lasio is happy
        if values.size != depth.size:
            padded = np.full(depth.size, np.nan, dtype=np.float64)
            n = min(values.size, depth.size)
            padded[:n] = values[:n]
            values = padded
        las.append_curve(mnemonic, values, unit=unit, descr=descr)

    las.write(str(path), version=2.0)
    return path


def _resolve_channel(sounding: "CPTSounding", spec: _CurveSpec) -> np.ndarray | None:
    """Pull the values array for one curve spec entry."""
    _, source, name, _, _ = spec
    if source == "depth":
        ch = sounding.channels.get("depth")
    elif source == "raw":
        ch = sounding.channels.get(name)
    elif source == "derived":
        ch = sounding.derived.get(name)
    else:
        return None
    if ch is None:
        return None
    arr = np.asarray(ch.values, dtype=np.float64)
    return arr if arr.size > 0 else None
