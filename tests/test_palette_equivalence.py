"""Regression tests for geoview_pyside6 color-palette equivalence.

The runtime theme switcher (`c()`) rotates between Dark, Light, SkyBlue,
and WarmBeige classes. Any attribute that is present on one class but
absent on another becomes a hidden AttributeError the moment the user
toggles to the missing theme. The NavQC WarmBeige crash
(`c().CARD` → AttributeError) in 2026-04 was exactly this failure
mode — `CARD` existed nowhere, but the symptom only surfaced under
WarmBeige because that was the active theme when the relevant code
path ran.

This test suite is the safety net: any future PR that adds an attribute
to one palette must add it to all four, or the tests fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SHARED_ROOT = str(Path(__file__).resolve().parents[1])
if _SHARED_ROOT not in sys.path:
    sys.path.insert(0, _SHARED_ROOT)

import pytest

from geoview_pyside6.constants import Dark, Light, SkyBlue, WarmBeige


PALETTES = {
    "Dark": Dark,
    "Light": Light,
    "SkyBlue": SkyBlue,
    "WarmBeige": WarmBeige,
}


def _public_attrs(cls) -> set:
    return {name for name in dir(cls) if not name.startswith("_")}


def test_all_palettes_expose_identical_attribute_sets():
    """Every palette must define the same set of public attributes."""
    sets = {name: _public_attrs(cls) for name, cls in PALETTES.items()}
    union = set().union(*sets.values())

    missing = {name: sorted(union - attrs) for name, attrs in sets.items()}
    broken = {k: v for k, v in missing.items() if v}

    assert not broken, (
        "Palette attribute drift detected — these classes are missing "
        "attributes present on other palettes:\n"
        + "\n".join(f"  {name}: {attrs}" for name, attrs in broken.items())
        + "\nAdd the missing attributes so theme toggles cannot crash."
    )


@pytest.mark.parametrize("name,cls", list(PALETTES.items()))
def test_palette_has_expected_baseline_keys(name, cls):
    """Sanity check: each palette must expose the load-bearing keys that
    geoview_pyside6 widgets depend on. If any of these goes missing the
    runtime breaks across every app."""
    required = {
        # surfaces
        "BG", "BG_ALT", "DARK", "NAVY", "SLATE", "SURFACE",
        # text
        "TEXT", "TEXT_BRIGHT", "MUTED", "DIM",
        # core colors
        "BLUE", "CYAN", "GREEN", "ORANGE", "RED", "PURPLE", "INDIGO", "ROSE",
        # semantic
        "SUCCESS", "WARNING", "DANGER", "INFO",
        # hover
        "GREEN_H", "CYAN_H", "RED_H", "BLUE_H", "ORANGE_H", "PURPLE_H",
        # borders
        "BORDER", "BORDER_H",
        # chart
        "CROSSHAIR", "CHART_BG", "CHART_GRID", "STATS_BOX_BG", "STATS_BOX_BORDER",
        # shadow
        "SHADOW",
    }
    present = _public_attrs(cls)
    missing = required - present
    assert not missing, (
        f"Palette {name} is missing required baseline keys: {sorted(missing)}"
    )


@pytest.mark.parametrize("name,cls", list(PALETTES.items()))
def test_palette_values_are_non_empty_strings(name, cls):
    """Every palette attribute must be a non-empty string — a `None` or
    empty value silently renders as black/transparent and is the
    second-most common source of theme-related visual bugs."""
    for attr in _public_attrs(cls):
        value = getattr(cls, attr)
        assert isinstance(value, str), (
            f"{name}.{attr} must be a string (QSS / rgba token), got {type(value).__name__}"
        )
        assert value, f"{name}.{attr} must not be empty"


def test_semantic_aliases_point_to_existing_keys():
    """SUCCESS/WARNING/DANGER/INFO aliases must equal GREEN/ORANGE/RED/CYAN."""
    for name, cls in PALETTES.items():
        assert cls.SUCCESS == cls.GREEN, f"{name}.SUCCESS must equal GREEN"
        assert cls.WARNING == cls.ORANGE, f"{name}.WARNING must equal ORANGE"
        assert cls.DANGER == cls.RED, f"{name}.DANGER must equal RED"
        assert cls.INFO == cls.CYAN, f"{name}.INFO must equal CYAN"
