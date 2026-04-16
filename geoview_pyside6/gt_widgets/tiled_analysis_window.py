"""
N3 TiledAnalysisWindow — 동일 sounding × 여러 method 동시 비교 (Wave 8)

참조: plans/new_widgets_spec.md §2
      plans/wave8_b3_cptproc_plan.md §3 Day 1~2

규칙:
- 최대 3 tile (v1.0)
- 각 tile = AnalysisBlock 인스턴스
- Global Depth 만 동기, 나머지는 독립
- QSplitter 기반 가로 분할
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSplitter, QWidget

from geoview_pyside6.gt_widgets.analysis_block import AnalysisBlock
from geoview_pyside6.gt_widgets.global_depth_picker import GlobalDepthPicker

_MAX_TILES = 3


class TiledAnalysisWindow(QSplitter):
    """가로 분할 QSplitter 기반 multi-block 비교 뷰."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._tiles: list[AnalysisBlock] = []
        self._depth_picker: GlobalDepthPicker | None = None

    # ---- Public API ----------------------------------------------------------

    @property
    def tile_count(self) -> int:
        return len(self._tiles)

    @property
    def tiles(self) -> list[AnalysisBlock]:
        return list(self._tiles)

    def add_tile(self, block: AnalysisBlock) -> int:
        """블록을 타일로 추가. 최대 3개. 반환: 인덱스."""
        if len(self._tiles) >= _MAX_TILES:
            raise ValueError(f"Maximum {_MAX_TILES} tiles allowed")
        self._tiles.append(block)
        self.addWidget(block)
        self._equalize_sizes()
        # depth sync 연결
        if self._depth_picker is not None:
            self._connect_depth(block)
        return len(self._tiles) - 1

    def remove_tile(self, index: int) -> AnalysisBlock:
        """인덱스로 타일 제거. 위젯은 삭제하지 않고 반환."""
        if index < 0 or index >= len(self._tiles):
            raise IndexError(f"Tile index {index} out of range")
        block = self._tiles.pop(index)
        block.setParent(None)
        self._equalize_sizes()
        return block

    def set_tiles(self, blocks: list[AnalysisBlock]) -> None:
        """전체 타일을 교체."""
        # 기존 제거
        for block in list(self._tiles):
            block.setParent(None)
        self._tiles.clear()
        # 새로 추가 (최대 3)
        for block in blocks[:_MAX_TILES]:
            self._tiles.append(block)
            self.addWidget(block)
        self._equalize_sizes()
        # depth sync
        if self._depth_picker is not None:
            for block in self._tiles:
                self._connect_depth(block)

    def link_depth(self, picker: GlobalDepthPicker) -> None:
        """N6 GlobalDepthPicker 연결 — range 변경 시 전 블록 chart 동기."""
        self._depth_picker = picker
        picker.sig_range_changed.connect(self._on_depth_changed)
        for block in self._tiles:
            self._connect_depth(block)

    # ---- Private -------------------------------------------------------------

    def _equalize_sizes(self) -> None:
        n = len(self._tiles)
        if n > 0:
            total = self.width() or 900
            self.setSizes([total // n] * n)

    def _connect_depth(self, block: AnalysisBlock) -> None:
        """개별 블록에 depth range 적용."""
        if self._depth_picker is None:
            return
        min_m, max_m = self._depth_picker.get_range()
        self._apply_depth_to_block(block, min_m, max_m)

    def _on_depth_changed(self, min_m: float, max_m: float) -> None:
        for block in self._tiles:
            self._apply_depth_to_block(block, min_m, max_m)

    @staticmethod
    def _apply_depth_to_block(block: AnalysisBlock, min_m: float, max_m: float) -> None:
        if block.chart_is_pyqtgraph and hasattr(block, "_chart_plot"):
            plot = block._chart_plot
            if plot is not None:
                plot.setXRange(min_m, max_m, padding=0)


__all__ = ["TiledAnalysisWindow"]
