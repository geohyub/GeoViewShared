"""Tests for chart-config + raw preservation — A2.0 Step 2."""
from __future__ import annotations

from lxml import etree as ET

from geoview_cpt.parsers._xml_fix import serialize_cpet_it_xml
from geoview_cpt.parsers.cpet_it_v30 import read_cpt_v30_bytes


class TestChartConfigRawBytes:
    def test_left_and_bottom_stored_per_sounding(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        for s in proj.soundings:
            assert "left" in s.chart_config_raw
            assert "bottom" in s.chart_config_raw
            assert s.chart_config_raw["left"].startswith(b"<ChartPropertiesLeft")
            assert s.chart_config_raw["bottom"].startswith(b"<ChartPropertiesBottom")

    def test_numeric_tags_preserved_and_round_trippable(self, synth_cpt_bytes):
        """The axis container ``<1>`` round-trips via serialize_cpet_it_xml."""
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        left_bytes = proj.soundings[0].chart_config_raw["left"]
        # lxml hands back the prefixed form
        assert b"_1" in left_bytes
        restored = serialize_cpet_it_xml(left_bytes)
        assert b"<1>" in restored
        assert b"</1>" in restored

    def test_chart_config_content_captured(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        left = proj.soundings[0].chart_config_raw["left"]
        assert b"<Min>0</Min>" in left
        assert b"<Max>50</Max>" in left


class TestExtraSectionsPreserved:
    def test_webgmap_captured(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert "WebGMap" in proj.extra_sections
        assert b"<Zoom>13</Zoom>" in proj.extra_sections["WebGMap"]

    def test_overlayprops_captured(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert "OverlayProps" in proj.extra_sections


class TestBlobAndExtrasOnSounding:
    def test_blob_b64_captured_from_element_text(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        # Synth template writes "BLOB_BASE64_ONE" as the leading text of <100>
        assert proj.soundings[0].blob_b64.startswith("BLOB_BASE64_ONE")
        assert proj.soundings[1].blob_b64.startswith("BLOB_BASE64_TWO")

    def test_extras_capture_other_children(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        # First sounding has <Samples/> and <PileData>
        extras = proj.soundings[0].extras
        assert "Samples" in extras
        assert "PileData" in extras
        assert b"PILE_B64" in extras["PileData"]


class TestFullInflatedXmlKept:
    def test_xml_plain_stored(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        assert proj.xml_plain.startswith(b"<?xml")
        assert b"<CPT Version=\"30\">" in proj.xml_plain

    def test_raw_compressed_stored(self, synth_cpt_bytes):
        proj = read_cpt_v30_bytes(synth_cpt_bytes)
        # zlib magic
        assert proj.raw_compressed[:2] == b"\x78\x9c"
        assert proj.raw_compressed == synth_cpt_bytes
