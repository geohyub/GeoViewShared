"""Tests for reader error paths — A2.0 Step 2."""
from __future__ import annotations

import zlib
from pathlib import Path

import pytest

from geoview_cpt.parsers.cpet_it_v30 import (
    CPetItReadError,
    read_cpt_v30,
    read_cpt_v30_bytes,
)


class TestBadInput:
    def test_empty_bytes(self):
        with pytest.raises(CPetItReadError, match="empty"):
            read_cpt_v30_bytes(b"")

    def test_not_zlib(self):
        with pytest.raises(CPetItReadError, match="zlib"):
            read_cpt_v30_bytes(b"not a zlib stream")

    def test_zlib_but_not_utf8(self):
        payload = zlib.compress(b"\xff\xfe\xff\xfe")
        with pytest.raises(CPetItReadError, match="UTF-8"):
            read_cpt_v30_bytes(payload)

    def test_zlib_utf8_but_broken_xml(self):
        payload = zlib.compress(b"<CPT Version='30'><Various>unterminated")
        with pytest.raises(CPetItReadError, match="XML parse"):
            read_cpt_v30_bytes(payload)

    def test_wrong_root(self):
        payload = zlib.compress(b"<?xml version='1.0'?><Other/>")
        with pytest.raises(CPetItReadError, match="root element"):
            read_cpt_v30_bytes(payload)

    def test_wrong_version(self):
        payload = zlib.compress(
            b"<?xml version='1.0'?><CPT Version='29'><Various><Handle>1</Handle></Various></CPT>"
        )
        with pytest.raises(CPetItReadError, match="Version"):
            read_cpt_v30_bytes(payload)

    def test_missing_various(self):
        payload = zlib.compress(
            b"<?xml version='1.0'?><CPT Version='30'><CPTFiles/></CPT>"
        )
        with pytest.raises(CPetItReadError, match="Various"):
            read_cpt_v30_bytes(payload)


class TestFileLevelErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(CPetItReadError, match="not found"):
            read_cpt_v30(tmp_path / "nope.cpt")

    def test_path_is_set_on_success(self, synth_cpt_file):
        from geoview_cpt.parsers.cpet_it_v30 import read_cpt_v30

        proj = read_cpt_v30(synth_cpt_file)
        assert proj.source_path == synth_cpt_file
