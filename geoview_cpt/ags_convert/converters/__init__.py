"""
geoview_cpt.ags_convert.converters
======================================
Bidirectional format converters — Phase A-3 Week 15 A3.4.

Each module in this package exposes a ``to_<format>(bundle, path)``
writer and a ``from_<format>(path) -> AGSBundle`` reader. The
``AGSBundle`` class is the canonical in-memory representation; a
converter round-trip is::

    bundle_v1 = load_ags("source.ags")
    to_xlsx(bundle_v1, "out.xlsx")
    bundle_v2 = from_xlsx("out.xlsx")
    assert_bundle_equal(bundle_v1, bundle_v2)   # semantic equality

Formats shipped in Week 15:

    xlsx        one sheet per AGS4 GROUP
    csv         one .csv file per group inside an output directory
    json        single JSON file with nested ``{group: {columns,
                unit, type, data}}`` structure
    parquet     directory of parquet files, one per group

LAS support (``lasio``) ships as an optional extra in
``pyproject.toml``; the module is importable but raises at call
time when ``lasio`` is not installed.

Top-level dispatch::

    from geoview_cpt.ags_convert.converters import convert

    convert("src.ags", "out.xlsx", fmt="xlsx")
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from geoview_cpt.ags_convert.converters.csv_fmt import from_csv, to_csv
from geoview_cpt.ags_convert.converters.json_fmt import from_json, to_json
from geoview_cpt.ags_convert.converters.parquet_fmt import (
    from_parquet,
    to_parquet,
)
from geoview_cpt.ags_convert.converters.xlsx_fmt import from_xlsx, to_xlsx
from geoview_cpt.ags_convert.wrapper import AGSBundle, dump_ags, load_ags

__all__ = [
    "to_xlsx",
    "from_xlsx",
    "to_csv",
    "from_csv",
    "to_json",
    "from_json",
    "to_parquet",
    "from_parquet",
    "convert",
    "assert_bundle_equal",
]


Format = Literal["ags", "xlsx", "csv", "json", "parquet", "las"]

_WRITERS = {
    "xlsx": to_xlsx,
    "csv": to_csv,
    "json": to_json,
    "parquet": to_parquet,
}
_READERS = {
    "xlsx": from_xlsx,
    "csv": from_csv,
    "json": from_json,
    "parquet": from_parquet,
}


def _infer_format(path: Path) -> Format:
    suffix = path.suffix.lower().lstrip(".")
    if suffix == "ags":
        return "ags"
    if suffix in ("xlsx", "xls"):
        return "xlsx"
    if suffix == "csv":
        return "csv"
    if suffix == "json":
        return "json"
    if suffix == "parquet":
        return "parquet"
    if suffix == "las":
        return "las"
    if path.is_dir():
        # Directory-based formats default to csv if not hinted
        return "csv"
    raise ValueError(f"cannot infer format from path {path!s}")


def convert(
    src: str | Path,
    dst: str | Path,
    *,
    src_format: Format | None = None,
    dst_format: Format | None = None,
) -> Path:
    """
    Convert ``src`` to ``dst`` by round-tripping through
    :class:`AGSBundle`. Either end can be ``.ags`` or any of the
    supported formats.
    """
    src = Path(src)
    dst = Path(dst)
    src_fmt = src_format or _infer_format(src)
    dst_fmt = dst_format or _infer_format(dst)

    if src_fmt == "ags":
        bundle = load_ags(src)
    elif src_fmt == "las":
        from geoview_cpt.ags_convert.converters.las_fmt import from_las

        bundle = from_las(src)
    else:
        reader = _READERS.get(src_fmt)
        if reader is None:
            raise ValueError(f"no reader for format {src_fmt!r}")
        bundle = reader(src)

    if dst_fmt == "ags":
        return dump_ags(bundle, dst)
    if dst_fmt == "las":
        from geoview_cpt.ags_convert.converters.las_fmt import to_las

        return to_las(bundle, dst)
    writer = _WRITERS.get(dst_fmt)
    if writer is None:
        raise ValueError(f"no writer for format {dst_fmt!r}")
    return writer(bundle, dst)


def assert_bundle_equal(
    left: AGSBundle,
    right: AGSBundle,
    *,
    groups: list[str] | None = None,
) -> None:
    """
    Semantic bundle equality check — per-group DataFrame value
    comparison. Used by converter round-trip tests.
    """
    left_groups = set(left.tables.keys())
    right_groups = set(right.tables.keys())
    if groups is None:
        if left_groups != right_groups:
            raise AssertionError(
                f"bundle group sets differ: "
                f"left={sorted(left_groups)}, right={sorted(right_groups)}"
            )
        groups = sorted(left_groups)
    for g in groups:
        l = left.tables[g].reset_index(drop=True).astype(str)
        r = right.tables[g].reset_index(drop=True).astype(str)
        if list(l.columns) != list(r.columns):
            raise AssertionError(
                f"{g} columns differ: {list(l.columns)} vs {list(r.columns)}"
            )
        if l.shape != r.shape:
            raise AssertionError(
                f"{g} shapes differ: {l.shape} vs {r.shape}"
            )
        for col in l.columns:
            if not (l[col] == r[col]).all():
                raise AssertionError(
                    f"{g}.{col} values differ"
                )
