"""Tests for geoview_cpt.parsers._xml_fix — master brief contract."""
from __future__ import annotations

import zlib

import pytest
from lxml import etree

from geoview_cpt.parsers._xml_fix import (
    parse_cpet_it_xml,
    real_tag,
    serialize_cpet_it_xml,
)


# ---------------------------------------------------------------------------
# parse_cpet_it_xml
# ---------------------------------------------------------------------------


class TestParseCpetItXml:
    def test_accepts_numeric_child_tags(self):
        src = b"<CPT Version='30'><CPTFiles><87616><Handle>1</Handle></87616></CPTFiles></CPT>"
        root = parse_cpet_it_xml(src)
        assert root.tag == "CPT"
        container = root.find("CPTFiles")
        (child,) = container
        # Prefix is single underscore per master brief
        assert child.tag == "_87616"
        assert real_tag(child) == "87616"

    def test_accepts_single_digit_tags(self):
        src = b"<Root><1>a</1><2>b</2></Root>"
        root = parse_cpet_it_xml(src)
        kids = list(root)
        assert [real_tag(k) for k in kids] == ["1", "2"]

    def test_leaves_alpha_tags_untouched(self):
        src = b"<CPT Version='30'><Various><Handle>42</Handle></Various></CPT>"
        root = parse_cpet_it_xml(src)
        assert root.find("Various").find("Handle").text == "42"

    def test_rejects_non_bytes_input(self):
        with pytest.raises(TypeError):
            parse_cpet_it_xml("<CPT/>")  # type: ignore[arg-type]

    def test_rejects_malformed_xml(self):
        with pytest.raises(etree.XMLSyntaxError):
            parse_cpet_it_xml(b"<CPT><unterminated")

    def test_nested_numeric_tags(self):
        """Chart axis containers (<1><2>…) live inside ChartProperties blocks."""
        src = (
            b"<CPT Version='30'><CPTFiles><100>"
            b"<ChartPropertiesLeft><1><Min>0</Min></1><2><Min>5</Min></2></ChartPropertiesLeft>"
            b"</100></CPTFiles></CPT>"
        )
        root = parse_cpet_it_xml(src)
        sounding = root.find("CPTFiles")[0]
        left = sounding.find("ChartPropertiesLeft")
        kids = list(left)
        assert [real_tag(k) for k in kids] == ["1", "2"]
        assert kids[0].find("Min").text == "0"
        assert kids[1].find("Min").text == "5"


# ---------------------------------------------------------------------------
# real_tag
# ---------------------------------------------------------------------------


class TestRealTag:
    def test_accepts_element(self):
        root = parse_cpet_it_xml(b"<Root><42>x</42></Root>")
        (child,) = root
        assert real_tag(child) == "42"

    def test_accepts_string(self):
        assert real_tag("_42") == "42"
        assert real_tag("_87616") == "87616"

    def test_passes_through_alpha_tag(self):
        assert real_tag("CPTName") == "CPTName"
        assert real_tag("_foo") == "_foo"   # not purely numeric

    def test_passes_through_bare_underscore(self):
        assert real_tag("_") == "_"

    def test_does_not_strip_multi_underscore(self):
        assert real_tag("__42") == "__42"


# ---------------------------------------------------------------------------
# serialize_cpet_it_xml — A2.0c writer prep
# ---------------------------------------------------------------------------


class TestSerializeRoundTrip:
    def test_round_trip_element(self):
        src = b"<Root><87616><Handle>1</Handle></87616></Root>"
        root = parse_cpet_it_xml(src)
        out = serialize_cpet_it_xml(root)
        # Original numeric tags restored
        assert b"<87616>" in out
        assert b"</87616>" in out
        assert b"_87616" not in out

    def test_round_trip_bytes_passthrough(self):
        """A pre-serialized fragment that still contains _DDD should round-trip."""
        fragment = b"<_1><Min>0</Min></_1>"
        out = serialize_cpet_it_xml(fragment)
        assert out == b"<1><Min>0</Min></1>"

    def test_round_trip_preserves_non_numeric(self):
        src = b"<CPT Version='30'><Various><Handle>1</Handle></Various></CPT>"
        root = parse_cpet_it_xml(src)
        out = serialize_cpet_it_xml(root)
        assert b"<Various>" in out
        assert b"<Handle>1</Handle>" in out

    def test_fullcycle_zlib_parse_serialize(self):
        xml = (
            b"<?xml version='1.0' encoding='UTF-8'?>"
            b"<CPT Version='30'><Various><Handle>1</Handle></Various>"
            b"<CPTFiles><777><CPTName>X</CPTName></777></CPTFiles></CPT>"
        )
        compressed = zlib.compress(xml)
        root = parse_cpet_it_xml(zlib.decompress(compressed))
        restored = serialize_cpet_it_xml(root)
        assert b"<777>" in restored
        assert b"</777>" in restored
