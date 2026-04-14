"""Tests for geoview_pyside6.export.color — Phase A-1 A1.5."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from geoview_pyside6.export.color import SRGB_PALETTE, ensure_srgb_png


class TestPalette:
    def test_has_navy(self):
        assert SRGB_PALETTE["navy"] == "#0B2545"

    def test_all_hex_format(self):
        pat = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for name, value in SRGB_PALETTE.items():
            assert pat.match(value), f"{name}={value!r} not a 6-digit hex"

    def test_expected_roles_present(self):
        for role in ("navy", "accent", "success", "warning", "danger", "paper"):
            assert role in SRGB_PALETTE


class TestEnsureSrgbPng:
    def _make_png(self, tmp_path: Path) -> Path:
        from PIL import Image

        p = tmp_path / "x.png"
        Image.new("RGB", (4, 4), (11, 37, 69)).save(p, format="PNG")
        return p

    def test_non_png_is_noop(self, tmp_path):
        p = tmp_path / "x.svg"
        p.write_text("<svg></svg>")
        out = ensure_srgb_png(p)
        assert out == p
        # unchanged content
        assert p.read_text() == "<svg></svg>"

    def test_png_gets_icc_profile(self, tmp_path):
        from PIL import Image

        p = self._make_png(tmp_path)
        ensure_srgb_png(p)
        with Image.open(p) as img:
            assert img.info.get("icc_profile"), "icc_profile missing after stamp"

    def test_png_pixels_preserved(self, tmp_path):
        from PIL import Image

        p = self._make_png(tmp_path)
        original = list(Image.open(p).getdata())
        ensure_srgb_png(p)
        stamped = list(Image.open(p).getdata())
        assert stamped == original
