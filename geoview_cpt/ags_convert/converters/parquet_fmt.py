"""
parquet converter — directory of ``<group>.parquet`` files.

Parquet does not store multiple tables per file, so the converter
writes one file per AGS4 GROUP into the target directory. Group
order is recorded in ``_manifest.json`` alongside the parquet files,
matching the csv converter layout.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["to_parquet", "from_parquet"]


_MANIFEST_NAME = "_manifest.json"


def to_parquet(bundle: AGSBundle, path: str | Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    order: list[str] = []
    for group, df in bundle.tables.items():
        # Parquet stores dtypes — force string to match AGS4 semantics
        df.astype(str).to_parquet(path / f"{group}.parquet", index=False)
        order.append(group)
    (path / _MANIFEST_NAME).write_text(
        json.dumps({"groups": order}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def from_parquet(path: str | Path) -> AGSBundle:
    path = Path(path)
    manifest_path = path / _MANIFEST_NAME
    if manifest_path.exists():
        order = json.loads(manifest_path.read_text(encoding="utf-8")).get(
            "groups", []
        )
    else:
        order = sorted(p.stem for p in path.glob("*.parquet"))

    tables: dict[str, pd.DataFrame] = {}
    for group in order:
        p = path / f"{group}.parquet"
        if not p.exists():
            continue
        tables[group] = pd.read_parquet(p).astype(str)
    headings = {g: list(df.columns) for g, df in tables.items()}
    bundle = AGSBundle(tables=tables, headings=headings)
    bundle.build_unit_map()
    return bundle
