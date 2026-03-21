"""Unit tests for GeoView CTk widgets — logic only, no display required.

Tests are organised by module:
  1. base_app   — constants, class attributes, ICONS dict
  2. kpi_card   — _TREND_ICONS, _TREND_COLORS, import check
  3. data_table — import check, column-width defaults
  4. activity_log — import check
  5. integration — full GUI smoke test (skipped when CTk / display unavailable)

Copyright (c) 2025-2026 Geoview Co., Ltd.
"""

from __future__ import annotations

import importlib
import sys
from unittest import mock

import pytest

from .conftest import skip_no_ctk, skip_no_display, skip_no_gui


# ================================================================
# 1. base_app — pure-Python constants (no CTk instantiation)
# ================================================================

class TestBaseAppConstants:
    """Test constants and class attributes defined at module level."""

    def test_icons_dict_has_expected_keys(self):
        from geoview_common.ctk_widgets.base_app import ICONS

        expected = {
            "home", "analysis", "upload", "settings", "report",
            "batch", "viz", "mag", "sonar", "seismic",
            "editor", "export", "module", "web",
        }
        assert expected.issubset(set(ICONS.keys())), (
            f"Missing ICONS keys: {expected - set(ICONS.keys())}"
        )

    def test_icons_values_are_single_chars(self):
        from geoview_common.ctk_widgets.base_app import ICONS

        for key, val in ICONS.items():
            assert isinstance(val, str), f"ICONS[{key!r}] should be str"
            assert len(val) == 1, f"ICONS[{key!r}] should be a single character, got {val!r}"

    def test_sidebar_width_open(self):
        from geoview_common.ctk_widgets.base_app import _SIDEBAR_W_OPEN
        assert _SIDEBAR_W_OPEN == 180

    def test_sidebar_width_closed(self):
        from geoview_common.ctk_widgets.base_app import _SIDEBAR_W_CLOSED
        assert _SIDEBAR_W_CLOSED == 52

    def test_header_height(self):
        from geoview_common.ctk_widgets.base_app import _HEADER_H
        assert _HEADER_H == 56

    def test_status_height(self):
        from geoview_common.ctk_widgets.base_app import _STATUS_H
        assert _STATUS_H == 30

    def test_geoviewapp_class_defaults(self):
        from geoview_common.ctk_widgets.base_app import GeoViewApp

        assert GeoViewApp.APP_TITLE == "GeoView"
        assert GeoViewApp.APP_VERSION == "1.0"
        assert GeoViewApp.APP_SUBTITLE == ""
        assert GeoViewApp.USE_SIDEBAR is True
        assert GeoViewApp.SIDEBAR_DEFAULT_OPEN is True
        assert GeoViewApp.WINDOW_SIZE == "1400x900"
        assert GeoViewApp.WINDOW_MIN_SIZE == (1200, 700)

    def test_geoviewapp_has_expected_methods(self):
        from geoview_common.ctk_widgets.base_app import GeoViewApp

        for method_name in (
            "get_nav_items", "build_page", "build_content",
            "set_status", "show_progress", "hide_progress",
            "set_notification", "navigate", "run",
        ):
            assert hasattr(GeoViewApp, method_name), (
                f"GeoViewApp missing method: {method_name}"
            )

    def test_has_ctk_flag_exists(self):
        from geoview_common.ctk_widgets.base_app import HAS_CTK
        assert isinstance(HAS_CTK, bool)


# ================================================================
# 2. kpi_card — trend dicts (module-level) + mock import
# ================================================================

class TestKPICardConstants:
    """Test module-level dicts and importability of kpi_card."""

    def test_import_kpi_card_module(self):
        mod = importlib.import_module("geoview_common.ctk_widgets.kpi_card")
        assert hasattr(mod, "KPICard")
        assert hasattr(mod, "_TREND_ICONS")
        assert hasattr(mod, "_TREND_COLORS")

    def test_trend_icons_keys(self):
        from geoview_common.ctk_widgets.kpi_card import _TREND_ICONS
        assert set(_TREND_ICONS.keys()) == {"up", "down", "flat"}

    def test_trend_icons_values_are_strings(self):
        from geoview_common.ctk_widgets.kpi_card import _TREND_ICONS
        for key, val in _TREND_ICONS.items():
            assert isinstance(val, str), f"_TREND_ICONS[{key!r}] not a str"
            assert len(val) == 1, f"_TREND_ICONS[{key!r}] expected single char"

    def test_trend_colors_keys(self):
        from geoview_common.ctk_widgets.kpi_card import _TREND_COLORS
        assert set(_TREND_COLORS.keys()) == {"up", "down", "flat"}

    def test_trend_colors_values_look_like_hex(self):
        from geoview_common.ctk_widgets.kpi_card import _TREND_COLORS
        for key, val in _TREND_COLORS.items():
            assert isinstance(val, str), f"_TREND_COLORS[{key!r}] not a str"
            assert val.startswith("#"), (
                f"_TREND_COLORS[{key!r}] should start with '#', got {val!r}"
            )

    def test_trend_icons_and_colors_have_same_keys(self):
        from geoview_common.ctk_widgets.kpi_card import _TREND_ICONS, _TREND_COLORS
        assert set(_TREND_ICONS.keys()) == set(_TREND_COLORS.keys())


# ================================================================
# 3. data_table — import + logic tests
# ================================================================

class TestDataTableLogic:
    """Test DataTable importability and column-width default behaviour."""

    def test_import_data_table_module(self):
        mod = importlib.import_module("geoview_common.ctk_widgets.data_table")
        assert hasattr(mod, "DataTable")

    def test_datatable_class_exists(self):
        from geoview_common.ctk_widgets.data_table import DataTable
        assert DataTable is not None

    def test_column_width_defaults_none_list(self):
        """When column_widths is omitted, _col_widths should be [None]*n_cols.

        We verify this by inspecting __init__ signature defaults and the
        logic: ``column_widths or [None] * self._n_cols``.
        """
        import inspect
        from geoview_common.ctk_widgets.data_table import DataTable

        sig = inspect.signature(DataTable.__init__)
        col_widths_param = sig.parameters.get("column_widths")
        assert col_widths_param is not None
        assert col_widths_param.default is None, (
            "column_widths default should be None"
        )

    def test_max_rows_default(self):
        import inspect
        from geoview_common.ctk_widgets.data_table import DataTable

        sig = inspect.signature(DataTable.__init__)
        max_rows_param = sig.parameters["max_rows"]
        assert max_rows_param.default == 500

    def test_row_height_default(self):
        import inspect
        from geoview_common.ctk_widgets.data_table import DataTable

        sig = inspect.signature(DataTable.__init__)
        row_height_param = sig.parameters["row_height"]
        assert row_height_param.default == 32


# ================================================================
# 4. activity_log — import tests
# ================================================================

class TestActivityLogImport:
    """Test ActivityLog importability and interface."""

    def test_import_activity_log_module(self):
        mod = importlib.import_module("geoview_common.ctk_widgets.activity_log")
        assert hasattr(mod, "ActivityLog")

    def test_activity_log_has_expected_methods(self):
        from geoview_common.ctk_widgets.activity_log import ActivityLog

        for method in ("info", "success", "warn", "error", "step", "header", "clear", "get_text"):
            assert hasattr(ActivityLog, method), (
                f"ActivityLog missing method: {method}"
            )

    def test_max_lines_default(self):
        import inspect
        from geoview_common.ctk_widgets.activity_log import ActivityLog

        sig = inspect.signature(ActivityLog.__init__)
        assert sig.parameters["max_lines"].default == 500

    def test_height_default(self):
        import inspect
        from geoview_common.ctk_widgets.activity_log import ActivityLog

        sig = inspect.signature(ActivityLog.__init__)
        assert sig.parameters["height"].default == 300


# ================================================================
# 5. Integration tests — full GUI (skipped in headless / no CTk)
# ================================================================

@skip_no_gui
class TestWidgetIntegration:
    """Smoke tests that instantiate real CTk widgets.

    Skipped automatically when customtkinter is missing or no display
    server is available (CI / headless).
    """

    @pytest.fixture(autouse=True)
    def _ctk_root(self, _shared_ctk_root):
        """Use a shared CTk root to avoid Tk reinitialisation issues."""
        self.root = _shared_ctk_root
        yield

    def test_kpi_card_instantiate(self):
        from geoview_common.ctk_widgets.kpi_card import KPICard

        card = KPICard(self.root, title="Test", accent_color="#2D5F8A")
        assert card is not None
        card.set_value("42", unit="items", trend="up")
        card.set_value("0", trend="down")
        card.set_value("99", trend="flat")
        card.set_value("--", trend="")
        card.set_title("New Title")

    def test_data_table_instantiate(self):
        from geoview_common.ctk_widgets.data_table import DataTable

        table = DataTable(self.root, columns=["Name", "Size", "Status"])
        assert table.row_count == 0
        assert table.get_selected() is None

        table.set_data([
            ["file1.mag", "1.2 MB", "PASS"],
            ["file2.mag", "0.8 MB", "WARN"],
        ])
        assert table.row_count == 2

        table.append_row(["file3.mag", "2.0 MB", "FAIL"])
        assert table.row_count == 3

        table.clear()
        assert table.row_count == 0

    def test_data_table_column_widths(self):
        from geoview_common.ctk_widgets.data_table import DataTable

        table = DataTable(
            self.root,
            columns=["A", "B"],
            column_widths=[100, 200],
        )
        assert table._col_widths == [100, 200]

    def test_data_table_none_widths(self):
        from geoview_common.ctk_widgets.data_table import DataTable

        table = DataTable(self.root, columns=["X", "Y", "Z"])
        assert table._col_widths == [None, None, None]

    def test_data_table_max_rows_limit(self):
        from geoview_common.ctk_widgets.data_table import DataTable

        table = DataTable(self.root, columns=["Val"], max_rows=3)
        table.set_data([["a"], ["b"], ["c"], ["d"], ["e"]])
        assert table.row_count == 3  # capped at max_rows

    def test_data_table_append_respects_max(self):
        from geoview_common.ctk_widgets.data_table import DataTable

        table = DataTable(self.root, columns=["Val"], max_rows=2)
        table.set_data([["a"], ["b"]])
        table.append_row(["c"])  # should be ignored
        assert table.row_count == 2

    def test_activity_log_instantiate(self):
        from geoview_common.ctk_widgets.activity_log import ActivityLog

        log = ActivityLog(self.root, height=200, max_lines=50)
        assert log is not None
        log.info("test info")
        log.success("test success")
        log.warn("test warn")
        log.error("test error")
        log.step("test step")
        log.header("test header")

        text = log.get_text()
        assert "test info" in text
        assert "test error" in text

        log.clear()
        cleared = log.get_text().strip()
        assert cleared == ""

    def test_activity_log_max_lines_trim(self):
        from geoview_common.ctk_widgets.activity_log import ActivityLog

        log = ActivityLog(self.root, max_lines=5)
        for i in range(10):
            log.info(f"line {i}")
        assert log._line_count == 5

    def test_kpi_card_invalid_trend_ignored(self):
        from geoview_common.ctk_widgets.kpi_card import KPICard

        card = KPICard(self.root, title="Test")
        # Should not raise with an unknown trend string
        card.set_value("10", trend="unknown_trend")
