"""Tests for geoview_cpt.ags_convert.wrapper — Phase A-3 A3.1."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from geoview_cpt.ags_convert import (
    STANDARD_DICTIONARY_V4_1_1,
    AGSBundle,
    AgsConvertError,
    dump_ags,
    load_ags,
)


# ---------------------------------------------------------------------------
# python-ags4 bundled test fixture
# ---------------------------------------------------------------------------


def _bundled_test_data_path() -> Path:
    import python_ags4

    base = Path(python_ags4.__file__).resolve().parent
    candidate = base / "data" / "test_data.ags"
    if not candidate.exists():
        pytest.skip("python-ags4 bundled test_data.ags not found")
    return candidate


@pytest.fixture(scope="module")
def bundled_ags_path() -> Path:
    return _bundled_test_data_path()


# ---------------------------------------------------------------------------
# STANDARD_DICTIONARY_V4_1_1
# ---------------------------------------------------------------------------


class TestStandardDictionary:
    def test_exists(self):
        assert STANDARD_DICTIONARY_V4_1_1.exists()

    def test_suffix(self):
        assert STANDARD_DICTIONARY_V4_1_1.suffix == ".ags"

    def test_size_reasonable(self):
        # v4_1_1 ships around ~375 KB
        assert STANDARD_DICTIONARY_V4_1_1.stat().st_size > 100_000


# ---------------------------------------------------------------------------
# load_ags
# ---------------------------------------------------------------------------


class TestLoadAgs:
    def test_returns_bundle(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        assert isinstance(bundle, AGSBundle)

    def test_tables_populated(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        assert len(bundle) > 0
        for group, df in bundle.tables.items():
            assert isinstance(df, pd.DataFrame)
            assert "HEADING" in df.columns

    def test_has_core_groups(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        # The bundled test_data.ags has PROJ / TRAN / UNIT / TYPE / LOCA
        for g in ("PROJ", "TRAN", "TYPE", "UNIT", "LOCA"):
            assert g in bundle, f"missing core group {g}"

    def test_heading_order_matches_columns(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        for group, df in bundle.tables.items():
            assert list(df.columns) == bundle.headings[group]

    def test_source_path_recorded(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        assert bundle.source_path == bundled_ags_path

    def test_unit_map_populated(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        assert bundle.units  # non-empty
        assert bundle.types  # non-empty
        # PROJ has no natural UNIT on PROJ_ID so the cell is blank but
        # the key should exist once build_unit_map is called
        assert "PROJ" in bundle.units

    def test_data_rows_excludes_unit_type(self, bundled_ags_path):
        bundle = load_ags(bundled_ags_path)
        data = bundle.data_rows("PROJ")
        assert (data["HEADING"] == "DATA").all()


class TestLoadErrors:
    def test_missing_file(self, tmp_path):
        with pytest.raises(AgsConvertError, match="not found"):
            load_ags(tmp_path / "nope.ags")

    def test_empty_file_returns_empty_bundle(self, tmp_path):
        # python-ags4 is permissive on malformed text (it just returns
        # empty tables). Assert we get an AGSBundle with no groups.
        bad = tmp_path / "empty.ags"
        bad.write_text("", encoding="utf-8")
        bundle = load_ags(bad)
        assert len(bundle) == 0


# ---------------------------------------------------------------------------
# dump_ags  +  round-trip smoke
# ---------------------------------------------------------------------------


class TestDumpRoundTrip:
    def test_dump_returns_path(self, bundled_ags_path, tmp_path):
        bundle = load_ags(bundled_ags_path)
        out = tmp_path / "roundtrip.ags"
        result = dump_ags(bundle, out)
        assert result == out
        assert out.exists()
        assert out.stat().st_size > 100

    def test_round_trip_groups_match(self, bundled_ags_path, tmp_path):
        bundle = load_ags(bundled_ags_path)
        out = tmp_path / "roundtrip.ags"
        dump_ags(bundle, out)
        reloaded = load_ags(out)
        assert sorted(reloaded.tables.keys()) == sorted(bundle.tables.keys())

    def test_round_trip_shapes_match(self, bundled_ags_path, tmp_path):
        bundle = load_ags(bundled_ags_path)
        out = tmp_path / "roundtrip.ags"
        dump_ags(bundle, out)
        reloaded = load_ags(out)
        for group in bundle.tables:
            assert bundle.tables[group].shape == reloaded.tables[group].shape, (
                f"{group} shape drift"
            )

    def test_round_trip_headings_preserved(self, bundled_ags_path, tmp_path):
        bundle = load_ags(bundled_ags_path)
        out = tmp_path / "roundtrip.ags"
        dump_ags(bundle, out)
        reloaded = load_ags(out)
        for group in bundle.headings:
            assert list(bundle.headings[group]) == list(reloaded.headings[group])

    def test_original_bundle_unchanged_after_dump(self, bundled_ags_path, tmp_path):
        """dump_ags must not mutate the caller's bundle — python-ags4
        mutates its arguments, so we verify our defensive-copy guard."""
        bundle = load_ags(bundled_ags_path)
        before_groups = set(bundle.tables.keys())
        before_proj = bundle.tables["PROJ"].copy(deep=True)
        dump_ags(bundle, tmp_path / "guard.ags")
        after_groups = set(bundle.tables.keys())
        assert before_groups == after_groups
        pd.testing.assert_frame_equal(bundle.tables["PROJ"], before_proj)

    def test_dump_empty_bundle_rejected(self, tmp_path):
        empty = AGSBundle()
        with pytest.raises(AgsConvertError, match="empty"):
            dump_ags(empty, tmp_path / "x.ags")

    def test_dump_rejects_non_bundle(self, tmp_path):
        with pytest.raises(TypeError):
            dump_ags({"PROJ": pd.DataFrame()}, tmp_path / "x.ags")  # type: ignore[arg-type]

    def test_dump_creates_parent(self, bundled_ags_path, tmp_path):
        bundle = load_ags(bundled_ags_path)
        out = tmp_path / "nested" / "deeper" / "out.ags"
        dump_ags(bundle, out)
        assert out.exists()
