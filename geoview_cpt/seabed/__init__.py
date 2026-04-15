"""
geoview_cpt.seabed
================================
Marine seabed frame landing detection (Phase A-2 A2.13).

When a seabed frame CPT is deployed from a vessel, the push force,
pore pressure and (optionally) altimeter channels show a simultaneous
excursion at the moment the frame's base plate contacts the mudline.
The :func:`detect_seabed_landing` routine scans for that event using
a **k-of-N** multi-signal rule (default: 3-of-4 conditions must fire
within a short depth window) so a missing altimeter or a noisy pore
sensor does not disable detection.
"""
from __future__ import annotations

from geoview_cpt.seabed.landing_detection import (
    DEFAULT_LANDING_RULES,
    LandingCondition,
    LandingResult,
    LandingRules,
    detect_seabed_landing,
)

__all__ = [
    "LandingCondition",
    "LandingResult",
    "LandingRules",
    "DEFAULT_LANDING_RULES",
    "detect_seabed_landing",
]
