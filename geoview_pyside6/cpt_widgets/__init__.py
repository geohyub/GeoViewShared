"""
cpt_widgets — CPT 3 앱 (CPTPrep/CPTQC/CPTProc) 전용 신규 위젯 (Wave 6)

v1.0 구현 목록 (new_widgets_spec.md):
- N2 ShortcutHintBanner        (Week 21 D5)
- N3 TiledAnalysisWindow       (Week 22 → Phase B Wave 3)
- N4 AnalysisBlock             (Week 20 D2~3, Day 3 fallback trigger)
- N5 ReactivePanel (축소판)    (Week 20 D3, 수동 Rerun)
- N6 GlobalDepthPicker         (Week 20 D1, 최초 구현) ← 본 세션
- N1 DistractionFreeToggle     v1.1 이연, 구현 금지

규율:
- 기존 widgets/ 내부 수정 금지 (welcome_dialog.add_section 확장만 허용)
- effects.py 수정 금지
- 본 디렉토리 내 파일만 신규/수정 허용
"""

from geoview_pyside6.cpt_widgets.analysis_block import (
    AnalysisBlock,
    BlockStatus,
    TraceRecord,
    compute_params_hash,
    read_traces,
    trace_directory,
    utc_now_iso,
    write_trace,
)
from geoview_pyside6.cpt_widgets.global_depth_picker import GlobalDepthPicker
from geoview_pyside6.cpt_widgets.reactive_panel import ReactivePanel
from geoview_pyside6.cpt_widgets.shortcut_hint_banner import ShortcutHintBanner
from geoview_pyside6.cpt_widgets.tiled_analysis_window import TiledAnalysisWindow

__all__ = [
    "AnalysisBlock",
    "BlockStatus",
    "GlobalDepthPicker",
    "ReactivePanel",
    "ShortcutHintBanner",
    "TiledAnalysisWindow",
    "TraceRecord",
    "compute_params_hash",
    "read_traces",
    "trace_directory",
    "utc_now_iso",
    "write_trace",
]
