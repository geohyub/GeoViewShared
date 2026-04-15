"""
geoview_cpt.ags_convert.wrapper
================================
Thin, canonical wrapper around ``python-ags4==1.0.0``.

Scope (Week 12 A3.1):

 - :class:`AGSBundle` — a single dataclass holding the four state
   pieces a GeoView consumer ever needs: the per-GROUP DataFrames,
   the column ordering per GROUP, and the UNIT / TYPE rows as
   dict[HEADING → string] so downstream code doesn't re-parse them.
 - :func:`load_ags` — read a ``.ags`` file via
   ``python_ags4.AGS4.AGS4_to_dataframe`` and materialize an
   :class:`AGSBundle`.
 - :func:`dump_ags` — write an :class:`AGSBundle` via
   ``python_ags4.AGS4.dataframe_to_AGS4``. Round-trip partner of
   :func:`load_ags`.

Out of scope for Week 12:

 - Rule 1-20 validator (Week 14 A3.3)
 - CPTProject → AGS4 writer (Week 13 A3.2)
 - xlsx / csv / las converters (Week 15 A3.4)

The wrapper does NOT touch :mod:`geoview_pyside6` or
:mod:`geoview_common` so the Phase A-2 contract is preserved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "AGSBundle",
    "AgsConvertError",
    "STANDARD_DICTIONARY_V4_1_1",
    "load_ags",
    "dump_ags",
]


class AgsConvertError(Exception):
    """Raised when a ``.ags`` file cannot be read or written."""


# ---------------------------------------------------------------------------
# Standard dictionary location (python-ags4 bundled v4.1.1)
# ---------------------------------------------------------------------------


def _standard_dictionary_path() -> Path:
    """
    Resolve the path to python-ags4's bundled AGS4 v4.1.1 standard
    dictionary. Returned as a ``pathlib.Path`` so callers can feed it
    into ``check_file`` (Week 14) without re-importing the library.
    """
    try:
        import python_ags4
    except ImportError as exc:
        raise AgsConvertError(
            "python-ags4 is not installed — add 'python-ags4==1.0.0' to "
            "pyproject.toml dependencies"
        ) from exc
    base = Path(python_ags4.__file__).resolve().parent
    candidate = base / "Standard_dictionary_v4_1_1.ags"
    if candidate.exists():
        return candidate
    # Fall back to 4_1 if 4_1_1 is ever removed
    fallback = base / "Standard_dictionary_v4_1.ags"
    if fallback.exists():
        return fallback
    raise AgsConvertError(
        f"python-ags4 standard dictionary not found next to {base}"
    )


STANDARD_DICTIONARY_V4_1_1: Path = _standard_dictionary_path()


# ---------------------------------------------------------------------------
# Bundle
# ---------------------------------------------------------------------------


@dataclass
class AGSBundle:
    """
    Canonical AGS4 container for the GeoView conversion engine.

    Attributes:
        tables:    ``{GROUP_NAME: pd.DataFrame}`` — each DataFrame has
                   ``HEADING`` as its first column and contains three
                   row kinds:

                       UNIT    → row 0
                       TYPE    → row 1
                       DATA    → rows 2..N

                   This matches what ``python_ags4.AGS4_to_dataframe``
                   returns so the round-trip is free of structural
                   reshapes.

        headings:  ``{GROUP_NAME: list[str]}`` — canonical column order
                   per GROUP. python-ags4 returns this alongside the
                   tables; we store it so :func:`dump_ags` can feed it
                   back without recomputing.

        units:     Convenience cache of the UNIT row extracted per
                   ``(group, heading)`` as a plain dict. Populated
                   lazily by :meth:`AGSBundle.build_unit_map` so tests
                   don't pay the cost when they only care about
                   DataFrames.

        types:     Same as ``units`` but for the TYPE row (PC / X /
                   XN / etc.).

        source_path: Original file, if :func:`load_ags` was used.
    """

    tables: dict[str, "pd.DataFrame"] = field(default_factory=dict)
    headings: dict[str, list[str]] = field(default_factory=dict)
    units: dict[str, dict[str, str]] = field(default_factory=dict)
    types: dict[str, dict[str, str]] = field(default_factory=dict)
    source_path: Path | None = None

    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.tables)

    def __contains__(self, group: str) -> bool:
        return group in self.tables

    def groups(self) -> list[str]:
        return list(self.tables.keys())

    def data_rows(self, group: str) -> "pd.DataFrame":
        """
        Return just the DATA rows of ``group`` (skipping UNIT and TYPE).
        Keeps the ``HEADING`` column intact so the caller can still
        filter on it.
        """
        if group not in self.tables:
            raise KeyError(f"group {group!r} not in bundle")
        df = self.tables[group]
        return df[df["HEADING"] == "DATA"].reset_index(drop=True)

    # ------------------------------------------------------------------

    def build_unit_map(self) -> None:
        """Populate :attr:`units` / :attr:`types` from the tables."""
        self.units.clear()
        self.types.clear()
        for group, df in self.tables.items():
            unit_row = df[df["HEADING"] == "UNIT"]
            type_row = df[df["HEADING"] == "TYPE"]
            if not unit_row.empty:
                self.units[group] = {
                    col: str(unit_row.iloc[0][col])
                    for col in df.columns if col != "HEADING"
                }
            if not type_row.empty:
                self.types[group] = {
                    col: str(type_row.iloc[0][col])
                    for col in df.columns if col != "HEADING"
                }


# ---------------------------------------------------------------------------
# load / dump
# ---------------------------------------------------------------------------


def load_ags(path: Path | str) -> AGSBundle:
    """
    Read a ``.ags`` file into an :class:`AGSBundle`.

    Delegates to ``python_ags4.AGS4.AGS4_to_dataframe`` for the actual
    parse so we inherit upstream format-spec compliance. The wrapper
    only repackages the result into the canonical :class:`AGSBundle`.

    Args:
        path: filesystem path to the ``.ags`` file.

    Raises:
        AgsConvertError:  on missing file or python-ags4 exceptions.
    """
    p = Path(path)
    if not p.exists():
        raise AgsConvertError(f"AGS file not found: {p}")

    try:
        from python_ags4 import AGS4
    except ImportError as exc:
        raise AgsConvertError(
            "python-ags4 not installed"
        ) from exc

    try:
        tables, headings = AGS4.AGS4_to_dataframe(p)
    except Exception as exc:
        raise AgsConvertError(f"python-ags4 load failed for {p}: {exc}") from exc

    bundle = AGSBundle(
        tables={k: v for k, v in tables.items()},
        headings={k: list(v) for k, v in headings.items()},
        source_path=p,
    )
    bundle.build_unit_map()
    return bundle


def dump_ags(bundle: AGSBundle, path: Path | str) -> Path:
    """
    Write an :class:`AGSBundle` back to a ``.ags`` file.

    Delegates to ``python_ags4.AGS4.dataframe_to_AGS4``. The wrapper
    ensures headings are preserved column-order-wise so the load→dump
    round-trip keeps the same on-disk layout.

    Returns the resolved output path.
    """
    if not isinstance(bundle, AGSBundle):
        raise TypeError(
            f"dump_ags expects AGSBundle, got {type(bundle).__name__}"
        )
    if not bundle.tables:
        raise AgsConvertError("cannot dump an empty AGSBundle")

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    try:
        from python_ags4 import AGS4
    except ImportError as exc:
        raise AgsConvertError("python-ags4 not installed") from exc

    # python-ags4 mutates the ``tables`` and ``headings`` arguments in
    # place (sorts them), so we hand over shallow copies to keep the
    # caller's bundle pristine.
    tables_copy = {k: v.copy() for k, v in bundle.tables.items()}
    headings_copy = {k: list(v) for k, v in bundle.headings.items()}

    try:
        AGS4.dataframe_to_AGS4(tables_copy, headings_copy, out)
    except Exception as exc:
        raise AgsConvertError(
            f"python-ags4 dump failed for {out}: {exc}"
        ) from exc

    return out
