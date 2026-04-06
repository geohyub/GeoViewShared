"""
GeoView SVG Icon Engine
========================
Lucide SVG 아이콘을 QIcon으로 변환하며, 다크 테마 색상을 자동 적용한다.
stroke="currentColor"를 지정된 색상으로 런타임 치환.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QSize, QRect
from PySide6.QtGui import (
    QIcon, QIconEngine, QPainter, QPixmap, QColor, QImage,
)
from PySide6.QtSvg import QSvgRenderer

_logger = logging.getLogger(__name__)

# ── 아이콘 디렉토리 ─────────────────────────────
ICON_DIR = Path(__file__).parent / "svg"

# ── GeoView 테마 기본 아이콘 색상 ──────────
# QPalette는 QSS와 동기화되지 않으므로, theme_aware.c()를 사용한다.
from geoview_pyside6.theme_aware import c


def _default_colors() -> dict[str, str]:
    """현재 테마에 맞는 기본 아이콘 색상을 반환한다."""
    return {
        "normal":   c().MUTED,
        "active":   c().TEXT,
        "disabled": c().DIM + "40",
    }


class SvgIconEngine(QIconEngine):
    """
    SVG 파일을 읽어 QIcon으로 렌더링하는 커스텀 엔진.
    stroke/fill의 currentColor를 지정 색상 또는 다크 테마 기본색으로 치환.
    """

    def __init__(self, svg_content: str, color: str | None = None):
        super().__init__()
        self._svg_raw = svg_content
        self._color = color  # None이면 다크 테마 기본색 사용

    # ── QIconEngine 오버라이드 ──

    def pixmap(self, size: QSize, mode: QIcon.Mode,
               state: QIcon.State) -> QPixmap:
        img = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        painter = QPainter(img)
        self.paint(painter, QRect(0, 0, size.width(), size.height()),
                   mode, state)
        painter.end()
        return QPixmap.fromImage(img)

    def paint(self, painter: QPainter, rect: QRect,
              mode: QIcon.Mode, state: QIcon.State):
        color = self._resolve_color(mode)
        svg_data = self._recolor_svg(color)

        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        if renderer.isValid():
            renderer.render(painter, rect)

    def clone(self) -> "SvgIconEngine":
        return SvgIconEngine(self._svg_raw, self._color)

    # ── 내부 메서드 ──

    def _resolve_color(self, mode: QIcon.Mode) -> QColor:
        """명시 색상이 있으면 사용, 없으면 다크 테마 기본색 적용."""
        if self._color:
            c = QColor(self._color)
            if mode == QIcon.Mode.Disabled:
                c.setAlpha(100)
            return c

        # QPalette 대신 theme_aware.c() 동적 색상 사용
        colors = _default_colors()
        if mode == QIcon.Mode.Disabled:
            return QColor(colors["disabled"])
        elif mode == QIcon.Mode.Selected or mode == QIcon.Mode.Active:
            return QColor(colors["active"])
        else:
            return QColor(colors["normal"])

    def _recolor_svg(self, color: QColor) -> str:
        """SVG의 stroke/fill currentColor를 실제 색상으로 치환."""
        hex_color = color.name()  # "#RRGGBB"
        svg = self._svg_raw
        svg = svg.replace('stroke="currentColor"', f'stroke="{hex_color}"')
        svg = svg.replace('fill="currentColor"', f'fill="{hex_color}"')
        svg = svg.replace("currentColor", hex_color)
        return svg


# ── SVG 캐시 (파일 I/O 최소화) ──────────────────
_svg_cache: dict[str, str] = {}


def _load_svg(name: str) -> str | None:
    """SVG 파일 내용을 캐시하여 반환."""
    if name in _svg_cache:
        return _svg_cache[name]

    svg_path = ICON_DIR / f"{name}.svg"
    if not svg_path.exists():
        _logger.warning("Icon not found: %s", svg_path)
        return None

    content = svg_path.read_text(encoding="utf-8")
    _svg_cache[name] = content
    return content


# ── 공용 헬퍼 함수 ──────────────────────────────

def icon(name: str, color: str | None = None) -> QIcon:
    """
    Lucide 아이콘을 QIcon으로 로드.

    Args:
        name:  아이콘 이름 (확장자 제외). 예: "anchor", "compass"
        color: 색상 hex 문자열. None이면 다크 테마 기본색(#9CA3AF) 적용.

    Returns:
        QIcon 객체. SVG 없으면 빈 QIcon.
        반환된 QIcon에 _gv_icon_name 속성이 부착되어 있어
        SidebarButton 등에서 상태별 색상 전환에 활용 가능.

    Usage::

        from geoview_pyside6.icons import icon
        btn.setIcon(icon("anchor"))                  # 기본 muted 색상
        btn.setIcon(icon("compass", color="#10B981")) # 명시 accent 색상
    """
    svg_content = _load_svg(name)
    if svg_content is None:
        return QIcon()

    engine = SvgIconEngine(svg_content, color)
    qi = QIcon(engine)
    qi._gv_icon_name = name  # SidebarButton 상태 전환용
    return qi


def icon_pixmap(name: str, size: int = 24,
                color: str | None = None) -> QPixmap:
    """
    아이콘을 QPixmap으로 직접 렌더링.
    KPI 카드 아이콘 원형 배경 등에 사용.
    """
    qicon = icon(name, color or "#FFFFFF")
    return qicon.pixmap(QSize(size, size))
