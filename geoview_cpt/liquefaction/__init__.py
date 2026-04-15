"""
geoview_cpt.liquefaction
================================
CPT-based liquefaction triggering + severity indices (Phase A-2 A2.10/A2.11).

Four methods implemented, each self-contained and pure-function:

    robertson_wride_1998    CRR from Qtn/Ic + KSE cutoff at Ic > 2.6
    youd_2001               NCEER workshop update (MSF via Youd 2001)
    boulanger_idriss_2014   B&I 2014 CPT-based (Kσ, Kα corrections)
    lpi_lsn                 Iwasaki 1986 Liquefaction Potential Index +
                            Tonkin & Taylor Liquefaction Severity Number

All four consume ``EarthquakeScenario`` and return
``LiquefactionProfile`` (per-depth CRR/CSR/FS + classification label).
"""
from __future__ import annotations

from geoview_cpt.liquefaction.common import (
    EarthquakeScenario,
    LiquefactionCase,
    LiquefactionProfile,
    LiquefactionResult,
)
from geoview_cpt.liquefaction.lpi_lsn import compute_lpi, compute_lsn
from geoview_cpt.liquefaction.boulanger_idriss_2014 import (
    boulanger_idriss_2014_crr,
    triggering_boulanger_idriss_2014,
)
from geoview_cpt.liquefaction.robertson_wride_1998 import (
    CLAY_LIKE_IC_THRESHOLD,
    robertson_wride_1998_crr,
    triggering_robertson_wride_1998,
)
from geoview_cpt.liquefaction.youd_2001 import (
    msf_youd_2001,
    triggering_youd_2001,
)

__all__ = [
    "EarthquakeScenario",
    "LiquefactionCase",
    "LiquefactionProfile",
    "LiquefactionResult",
    "CLAY_LIKE_IC_THRESHOLD",
    "robertson_wride_1998_crr",
    "triggering_robertson_wride_1998",
    "msf_youd_2001",
    "triggering_youd_2001",
    "boulanger_idriss_2014_crr",
    "triggering_boulanger_idriss_2014",
    "compute_lpi",
    "compute_lsn",
]
