"""
csv converter — directory of ``<group>.csv`` files.

Each AGS4 GROUP becomes one CSV whose first row is the pandas column
header, second row the AGS4 UNIT row, third row the TYPE row, and
subsequent rows the DATA. A ``_manifest.json`` file at the directory
root records the group order so round-trips preserve it.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["to_csv", "from_csv"]


_MANIFEST_NAME = "_manifest.json"


def to_csv(bundle: AGSBundle, path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    order: list[str] = []
    for group, df in bundle.tables.items():
        df.astype(str).to_csv(
            path / f"{group}.csv", index=False, encoding="utf-8"
        )
        order.append(group)
    (path / _MANIFEST_NAME).write_text(
        json.dumps({"groups": order}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def from_csv(path: str | Path) -> AGSBundle:
    path = Path(path)
    manifest_path = path / _MANIFEST_NAME
    if manifest_path.exists():
        order = json.loads(manifest_path.read_text(encoding="utf-8")).get(
            "groups", []
        )
    else:
        order = sorted(p.stem for p in path.glob("*.csv"))

    tables: dict[str, pd.DataFrame] = {}
    for group in order:
        csv_path = path / f"{group}.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
        tables[group] = df.astype(str)
    headings = {g: list(df.columns) for g, df in tables.items()}
    bundle = AGSBundle(tables=tables, headings=headings)
    bundle.build_unit_map()
    return bundle
