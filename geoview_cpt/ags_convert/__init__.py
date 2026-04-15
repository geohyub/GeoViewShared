"""
geoview_cpt.ags_convert
================================
AGS4 conversion engine — Phase A-3.

Week 12 (A3.1 + A3.6) lands the first layer: a thin wrapper around
``python-ags4==1.0.0`` that normalizes the library's
``(tables, headings)`` tuple into a single :class:`AGSBundle` and
adds a canonical load/dump API the rest of the Phase A-3 code will
build on.

Out of scope for Week 12:

 - AGS4 writer from :class:`CPTProject` / :class:`CPTSounding`
   (Week 13 A3.2)
 - Rule 1-20 validator wrapper (Week 14 A3.3)
 - xlsx / csv / las format converters (Week 15 A3.4)
 - ``geoview-ags`` CLI (Week 15 A3.5)

Public API:

    load_ags            AGS4 file → AGSBundle
    dump_ags            AGSBundle → AGS4 file (round-trip partner)
    AGSBundle           ``tables`` + ``headings`` + ``units`` + ``types``
                         container (dataclass)
    STANDARD_DICTIONARY python-ags4 v4.1.1 standard dictionary path
"""
from __future__ import annotations

from geoview_cpt.ags_convert.jako_audit import (
    AGS4_CORE_GROUPS,
    AuditReport,
    audit_missing_fields,
)
from geoview_cpt.ags_convert.wrapper import (
    STANDARD_DICTIONARY_V4_1_1,
    AGSBundle,
    AgsConvertError,
    dump_ags,
    load_ags,
)
from geoview_cpt.ags_convert.writer import (
    OnMissingPolicy,
    ProjectMeta,
    build_core_bundle,
    write_ags,
)

__all__ = [
    "AGSBundle",
    "AgsConvertError",
    "load_ags",
    "dump_ags",
    "STANDARD_DICTIONARY_V4_1_1",
    "AGS4_CORE_GROUPS",
    "AuditReport",
    "audit_missing_fields",
    "OnMissingPolicy",
    "ProjectMeta",
    "build_core_bundle",
    "write_ags",
]
