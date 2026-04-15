"""
LAS converter — optional, gated on the ``las`` optional extra.

A LAS (Canadian Well Logging Standard) file holds a single
depth-indexed log, so the converter exports the SCPT group only (the
per-depth CPT row with qc / fs / u2 / qt etc.) and synthesises the
LAS header from PROJ / LOCA + SCPG metadata. Round-trip is lossy
for everything outside SCPT — if the caller needs full bundle
round-trip they should use one of the structured formats instead.

The writer imports :mod:`lasio` lazily so the rest of the converter
package stays importable when the optional dep is not installed.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from geoview_cpt.ags_convert.wrapper import AgsConvertError, AGSBundle

__all__ = ["to_las", "from_las"]


def _require_lasio():
    try:
        import lasio  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise AgsConvertError(
            "las converter requires the 'las' optional extra — "
            "install with `pip install geoview-cpt[las]` (which pulls "
            "lasio)"
        ) from exc
    return lasio


def _data_rows(df: pd.DataFrame) -> pd.DataFrame:
    return df.iloc[2:].reset_index(drop=True)


def to_las(bundle: AGSBundle, path: str | Path) -> Path:
    lasio = _require_lasio()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    scpt = bundle.tables.get("SCPT")
    if scpt is None:
        raise AgsConvertError("bundle has no SCPT group — LAS export skipped")

    data = _data_rows(scpt)
    depth_col = "SCPT_DPTH"
    if depth_col not in data.columns:
        raise AgsConvertError("SCPT group has no SCPT_DPTH column")
    depth = pd.to_numeric(data[depth_col], errors="coerce").to_numpy()

    las = lasio.LASFile()
    las.well.STRT.value = float(depth.min()) if len(depth) else 0.0
    las.well.STOP.value = float(depth.max()) if len(depth) else 0.0
    step = float(depth[1] - depth[0]) if len(depth) >= 2 else 0.0
    las.well.STEP.value = step
    las.well.NULL.value = -999.25

    loca_df = bundle.tables.get("LOCA")
    if loca_df is not None:
        loca_data = _data_rows(loca_df)
        if len(loca_data) > 0:
            las.well.WELL.value = str(loca_data.iloc[0].get("LOCA_ID", ""))

    proj_df = bundle.tables.get("PROJ")
    if proj_df is not None:
        proj_data = _data_rows(proj_df)
        if len(proj_data) > 0:
            las.well.COMP.value = str(proj_data.iloc[0].get("PROJ_CLNT", ""))

    las.add_curve("DEPT", depth, unit="m", descr="Depth")
    numeric_cols = [
        c
        for c in data.columns
        if c not in ("HEADING", "LOCA_ID", "SCPG_TESN", "SCPT_DPTH")
    ]
    unit_row = scpt.iloc[0]
    for col in numeric_cols:
        series = pd.to_numeric(data[col], errors="coerce").to_numpy()
        unit = str(unit_row.get(col, "")).strip()
        las.add_curve(col, series, unit=unit, descr=col)

    las.write(str(path), version=2.0)
    return path


def from_las(path: str | Path) -> AGSBundle:
    lasio = _require_lasio()
    path = Path(path)
    las = lasio.read(str(path))

    depth = las["DEPT"]
    loca_id = str(las.well.WELL.value) if las.well.WELL.value else "CPT01"

    rows: list[dict[str, str]] = []
    for i in range(len(depth)):
        row: dict[str, str] = {
            "HEADING":   "DATA",
            "LOCA_ID":   loca_id,
            "SCPG_TESN": "01",
            "SCPT_DPTH": f"{depth[i]:.2f}",
        }
        for curve in las.curves:
            if curve.mnemonic == "DEPT":
                continue
            value = las[curve.mnemonic][i]
            row[curve.mnemonic] = (
                "" if value is None or pd.isna(value) else f"{float(value):.2f}"
            )
        rows.append(row)

    cols = ["HEADING", "LOCA_ID", "SCPG_TESN", "SCPT_DPTH"] + [
        c.mnemonic for c in las.curves if c.mnemonic != "DEPT"
    ]
    unit_row = {"HEADING": "UNIT"}
    type_row = {"HEADING": "TYPE"}
    for col in cols[1:]:
        if col == "SCPT_DPTH":
            unit_row[col] = "m"
            type_row[col] = "2DP"
        elif col == "LOCA_ID":
            unit_row[col] = ""
            type_row[col] = "ID"
        elif col == "SCPG_TESN":
            unit_row[col] = ""
            type_row[col] = "X"
        else:
            curve = next(c for c in las.curves if c.mnemonic == col)
            unit_row[col] = str(curve.unit or "")
            type_row[col] = "2DP"

    df = pd.DataFrame([unit_row, type_row, *rows], columns=cols).astype(str)
    bundle = AGSBundle(tables={"SCPT": df}, headings={"SCPT": cols})
    bundle.build_unit_map()
    return bundle
