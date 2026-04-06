"""
GeoView PySide6 — Shared Widgets
==================================
24개 프로그램이 공유하는 재사용 가능한 위젯 컬렉션.
"""

from geoview_pyside6.widgets.kpi_card import KPICard
from geoview_pyside6.widgets.status_badge import StatusBadge
from geoview_pyside6.widgets.data_table import GVTableView
from geoview_pyside6.widgets.file_drop_zone import FileDropZone
from geoview_pyside6.widgets.search_input import SearchInput
from geoview_pyside6.widgets.form_field import FormField, FormFieldGroup
from geoview_pyside6.widgets.collapsible_section import CollapsibleSection
from geoview_pyside6.widgets.filter_toolbar import FilterToolbar
from geoview_pyside6.widgets.dashboard_template import DashboardTemplate
from geoview_pyside6.widgets.context_menu import create_context_menu
from geoview_pyside6.widgets.animated_stack import AnimatedStackedWidget
from geoview_pyside6.widgets.loading_spinner import LoadingSpinner, LoadingOverlay
from geoview_pyside6.widgets.skeleton_loader import (
    SkeletonRect, SkeletonText, SkeletonKPICard, SkeletonTableRows,
)
from geoview_pyside6.widgets.command_palette import CommandPalette
from geoview_pyside6.widgets.welcome_dialog import WelcomeDialog
from geoview_pyside6.widgets.breadcrumb import Breadcrumb
from geoview_pyside6.widgets.animated_tab_bar import AnimatedTabBar
from geoview_pyside6.widgets.settings_panel import SettingsPanel
from geoview_pyside6.widgets.notification_center import NotificationCenter
from geoview_pyside6.widgets.success_overlay import SuccessOverlay
from geoview_pyside6.utils import ElidedLabel

__all__ = [
    "KPICard", "StatusBadge", "GVTableView", "FileDropZone",
    "SearchInput", "FormField", "FormFieldGroup", "CollapsibleSection", "FilterToolbar",
    "DashboardTemplate", "create_context_menu", "AnimatedStackedWidget",
    "LoadingSpinner", "LoadingOverlay",
    "SkeletonRect", "SkeletonText", "SkeletonKPICard", "SkeletonTableRows",
    "CommandPalette", "WelcomeDialog",
    "Breadcrumb", "AnimatedTabBar",
    "SettingsPanel", "NotificationCenter",
    "SuccessOverlay",
    "ElidedLabel",
]
