"""
gt_widgets — GT Suite 3 앱 (GTPrep/GTQC/GTProc) 전용 위젯

v1.0 구현 목록:
- N2 ShortcutHintBanner
- N3 TiledAnalysisWindow
- N4 AnalysisBlock
- N5 ReactivePanel (축소판)
- N6 GlobalDepthPicker
- Autosave + UndoStack
"""

from geoview_pyside6.gt_widgets.autosave import (
    AutosaveManager,
    AutosaveRecord,
    UndoStack,
)
from geoview_pyside6.gt_widgets.analysis_block import (
    AnalysisBlock,
    BlockStatus,
    TraceRecord,
    compute_params_hash,
    read_traces,
    trace_directory,
    utc_now_iso,
    write_trace,
)
from geoview_pyside6.gt_widgets.global_depth_picker import GlobalDepthPicker
from geoview_pyside6.gt_widgets.reactive_panel import ReactivePanel
from geoview_pyside6.gt_widgets.shortcut_hint_banner import ShortcutHintBanner
from geoview_pyside6.gt_widgets.tiled_analysis_window import TiledAnalysisWindow

__all__ = [
    "AnalysisBlock",
    "AutosaveManager",
    "AutosaveRecord",
    "BlockStatus",
    "GlobalDepthPicker",
    "ReactivePanel",
    "ShortcutHintBanner",
    "TiledAnalysisWindow",
    "TraceRecord",
    "UndoStack",
    "compute_params_hash",
    "read_traces",
    "trace_directory",
    "utc_now_iso",
    "write_trace",
]
