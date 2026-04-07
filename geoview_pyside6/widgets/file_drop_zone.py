"""
GeoView PySide6 — FileDropZone Widget
=======================================
파일 드래그앤드롭 영역. 확장자 필터, 브라우즈 버튼, 컴팩트 모드 지원.
24개 프로그램이 공유하는 범용 파일 입력 위젯.

Usage::

    from geoview_pyside6.widgets.file_drop_zone import FileDropZone

    drop = FileDropZone(
        accepted_extensions={".csv", ".txt", ".dat"},
        title="MAG 파일을 여기에 드래그",
        icon_name="upload",
    )
    drop.files_dropped.connect(on_files)

    # Compact (toolbar / header row)
    drop_compact = FileDropZone(
        accepted_extensions={".sgy", ".segy"},
        title="SEG-Y 파일 드롭",
        compact=True,
    )
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    Qt, Signal, QTimer,
    QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup,
)
from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QSizePolicy, QGraphicsOpacityEffect,
    QWidget,
)

from geoview_pyside6.constants import Font, Space, Radius, rgba
from geoview_pyside6.theme_aware import c
from geoview_pyside6.icons.icon_engine import icon_pixmap

if TYPE_CHECKING:
    pass


class FileDropZone(QFrame):
    """
    파일 드래그앤드롭 영역.

    Signals:
        files_dropped(list[str]): 유효 확장자의 파일 경로 리스트.

    Args:
        accepted_extensions: 허용 확장자 집합 (예: {".csv", ".txt"}).
            None이면 모든 파일 허용.
        title: 중앙 안내 텍스트.
        subtitle: 보조 텍스트. 비어 있으면 허용 확장자를 자동 표시.
        icon_name: Lucide SVG 아이콘 이름 (기본 "upload").
        browse_enabled: 파일 탐색 버튼 표시 여부.
        compact: True이면 단일 행 레이아웃 (46px).
        parent: 부모 위젯.
    """

    files_dropped = Signal(list)  # list[str]

    # ── 초기화 ──────────────────────────────────────

    def __init__(
        self,
        accepted_extensions: set[str] | None = None,
        title: str = "Drop files here",
        subtitle: str = "",
        icon_name: str = "upload",
        browse_enabled: bool = True,
        compact: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._accepted_exts: set[str] | None = (
            {e.lower() if e.startswith(".") else f".{e.lower()}"
             for e in accepted_extensions}
            if accepted_extensions else None
        )
        self._title_text = title
        self._subtitle_text = subtitle
        self._icon_name = icon_name
        self._browse_enabled = browse_enabled
        self._compact = compact
        self._drag_over = False
        self._enabled = True

        self.setAcceptDrops(True)
        self.setObjectName("FileDropZone")
        self.setAccessibleName(title or "File drop zone")

        if compact:
            self.setFixedHeight(46)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        else:
            self.setMinimumHeight(160)
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._build_ui()
        self._apply_frame_style()

    # ── UI 구성 ────────────────────────────────────

    def _build_ui(self):
        if self._compact:
            self._build_compact()
        else:
            self._build_normal()

    def _build_compact(self):
        """Single-row: [icon] [title] ... [browse]"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.MD, Space.XS, Space.MD, Space.XS)
        layout.setSpacing(Space.SM)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setObjectName("dropZoneIconCompact")
        self._icon_label.setFixedSize(24, 24)
        pm = icon_pixmap(self._icon_name, size=24, color=c().DIM)
        self._icon_label.setPixmap(pm)
        self._icon_label.setStyleSheet("background:transparent; border:none;")
        layout.addWidget(self._icon_label)

        # Title
        self._title_label = QLabel(self._title_text)
        self._title_label.setObjectName("dropZoneTitleCompact")
        self._title_label.setStyleSheet(f"""
            color: {c().MUTED};
            font-size: {Font.SM}px;
            font-weight: {Font.MEDIUM};
            font-family: {Font.SANS};
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._title_label)
        layout.addStretch()

        # Browse
        if self._browse_enabled:
            self._browse_btn = QPushButton("Browse Files")
            self._browse_btn.setObjectName("dropZoneBrowseCompact")
            self._browse_btn.setCursor(Qt.PointingHandCursor)
            self._browse_btn.setStyleSheet(self._browse_button_qss())
            self._browse_btn.clicked.connect(self._browse_files)
            layout.addWidget(self._browse_btn)

    def _build_normal(self):
        """Centered vertical stack: icon-area / title / subtitle / browse / ext-hint."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(Space.XL, 48, Space.XL, 48)
        layout.setSpacing(Space.SM)

        # ── Icon area: accent-tinted rounded square ──
        icon_container = QWidget()
        icon_container.setObjectName("dropZoneIconArea")
        icon_container.setFixedSize(56, 56)
        icon_container.setStyleSheet(f"""
            #dropZoneIconArea {{
                background: {rgba(c().CYAN, 0.1)};
                border-radius: {Radius.LG}px;
                border: none;
            }}
        """)

        icon_inner = QVBoxLayout(icon_container)
        icon_inner.setContentsMargins(0, 0, 0, 0)
        icon_inner.setAlignment(Qt.AlignCenter)

        self._icon_label = QLabel()
        self._icon_label.setObjectName("dropZoneIcon")
        self._icon_label.setFixedSize(28, 28)
        self._icon_label.setAlignment(Qt.AlignCenter)
        pm = icon_pixmap(self._icon_name, size=28, color=c().CYAN)
        self._icon_label.setPixmap(pm)
        self._icon_label.setStyleSheet("background: transparent; border: none;")
        icon_inner.addWidget(self._icon_label, alignment=Qt.AlignCenter)

        self._icon_container = icon_container
        layout.addWidget(icon_container, alignment=Qt.AlignCenter)

        layout.addSpacing(Space.SM)

        # ── Title ──
        self._title_label = QLabel(self._title_text)
        self._title_label.setObjectName("dropZoneTitle")
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet(f"""
            color: {c().TEXT};
            font-size: {Font.LG}px;
            font-weight: {Font.SEMIBOLD};
            font-family: {Font.SANS};
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._title_label)

        # ── Subtitle ──
        sub_text = self._subtitle_text or "또는 파일을 직접 선택하세요"
        self._subtitle_label = QLabel(sub_text)
        self._subtitle_label.setObjectName("dropZoneSubtitle")
        self._subtitle_label.setAlignment(Qt.AlignCenter)
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setStyleSheet(f"""
            color: {c().DIM};
            font-size: {Font.BASE}px;
            font-family: {Font.SANS};
            background: transparent;
            border: none;
        """)
        layout.addWidget(self._subtitle_label)

        layout.addSpacing(Space.SM)

        # ── Browse button (accent styled) ──
        if self._browse_enabled:
            self._browse_btn = QPushButton("Browse Files")
            self._browse_btn.setObjectName("dropZoneBrowse")
            self._browse_btn.setCursor(Qt.PointingHandCursor)
            self._browse_btn.setFixedHeight(34)
            self._browse_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {c().CYAN};
                    color: #ffffff;
                    border: none;
                    border-radius: {Radius.BASE}px;
                    font-size: {Font.SM}px;
                    font-weight: {Font.MEDIUM};
                    font-family: {Font.SANS};
                    padding: 6px 20px;
                }}
                QPushButton:hover {{
                    background: {c().CYAN_H};
                }}
                QPushButton:pressed {{
                    background: {c().CYAN};
                    opacity: 0.85;
                }}
                QPushButton:disabled {{
                    background: {c().SLATE};
                    color: {c().DIM};
                }}
            """)
            self._browse_btn.clicked.connect(self._browse_files)
            layout.addWidget(self._browse_btn, alignment=Qt.AlignCenter)

        layout.addSpacing(Space.XS)

        # ── Extensions hint (monospace, dim) ──
        ext_hint = self._extensions_hint()
        if ext_hint:
            self._ext_label = QLabel(ext_hint)
            self._ext_label.setObjectName("dropZoneExtHint")
            self._ext_label.setAlignment(Qt.AlignCenter)
            self._ext_label.setStyleSheet(f"""
                color: {c().DIM};
                font-size: 10px;
                font-family: {Font.MONO};
                background: transparent;
                border: none;
                letter-spacing: 0.5px;
            """)
            layout.addWidget(self._ext_label)

    # ── 공개 API ──────────────────────────────────

    def set_accepted_extensions(self, exts: set[str]):
        """런타임에 허용 확장자 변경."""
        self._accepted_exts = {
            e.lower() if e.startswith(".") else f".{e.lower()}"
            for e in exts
        }
        # subtitle이 자동 생성이었으면 갱신
        if not self._subtitle_text and not self._compact:
            if hasattr(self, '_ext_label'):
                self._ext_label.setText(self._extensions_hint())

    def set_enabled_state(self, enabled: bool):
        """드롭 영역 활성/비활성 전환."""
        self._enabled = enabled
        self.setAcceptDrops(enabled)

        opacity = 1.0 if enabled else 0.45
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(opacity)
        self.setGraphicsEffect(effect)

        if hasattr(self, "_browse_btn"):
            self._browse_btn.setEnabled(enabled)

    # ── Drag & Drop 이벤트 ────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if not self._enabled:
            event.ignore()
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_over = True
            self._apply_frame_style()
            self._apply_drag_over_visuals()
            self._start_icon_float()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        self._drag_over = False
        self._apply_frame_style()
        self._apply_normal_visuals()
        self._stop_icon_float()

    def dropEvent(self, event: QDropEvent):
        self._drag_over = False
        self._apply_frame_style()
        self._apply_normal_visuals()
        self._stop_icon_float()

        if not self._enabled:
            return

        paths: list[str] = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if not os.path.isfile(path):
                continue
            if self._accepted_exts is None:
                paths.append(path)
            else:
                ext = os.path.splitext(path)[1].lower()
                if ext in self._accepted_exts:
                    paths.append(path)

        if paths:
            self.files_dropped.emit(paths)
            self._drop_bounce()

    def _drop_bounce(self):
        """Scale bounce after successful drop: 1.0 -> 0.97 -> 1.0 over 200ms."""
        cur_min = self.minimumSize()
        cur_max = self.maximumSize()
        # Only animate the minimum height for squeeze effect
        base_h = self.height()
        squeeze_h = int(base_h * 0.97)

        group = QSequentialAnimationGroup(self)
        # Phase 1: squeeze
        squeeze = QPropertyAnimation(self, b"minimumHeight", self)
        squeeze.setDuration(100)
        squeeze.setStartValue(base_h)
        squeeze.setEndValue(squeeze_h)
        squeeze.setEasingCurve(QEasingCurve.Type.OutQuad)
        group.addAnimation(squeeze)
        # Phase 2: release back
        release = QPropertyAnimation(self, b"minimumHeight", self)
        release.setDuration(100)
        release.setStartValue(squeeze_h)
        release.setEndValue(base_h if not self._compact else 46)
        release.setEasingCurve(QEasingCurve.Type.InOutQuad)
        group.addAnimation(release)
        group.start(QSequentialAnimationGroup.DeletionPolicy.DeleteWhenStopped)

    # ── 파일 탐색 대화상자 ────────────────────────

    def _browse_files(self):
        if self._accepted_exts:
            desc = " ".join(f"*{e}" for e in sorted(self._accepted_exts))
            filt = f"Accepted Files ({desc});;All Files (*)"
        else:
            filt = "All Files (*)"

        paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", filt)
        if paths:
            self.files_dropped.emit(paths)

    # ── 스타일 / 시각 효과 ────────────────────────

    def _apply_frame_style(self):
        """Apply QSS for the drop zone frame in normal or drag-over state."""
        if self._drag_over:
            self.setStyleSheet(f"""
                FileDropZone {{
                    background: {c().NAVY};
                    border: 2px solid {c().CYAN};
                    border-radius: {Radius.LG}px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                FileDropZone {{
                    background: {c().NAVY};
                    border: 2px dashed {c().BORDER};
                    border-radius: {Radius.LG}px;
                }}
                FileDropZone:hover {{
                    border-color: {rgba(c().CYAN, 0.25)};
                }}
            """)

    def _apply_drag_over_visuals(self):
        """드래그 진입 시 아이콘 강조 + 텍스트 밝게."""
        if self._compact:
            pm = icon_pixmap(self._icon_name, size=24, color=c().CYAN)
            self._icon_label.setPixmap(pm)
            self._title_label.setStyleSheet(f"""
                color: {c().TEXT_BRIGHT};
                font-size: {Font.SM}px;
                font-weight: {Font.MEDIUM};
                font-family: {Font.SANS};
                background: transparent;
                border: none;
            """)
        else:
            # Icon becomes brighter
            pm = icon_pixmap(self._icon_name, size=28, color=c().CYAN)
            self._icon_label.setPixmap(pm)

            # Icon area gets stronger accent tint
            self._icon_container.setStyleSheet(f"""
                #dropZoneIconArea {{
                    background: {rgba(c().CYAN, 0.25)};
                    border-radius: {Radius.LG}px;
                    border: none;
                }}
            """)

            # Title brighter
            self._title_label.setStyleSheet(f"""
                color: {c().TEXT_BRIGHT};
                font-size: {Font.LG}px;
                font-weight: {Font.SEMIBOLD};
                font-family: {Font.SANS};
                background: transparent;
                border: none;
            """)

    def _apply_normal_visuals(self):
        """드래그 해제 시 원래 시각 상태 복원."""
        if self._compact:
            pm = icon_pixmap(self._icon_name, size=24, color=c().DIM)
            self._icon_label.setPixmap(pm)
            self._title_label.setStyleSheet(f"""
                color: {c().MUTED};
                font-size: {Font.SM}px;
                font-weight: {Font.MEDIUM};
                font-family: {Font.SANS};
                background: transparent;
                border: none;
            """)
        else:
            pm = icon_pixmap(self._icon_name, size=28, color=c().CYAN)
            self._icon_label.setPixmap(pm)

            # Restore icon area
            self._icon_container.setStyleSheet(f"""
                #dropZoneIconArea {{
                    background: {rgba(c().CYAN, 0.1)};
                    border-radius: {Radius.LG}px;
                    border: none;
                }}
            """)

            # Restore title
            self._title_label.setStyleSheet(f"""
                color: {c().TEXT};
                font-size: {Font.LG}px;
                font-weight: {Font.SEMIBOLD};
                font-family: {Font.SANS};
                background: transparent;
                border: none;
            """)

    # ── 아이콘 플로트 애니메이션 (드래그 중) ─────────

    def _start_icon_float(self):
        """드래그 오버 중 아이콘을 위아래로 부드럽게 띄움."""
        if not hasattr(self, '_drag_float_timer'):
            self._drag_float_offset = 0.0
            self._drag_float_dir = 1
            self._drag_float_timer = QTimer(self)
            self._drag_float_timer.setInterval(50)
            self._drag_float_timer.timeout.connect(self._drag_float_tick)
        self._drag_float_offset = 0.0
        self._drag_float_dir = 1
        self._drag_float_timer.start()

    def _drag_float_tick(self):
        self._drag_float_offset += self._drag_float_dir * 0.5
        if abs(self._drag_float_offset) > 6:
            self._drag_float_dir *= -1
        self._icon_label.setContentsMargins(0, int(self._drag_float_offset), 0, 0)

    def _stop_icon_float(self):
        """플로트 애니메이션 정지 및 원래 위치 복원."""
        if hasattr(self, '_drag_float_timer'):
            self._drag_float_timer.stop()
            self._icon_label.setContentsMargins(0, 0, 0, 0)

    # ── QSS helpers ──────────────────────────────

    def _browse_button_qss(self) -> str:
        """Browse button QSS for compact mode."""
        return f"""
            QPushButton {{
                background: transparent;
                color: {c().MUTED};
                border: 1px solid {c().BORDER};
                border-radius: {Radius.SM}px;
                font-size: {Font.SM}px;
                font-family: {Font.SANS};
                padding: 5px 14px;
            }}
            QPushButton:hover {{
                background: {c().DARK};
                color: {c().TEXT};
                border-color: {c().BORDER_H};
            }}
            QPushButton:pressed {{
                background: {c().SLATE};
            }}
            QPushButton:disabled {{
                color: {c().DIM};
                border-color: {c().BORDER};
            }}
        """

    # ── 테마 갱신 ─────────────────────────────────

    def refresh_theme(self):
        """Re-apply all theme-dependent styles after a theme switch."""
        self._apply_frame_style()
        self._apply_normal_visuals()
        if self._browse_enabled and hasattr(self, '_browse_btn'):
            if self._compact:
                self._browse_btn.setStyleSheet(self._browse_button_qss())
            else:
                self._browse_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {c().CYAN};
                        color: #ffffff;
                        border: none;
                        border-radius: {Radius.BASE}px;
                        font-size: {Font.SM}px;
                        font-weight: {Font.MEDIUM};
                        font-family: {Font.SANS};
                        padding: 6px 20px;
                    }}
                    QPushButton:hover {{
                        background: {c().CYAN_H};
                    }}
                    QPushButton:pressed {{
                        background: {c().CYAN};
                        opacity: 0.85;
                    }}
                    QPushButton:disabled {{
                        background: {c().SLATE};
                        color: {c().DIM};
                    }}
                """)
        # Subtitle
        if not self._compact and hasattr(self, '_subtitle_label'):
            self._subtitle_label.setStyleSheet(f"""
                color: {c().DIM};
                font-size: {Font.BASE}px;
                font-family: {Font.SANS};
                background: transparent;
                border: none;
            """)
        # Extensions hint
        if not self._compact and hasattr(self, '_ext_label'):
            self._ext_label.setStyleSheet(f"""
                color: {c().DIM};
                font-size: 10px;
                font-family: {Font.MONO};
                background: transparent;
                border: none;
                letter-spacing: 0.5px;
            """)

    # ── 유틸리티 ──────────────────────────────────

    def _extensions_hint(self) -> str:
        """허용 확장자를 보조 텍스트로 포맷."""
        if not self._accepted_exts:
            return ""
        return " ".join(sorted(self._accepted_exts))
