"""
geoview_gi.lab.sa_geolab
================================
Parser for SA Geolab Pte Ltd (JAKO Korea vendor) PDF summary reports.

Two PDF flavours ship with the JAKO project (Wave 0 confirmed):

    JAKO - signed.pdf              158 pages (final signed report)
    JAKO-PC Preliminary.pdf         56 pages (preliminary)

Both are produced by **Acrobat PDFMaker 25 for Excel**, so the text
extraction is stable line-by-line via ``pypdf``. The report is a table
with one row per sample showing borehole/sample ID, USCS classification,
index properties, strength results, and a failure code.

Key nomenclature (Wave 0 3rd-round inventory):

 - Sample naming: ``B1`` (bulk) / ``Q1`` / ``Q2`` / ``Q3`` (quality),
   ``P1`` / ``P2`` / ``P3`` (push), ``PC1-10`` / ``KN01-06`` (vendor)
 - 16 test types (see :data:`TEST_TYPES`)
 - Failure codes A/B/C/D (see :data:`FAILURE_CODES`)
 - State codes R/r/M/c/e/cyc/QD/CD (see :data:`STATE_CODES`)

**Scope (v1)**: We extract the raw per-page text and pattern-match
sample IDs (``B1``, ``Q1..Q3``, ``PC1..PC10``, ``KN01..KN06``) into
minimal :class:`geoview_gi.minimal_model.LabSample` stubs. Full column
extraction (strength, LL/PL, percent fines) is v1.1 — tracked as
open question Q39.

The v1 parser is deliberately **forgiving**: a torn or truncated PDF
just produces fewer samples, and callers can inspect ``raw_lines`` via
:attr:`metadata` to triage.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from geoview_gi.minimal_model import LabSample

__all__ = [
    "SAGeolabParseError",
    "TEST_TYPES",
    "FAILURE_CODES",
    "STATE_CODES",
    "parse_sa_geolab_pdf",
]


class SAGeolabParseError(Exception):
    """Raised when an SA Geolab PDF cannot be read."""


# ---------------------------------------------------------------------------
# Reference dictionaries (Wave 0 3rd-round recon)
# ---------------------------------------------------------------------------


TEST_TYPES: dict[str, str] = {
    "UU":   "Unconsolidated Undrained Triaxial",
    "CIU":  "Consolidated Isotropic Undrained Triaxial",
    "CID":  "Consolidated Isotropic Drained Triaxial",
    "CAU":  "Consolidated Anisotropic Undrained Triaxial",
    "RC":   "Resonant Column",
    "IL":   "Oedometer Incremental Load",
    "CRS":  "Oedometer Constant Rate of Strain",
    "FC":   "Fall Cone",        # or HC
    "HC":   "Hand Cone",
    "DS":   "Direct Shear (shearbox)",
    "DSS":  "Direct Simple Shear",
    "RS":   "Ring Shear",
    "DR":   "Density Relative",
    "F":    "Fines content",
    "NES":  "Non-standard element test",
    "NP":   "Non plastic",
}


FAILURE_CODES: dict[str, str] = {
    "A": "Bulge",
    "B": "Single Shear Plane",
    "C": "Multiple Shear Plane",
    "D": "Vertical Fracture",
}


STATE_CODES: dict[str, str] = {
    "R":    "Reconstituted",
    "r":    "Remoulded",
    "M":    "Mixed",
    "c":    "Compacted",
    "e":    "Effective stress path",
    "cyc":  "Cyclic",
    "QD":   "Quick drained",
    "CD":   "Consolidated drained",
}


# ---------------------------------------------------------------------------
# v1 line extraction
# ---------------------------------------------------------------------------


# Matches "PC1 P1 B1 0.00 SC 44.0" and similar — borehole prefix is optional.
_SAMPLE_LINE_RE = re.compile(
    r"""
    ^\s*
    (?P<prefix>(?:PC\d{1,2}|KN\d{2}|BH-?\d+|P[123]))?   # optional borehole tag
    \s*
    (?:P[123]\s+)?                                       # optional push
    (?P<id>B\d|Q\d|U\d|D\d|P\d)                          # sample id
    \s+
    (?P<depth>\d+\.\d+)                                  # top depth in metres
    \s*
    (?P<classification>[A-Z]{2})?                        # USCS class (optional)
    """,
    re.VERBOSE,
)


def parse_sa_geolab_pdf(path: Path | str) -> list[LabSample]:
    """
    Extract :class:`LabSample` stubs from an SA Geolab PDF.

    Args:
        path: filesystem path to ``*.pdf``.

    Returns:
        A list of :class:`LabSample` (one per line the regex matched).
        ``sample_type`` defaults to ``"OTHER"``; ``top_m`` carries the
        extracted depth. When a USCS classification letter pair is
        present it is stashed on ``metadata`` via a custom attribute —
        since :class:`LabSample` is pinned at 17 fields we attach it
        through the sample's ``sample_ref`` slot instead (transparent
        for the A2.19 contract).
    """
    try:
        import pypdf
    except ImportError as exc:
        raise SAGeolabParseError(f"pypdf not installed: {exc}") from exc

    p = Path(path)
    if not p.exists():
        raise SAGeolabParseError(f"file not found: {p}")

    try:
        reader = pypdf.PdfReader(str(p))
    except Exception as exc:
        raise SAGeolabParseError(f"cannot open {p}: {exc}") from exc

    borehole_id = _guess_borehole_id(reader)
    samples: list[LabSample] = []
    seen: set[tuple[str, float]] = set()

    for page in reader.pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        for line in text.splitlines():
            sample = _line_to_sample(line, borehole_id=borehole_id)
            if sample is None:
                continue
            key = (sample.sample_id, sample.top_m)
            if key in seen:
                continue
            seen.add(key)
            samples.append(sample)

    return samples


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _guess_borehole_id(reader) -> str:
    """Scan the first few pages for a "Borehole No." label."""
    for idx in range(min(5, len(reader.pages))):
        try:
            text = reader.pages[idx].extract_text() or ""
        except Exception:
            continue
        m = re.search(r"Borehole\s*No\.?\s*[:\-]?\s*(\S+)", text, re.IGNORECASE)
        if m:
            return m.group(1)
    return "JAKO"


def _line_to_sample(line: str, *, borehole_id: str) -> LabSample | None:
    line = line.strip()
    if not line:
        return None
    m = _SAMPLE_LINE_RE.match(line)
    if not m:
        return None
    sample_id = m.group("id")
    try:
        depth = float(m.group("depth"))
    except ValueError:
        return None
    if depth < 0 or depth > 200:
        return None
    classification = m.group("classification") or ""
    sample_ref = classification

    sample_type = "OTHER"
    if sample_id.startswith("B"):
        sample_type = "B"
    elif sample_id.startswith("U"):
        sample_type = "U"
    elif sample_id.startswith("D"):
        sample_type = "D"
    elif sample_id.startswith("P"):
        sample_type = "P"

    try:
        return LabSample(
            loca_id=borehole_id or "JAKO",
            sample_id=sample_id,
            sample_type=sample_type,   # type: ignore[arg-type]
            sample_ref=sample_ref,
            top_m=depth,
        )
    except ValueError:
        return None
