"""Tests for geoview_cpt.parsers._xml_sanitize — A2.0 Step 1."""
from __future__ import annotations

import pytest
from lxml import etree as ET

from geoview_cpt.parsers._xml_sanitize import (
    NUMERIC_TAG_PREFIX,
    is_mangled_tag,
    mangle,
    original_tag,
    unmangle,
)


class TestMangle:
    def test_prefixes_simple_open(self):
        assert mangle("<1>x</1>") == "<n_1>x</n_1>"

    def test_prefixes_five_digit(self):
        assert mangle("<87616>b</87616>") == "<n_87616>b</n_87616>"

    def test_self_closing(self):
        assert mangle("<42/>") == "<n_42/>"

    def test_leaves_alpha_tags_alone(self):
        xml = "<CPT><Various><Handle>1</Handle></Various></CPT>"
        assert mangle(xml) == xml

    def test_nested_numeric(self):
        src = "<Chart><1><2>v</2></1></Chart>"
        assert mangle(src) == "<Chart><n_1><n_2>v</n_2></n_1></Chart>"

    def test_idempotent(self):
        once = mangle("<87616>x</87616>")
        twice = mangle(once)
        assert once == twice

    def test_tag_with_attribute(self):
        assert mangle('<1 k="v">x</1>') == '<n_1 k="v">x</n_1>'


class TestUnmangle:
    def test_round_trip(self):
        src = "<Root><87616>a<1>b</1></87616></Root>"
        assert unmangle(mangle(src)) == src

    def test_leaves_non_numeric_prefixed_alone(self):
        # "n_foo" isn't a mangled numeric — must survive unchanged
        src = "<Root><n_foo>x</n_foo></Root>"
        assert unmangle(src) == src

    def test_round_trip_with_attributes(self):
        src = '<Root><87616 k="v">x</87616></Root>'
        assert unmangle(mangle(src)) == src


class TestLxmlAcceptsMangled:
    def test_lxml_parses_mangled_output(self):
        src = "<CPT Version='30'><87616><Handle>1</Handle></87616></CPT>"
        root = ET.fromstring(mangle(src).encode("utf-8"))
        assert root.tag == "CPT"
        # child tag is now the mangled form
        (child,) = root
        assert child.tag == "n_87616"
        assert is_mangled_tag(child.tag)
        assert original_tag(child.tag) == "87616"

    def test_lxml_rejects_unmangled(self):
        src = "<CPT><87616>x</87616></CPT>"
        with pytest.raises(ET.XMLSyntaxError):
            ET.fromstring(src.encode("utf-8"))


class TestHelpers:
    def test_is_mangled_tag_positive(self):
        assert is_mangled_tag("n_42")
        assert is_mangled_tag("n_87616")

    def test_is_mangled_tag_negative(self):
        assert not is_mangled_tag("n_foo")
        assert not is_mangled_tag("CPTName")
        assert not is_mangled_tag("n_")
        assert not is_mangled_tag("87616")

    def test_original_tag_roundtrip(self):
        assert original_tag("n_42") == "42"

    def test_original_tag_passthrough(self):
        assert original_tag("CPTName") == "CPTName"
        assert original_tag(f"{NUMERIC_TAG_PREFIX}abc") == "n_abc"
