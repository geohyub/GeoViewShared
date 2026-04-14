"""Tests for <Various> extraction — A2.0 Step 2."""
from __future__ import annotations

from geoview_cpt.parsers.cpet_it_v30 import read_cpt_v30_bytes


class TestBrandingFields:
    def test_four_partner_fields(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.partner_brand == "Geoview"
        assert proj.partner_description == "Marine Research Geotechnical Engineers"
        assert proj.partner_address == "Busan, South Korea"
        assert proj.partner_url == "http://www.geoview.co.kr"

    def test_partner_logo_path(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.partner_logo_path.endswith("geoview_logo.png")


class TestProjectIdentity:
    def test_project_name_and_handle(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.handle == 12345
        assert proj.name == "Synth Project"
        assert proj.project_id == "PRJ-001"
        assert proj.location == "Test Bay"
        assert proj.comments == "unit test"


class TestUIConfig:
    def test_unit_system_si(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.unit_system == 0

    def test_display_image_flag(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.display_image is True

    def test_vertical_plot_flag(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.vertical_plot is False

    def test_font(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.font_name == "Arial Narrow"
        assert proj.font_size == 7


class TestCustomSBTnDesc:
    def test_semicolon_split(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        # "A;B;C;D;;;;;;" → 10 slots
        assert proj.custom_sbtn_desc == ["A", "B", "C", "D", "", "", "", "", "", ""]


class TestRawPreservation:
    def test_various_raw_roundtrippable(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert b"<Various>" in proj.various_raw
        assert b"Geoview" in proj.various_raw
        assert b"</Various>" in proj.various_raw
