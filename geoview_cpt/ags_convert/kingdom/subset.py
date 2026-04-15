"""
Kingdom AGS4 subset filter — A-3 bundle → Kingdom-ready bundle.

Approach (per the Phase A-4 Week 16 plan): **never** re-implement the
A-3 writer logic. Take a bundle produced by
:func:`geoview_cpt.ags_convert.write_ags` (or already-loaded with
:func:`load_ags`), strip the GROUPs Kingdom does not consume, pin
``LOCA_GREF`` to the Kingdom project CRS, and rebuild the global
UNIT / TYPE dictionaries against the surviving groups.

Validation is delegated to the Week 14 A3.3 validator so the Kingdom
drop inherits Rule 1-20 cleanliness for free.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Iterable

import pandas as pd

from geoview_cpt.ags_convert.groups import (
    build_type_dictionary,
    build_unit_dictionary,
)
from geoview_cpt.ags_convert.wrapper import AGSBundle, AgsConvertError, dump_ags

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.writer import ProjectMeta
    from geoview_cpt.model import CPTSounding

__all__ = [
    "KINGDOM_GROUPS",
    "EXCLUDED_GROUPS",
    "DEFAULT_KINGDOM_CRS",
    "build_kingdom_subset",
    "write_kingdom_ags",
]


KINGDOM_GROUPS: tuple[str, ...] = (
    "PROJ",
    "TRAN",
    "UNIT",
    "TYPE",
    "LOCA",
    "SCPG",
    "SCPT",
    "SCPP",
    "GEOL",
)
"""GROUPs that survive the Kingdom filter, in canonical AGS4 emission
order."""


EXCLUDED_GROUPS: frozenset[str] = frozenset({"HOLE", "SAMP", "ISPT"})
"""GROUPs intentionally dropped — Kingdom is a geoscientific viewer
and the GI borehole / sample / SPT records belong in a separate
HoleBASE drop."""


# Kingdom default CRSes — the marine team uses EPSG:5179 (Korea
# Central Belt 2010 / KGD2002) for nearshore and EPSG:4326 (WGS 84)
# for offshore wind farm sites. Anything else must be supplied
# explicitly via ``crs=`` or ``project_meta.crs``.
DEFAULT_KINGDOM_CRS: tuple[str, ...] = ("EPSG:5179", "EPSG:4326")


def build_kingdom_subset(
    bundle: AGSBundle,
    *,
    project_meta: "ProjectMeta | None" = None,
    crs: str | None = None,
) -> AGSBundle:
    """
    Filter ``bundle`` to the Kingdom-consumable subset.

    Args:
        bundle:        any :class:`AGSBundle` — typically the result of
                       :func:`load_ags` on a Phase A-3 write_ags
                       output.
        project_meta:  optional :class:`ProjectMeta`. When supplied
                       its ``crs`` field is used as the LOCA_GREF
                       fallback.
        crs:           explicit Kingdom CRS string (e.g.
                       ``"EPSG:5179"``). Wins over both
                       ``project_meta.crs`` and the original bundle's
                       ``LOCA_GREF`` value.

    Returns:
        A new :class:`AGSBundle` containing only the
        :data:`KINGDOM_GROUPS`. UNIT / TYPE dictionaries are
        regenerated from the surviving groups so they no longer carry
        units only used by HOLE / SAMP / ISPT.

    Raises:
        AgsConvertError: when the bundle has no LOCA group, or when
                         the resulting LOCA_GREF cell would be blank
                         (Kingdom requires a CRS — there is no
                         meaningful default).
    """
    if "LOCA" not in bundle.tables:
        raise AgsConvertError(
            "Kingdom subset requires a LOCA group in the source bundle"
        )

    # Resolve the CRS — explicit > project_meta > existing LOCA_GREF
    target_crs = (crs or "").strip()
    if not target_crs and project_meta is not None:
        target_crs = (project_meta.crs or "").strip()

    loca_df = bundle.tables["LOCA"].copy()
    if not target_crs:
        # Try to inherit from the existing LOCA_GREF cell
        existing = ""
        if "LOCA_GREF" in loca_df.columns and len(loca_df) > 2:
            existing = str(loca_df.iloc[2].get("LOCA_GREF", "")).strip()
        target_crs = existing
    if not target_crs:
        raise AgsConvertError(
            "Kingdom subset requires LOCA_GREF (CRS). Pass crs=... or "
            "set project_meta.crs — Kingdom has no safe default."
        )
    if "LOCA_GREF" not in loca_df.columns:
        raise AgsConvertError(
            "LOCA group missing LOCA_GREF heading — cannot pin Kingdom CRS"
        )
    # Stamp the CRS into every DATA row of LOCA
    loca_df = _stamp_column(loca_df, "LOCA_GREF", target_crs)

    surviving: dict[str, pd.DataFrame] = {}
    for group in KINGDOM_GROUPS:
        if group in ("UNIT", "TYPE"):
            # Regenerated below
            continue
        if group == "LOCA":
            surviving["LOCA"] = loca_df
            continue
        df = bundle.tables.get(group)
        if df is not None:
            surviving[group] = df.copy()

    # Regenerate the global UNIT / TYPE dictionaries against the
    # filtered groups so we don't ship units for excluded groups.
    used_units = _collect_units(surviving)
    used_types = _collect_types(surviving)
    unit_df = build_unit_dictionary(used_units)
    type_df = build_type_dictionary(used_types)

    ordered: dict[str, pd.DataFrame] = {}
    for group in KINGDOM_GROUPS:
        if group == "UNIT":
            ordered["UNIT"] = unit_df
        elif group == "TYPE":
            ordered["TYPE"] = type_df
        elif group in surviving:
            ordered[group] = surviving[group]

    headings = {g: list(df.columns) for g, df in ordered.items()}
    new_bundle = AGSBundle(tables=ordered, headings=headings)
    new_bundle.build_unit_map()
    return new_bundle


def write_kingdom_ags(
    sounding: "CPTSounding",
    path: Path | str,
    *,
    project_meta: "ProjectMeta | None" = None,
    crs: str | None = None,
) -> Path:
    """
    Convenience: write a sounding straight to a Kingdom-ready ``.ags``
    file in one call.

    Equivalent to::

        from geoview_cpt.ags_convert import write_ags, load_ags
        full = tmp / "full.ags"
        write_ags(sounding, full, project_meta=project_meta)
        bundle = load_ags(full)
        kingdom = build_kingdom_subset(bundle, project_meta=project_meta, crs=crs)
        return dump_ags(kingdom, path)
    """
    from geoview_cpt.ags_convert.writer import write_ags  # local — avoid cycle
    from geoview_cpt.ags_convert.wrapper import load_ags

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write the full-fat AGS4 to a tempfile, then filter.
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        full_path = Path(td) / "full.ags"
        write_ags(sounding, full_path, project_meta=project_meta)
        full_bundle = load_ags(full_path)
        kingdom_bundle = build_kingdom_subset(
            full_bundle, project_meta=project_meta, crs=crs
        )
    return dump_ags(kingdom_bundle, path)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _stamp_column(df: pd.DataFrame, col: str, value: str) -> pd.DataFrame:
    """Set ``col`` to ``value`` on every DATA row of ``df``. UNIT / TYPE
    rows are left untouched."""
    df = df.copy()
    if col not in df.columns or len(df) <= 2:
        return df
    df.loc[df["HEADING"] == "DATA", col] = value
    return df


def _collect_units(tables: Iterable[pd.DataFrame] | dict[str, pd.DataFrame]) -> set[str]:
    out: set[str] = set()
    items = tables.values() if isinstance(tables, dict) else tables
    for df in items:
        if df.empty:
            continue
        unit_row = df.iloc[0]
        for col, value in unit_row.items():
            if col == "HEADING":
                continue
            text = str(value).strip()
            if text:
                out.add(text)
    return out


def _collect_types(tables: Iterable[pd.DataFrame] | dict[str, pd.DataFrame]) -> set[str]:
    out: set[str] = set()
    items = tables.values() if isinstance(tables, dict) else tables
    for df in items:
        if len(df) < 2:
            continue
        type_row = df.iloc[1]
        for col, value in type_row.items():
            if col == "HEADING":
                continue
            text = str(value).strip()
            if text:
                out.add(text)
    return out
