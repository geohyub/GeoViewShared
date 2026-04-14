"""Tests for geoview_pyside6.export.fonts — Phase A-1 A1.5."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pytest

from geoview_pyside6.export import fonts as fonts_mod
from geoview_pyside6.export.fonts import (
    PRETENDARD_DIR,
    PRETENDARD_FAMILY,
    PRETENDARD_FILES,
    pretendard_available,
    register_pretendard,
)


class TestInventory:
    def test_all_four_weights_present(self):
        assert pretendard_available() is True
        for name in PRETENDARD_FILES:
            assert (PRETENDARD_DIR / name).exists(), f"missing {name}"

    def test_family_name(self):
        assert PRETENDARD_FAMILY == "Pretendard"


class TestRegistration:
    def test_register_returns_family(self):
        assert register_pretendard(force=True) == "Pretendard"

    def test_rcparams_set(self):
        register_pretendard(force=True)
        import matplotlib.pyplot as plt

        assert plt.rcParams["font.family"] == ["Pretendard"] or plt.rcParams[
            "font.family"
        ] == "Pretendard"
        assert plt.rcParams["svg.fonttype"] == "none"
        assert plt.rcParams["pdf.fonttype"] == 42
        assert plt.rcParams["axes.unicode_minus"] is False

    def test_idempotent_second_call_is_noop(self):
        register_pretendard(force=True)
        # Module flag should now be True; a non-forced call returns without work
        assert fonts_mod._registered is True
        assert register_pretendard() == "Pretendard"

    def test_font_manager_finds_pretendard(self):
        register_pretendard(force=True)
        from matplotlib import font_manager

        # font_manager.findfont should resolve to one of our OTF files
        found = font_manager.findfont(
            font_manager.FontProperties(family="Pretendard"),
            fallback_to_default=False,
        )
        assert "Pretendard" in found
