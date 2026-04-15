"""
xlsx converter — one Excel sheet per AGS4 GROUP.

The AGS4 row ordering (UNIT row, TYPE row, DATA rows with a leading
``HEADING`` column) is preserved literally in the sheet: the first
Excel row is the pandas column header (group headings), the first
sheet data row is the UNIT row, the second is TYPE, and rows 3+ are
DATA. This keeps the converter a pure serialisation step — no data
loss or column re-ordering.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["to_xlsx", "from_xlsx"]


def to_xlsx(bundle: AGSBundle, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for group, df in bundle.tables.items():
            # Excel sheet names cap at 31 chars; AGS4 group names are ≤4.
            df.astype(str).to_excel(writer, sheet_name=group, index=False)
    return path


def from_xlsx(path: str | Path) -> AGSBundle:
    path = Path(path)
    sheets = pd.read_excel(path, sheet_name=None, dtype=str)
    tables: dict[str, pd.DataFrame] = {}
    for name, df in sheets.items():
        df = df.fillna("").astype(str)
        tables[name] = df
    headings = {g: list(df.columns) for g, df in tables.items()}
    bundle = AGSBundle(tables=tables, headings=headings)
    bundle.build_unit_map()
    return bundle
