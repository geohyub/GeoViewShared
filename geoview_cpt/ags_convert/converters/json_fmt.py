"""
json converter — single JSON file encoding the whole bundle.

Schema::

    {
      "schema_version": "1.0",
      "groups": {
        "PROJ": {
          "columns": ["HEADING", "PROJ_ID", ...],
          "rows":    [["UNIT", ...], ["TYPE", "ID", ...], ["DATA", "P01", ...]]
        },
        ...
      },
      "order": ["PROJ", "TRAN", ...]
    }

Rows are stored as a list-of-lists so the JSON stays compact and
column-order-preserving. On read the order is restored from the
``order`` key.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from geoview_cpt.ags_convert.wrapper import AGSBundle

__all__ = ["to_json", "from_json"]


SCHEMA_VERSION = "1.0"


def to_json(bundle: AGSBundle, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    groups_out: dict[str, dict] = {}
    order: list[str] = []
    for group, df in bundle.tables.items():
        df = df.astype(str)
        groups_out[group] = {
            "columns": list(df.columns),
            "rows": df.values.tolist(),
        }
        order.append(group)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "groups": groups_out,
        "order": order,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def from_json(path: str | Path) -> AGSBundle:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    order = payload.get("order") or list(payload.get("groups", {}).keys())
    tables: dict[str, pd.DataFrame] = {}
    for group in order:
        entry = payload["groups"][group]
        df = pd.DataFrame(entry["rows"], columns=entry["columns"]).astype(str)
        tables[group] = df
    headings = {g: list(df.columns) for g, df in tables.items()}
    bundle = AGSBundle(tables=tables, headings=headings)
    bundle.build_unit_map()
    return bundle
