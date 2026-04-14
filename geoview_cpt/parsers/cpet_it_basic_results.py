"""
geoview_cpt.parsers.cpet_it_basic_results
============================================
Reader for CPeT-IT ``*-Basic results.xls`` (and ``*-Estimated parameters.xls``)
exports — the per-sounding analysis outputs that ship alongside the
``.cpt`` project file.

Use case: A2.5 R2 tolerance harness. Our derivation pipeline computes
qt/Rf/Bq/Ic/SBT/γ/σ_v0/u₀/σ'_v0 from raw qc/fs/u₂; the same outputs
appear in CPeT-IT's Basic Results columns. Reading them lets the test
suite assert per-sample agreement within Risk R2 tolerance
(qt ±0.1%, Ic ±0.5%, γ ±5%).

The xlsx is a flat sheet:

    r0   meta header strip ("In situ data" / "Basic output data")
    r1   column names (English, with mojibake on γ and σ symbols)
    r2+  numeric data, one row per processed sample

Korean / Greek symbols (γ, σ) come through as cp1252 mojibake but the
column position is stable across files, so we map by **position**, not
text. The header text is preserved on :attr:`BasicResultsTable.header_raw`
for tooling that wants to render the original strings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

__all__ = [
    "BasicResultsTable",
    "BasicResultsParseError",
    "parse_basic_results",
    "BASIC_RESULTS_COLUMNS",
]


class BasicResultsParseError(Exception):
    """Raised when a CPeT-IT Basic results xls cannot be parsed."""


# Stable column positions — verified against JAKO 분석결과_2nd/cpt01-Basic results.xls
BASIC_RESULTS_COLUMNS: dict[str, int] = {
    "no":         0,
    "depth":      1,
    "qc":         2,
    "fs":         3,
    "u":          4,
    "other":      5,
    "qt":         6,
    "rf":         7,
    "sbt":        8,
    "ic_sbt":     9,
    "gamma":     10,
    "sigma_v":   11,
    "u0":        12,
    "sigma_pvo": 13,
    "qt1":       14,
    "fr":        15,
    "bq":        16,
    "sbtn":      17,
    "n":         18,
    "cn":        19,
    "ic":        20,
    "qtn":       21,
    "u2":        22,
    "ib":        23,
    "mod_sbtn":  24,
    "schneider": 25,
}


@dataclass
class BasicResultsTable:
    """Parsed CPeT-IT Basic Results sheet."""

    source_path: Path
    n_samples: int
    columns: dict[str, np.ndarray] = field(default_factory=dict)
    header_raw: list[Any] = field(default_factory=list)

    def __len__(self) -> int:
        return self.n_samples

    def __contains__(self, key: str) -> bool:
        return key in self.columns

    def get(self, key: str) -> np.ndarray:
        try:
            return self.columns[key]
        except KeyError as exc:
            raise KeyError(
                f"column {key!r} not in BasicResultsTable; have "
                f"{list(self.columns)}"
            ) from exc


def parse_basic_results(path: Path | str) -> BasicResultsTable:
    """
    Read a CPeT-IT ``*-Basic results.xls`` into a
    :class:`BasicResultsTable` of numpy arrays keyed by canonical name.
    """
    p = Path(path)
    if not p.exists():
        raise BasicResultsParseError(f"file not found: {p}")

    try:
        import xlrd
    except ImportError as exc:
        raise BasicResultsParseError(f"xlrd not installed: {exc}") from exc

    try:
        wb = xlrd.open_workbook(str(p))
    except Exception as exc:
        raise BasicResultsParseError(f"cannot open {p}: {exc}") from exc

    sh = wb.sheet_by_index(0)
    if sh.nrows < 3:
        raise BasicResultsParseError(f"{p}: too few rows for Basic Results")

    header_raw = [sh.cell_value(1, c) for c in range(sh.ncols)]

    n_data = sh.nrows - 2
    columns: dict[str, np.ndarray] = {}
    for name, col_idx in BASIC_RESULTS_COLUMNS.items():
        if col_idx >= sh.ncols:
            continue
        arr = np.empty(n_data, dtype=np.float64)
        for i in range(n_data):
            v = sh.cell_value(i + 2, col_idx)
            try:
                arr[i] = float(v)
            except (TypeError, ValueError):
                arr[i] = np.nan
        columns[name] = arr

    return BasicResultsTable(
        source_path=p,
        n_samples=n_data,
        columns=columns,
        header_raw=header_raw,
    )
