"""
geoview_cpt.ags_convert.kingdom
===================================
Kingdom AGS4 Bridge — Phase A-4 Week 16 A4.0.

Kingdom (the SeisWare-derived geoscientific viewer used in marine
geophysics) consumes AGS4 files but only understands a subset of the
v4.1.1 dictionary: project metadata + CPT body + auto-derived
stratigraphy. Drill-hole, lab-sample, and SPT data live in a
separate GI workflow and are intentionally **excluded** from the
Kingdom drop.

This package owns that filtering step. The A-3 writer produces a
full-fat AGS4 bundle; :func:`build_kingdom_subset` strips it to the
groups Kingdom expects and pins the CRS to a Kingdom-acceptable
value.

Public API::

    build_kingdom_subset(bundle, *, project_meta, crs)
    write_kingdom_ags(sounding, path, *, project_meta, crs)
    KINGDOM_GROUPS
    EXCLUDED_GROUPS

Week 17–18 will add the Kingdom companion formats (LAS, checkshot,
location CSV) and the ``09_kingdom/`` folder assembly under A4.1–A4.7.
"""
from __future__ import annotations

from geoview_cpt.ags_convert.kingdom.checkshot import (
    CHECKSHOT_COLUMNS,
    SCPTSoundingPicks,
    build_checkshot_csv,
    build_checkshot_directory,
)
from geoview_cpt.ags_convert.kingdom.las_export import (
    DEFAULT_CURVES,
    build_kingdom_las,
)
from geoview_cpt.ags_convert.kingdom.location import (
    LOCATION_COLUMNS,
    build_location_csv,
    build_location_csv_from_bundles,
)
from geoview_cpt.ags_convert.kingdom.subset import (
    DEFAULT_KINGDOM_CRS,
    EXCLUDED_GROUPS,
    KINGDOM_GROUPS,
    build_kingdom_subset,
    write_kingdom_ags,
)

__all__ = [
    # subset
    "KINGDOM_GROUPS",
    "EXCLUDED_GROUPS",
    "DEFAULT_KINGDOM_CRS",
    "build_kingdom_subset",
    "write_kingdom_ags",
    # las
    "DEFAULT_CURVES",
    "build_kingdom_las",
    # checkshot
    "CHECKSHOT_COLUMNS",
    "SCPTSoundingPicks",
    "build_checkshot_csv",
    "build_checkshot_directory",
    # location
    "LOCATION_COLUMNS",
    "build_location_csv",
    "build_location_csv_from_bundles",
]
