"""
KPI Card Widget
================
큰 숫자 + 라벨 + 선택적 트렌드 표시.
숫자는 Geist Mono tabular-nums로 표시.
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from geoview_pyside6.constants import Font, Space
from geoview_pyside6.theme_aware import c
from geoview_pyside6.effects import apply_shadow
from geoview_pyside6.icons.icon_engine import icon_pixmap


class KPICard(QFrame):
    """
    KPI 카드 위젯.

    Usage:
        card = KPICard("📊", "1,231", "Total Tests", trend="+12%")
    """

    def __init__(
        self,
        icon: str = "📊",
        value: str = "—",
        label: str = "",
        trend: str = "",
        accent: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName("gvCard")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(Space.BASE, Space.MD, Space.BASE, Space.MD)
        layout.setSpacing(Space.SM)

        # Icon (hidden when empty)
        if icon:
            _accent = accent or c().BLUE
            icon_label = QLabel()
            icon_label.setFixedSize(44, 44)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Detect Lucide SVG name vs emoji/unicode/single-letter text
            # Single characters (len==1) are always text labels, not SVG names.
            if (len(icon) > 1
                    and icon.isascii()
                    and icon.replace("-", "").replace("_", "").isalpha()):
                # Short ASCII string like "star", "check-circle" → render SVG
                pxm = icon_pixmap(icon, 24, _accent)
                icon_label.setPixmap(pxm)
                icon_label.setStyleSheet(
                    f"background: {_accent}26; border-radius: 8px;"
                )
            else:
                # Emoji / unicode character → keep text rendering
                icon_label.setText(icon)
                icon_label.setStyleSheet(
                    f"font-size: 20px; background: {_accent}26; "
                    f"border-radius: 8px;"
                )
            layout.addWidget(icon_label)

        # Value + Label
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        # Value row (value + optional trend)
        value_row = QHBoxLayout()
        value_row.setSpacing(Space.SM)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("kpiValue")
        value_row.addWidget(self._value_label)

        if trend:
            self._trend_label = QLabel(trend)
            if trend.startswith("+"):
                self._trend_label.setObjectName("badgePass")
            elif trend.startswith("-"):
                self._trend_label.setObjectName("badgeFail")
            else:
                self._trend_label.setObjectName("badgeInfo")
            value_row.addWidget(self._trend_label)

        value_row.addStretch()
        text_layout.addLayout(value_row)

        self._label = QLabel(label)
        self._label.setObjectName("kpiLabel")
        text_layout.addWidget(self._label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Accessibility
        self.setAccessibleName(f"{label}: {value}")

        # Subtle depth
        apply_shadow(self, level=1)

    # ── Loading / Skeleton ──

    def set_loading(self, loading: bool = True):
        """스켈레톤 로딩 상태 전환.

        Args:
            loading: True이면 실제 값/라벨을 숨기고 스켈레톤 표시,
                     False이면 스켈레톤 숨기고 실제 값/라벨 표시.
        """
        if loading:
            self._value_label.hide()
            self._label.hide()
            if hasattr(self, '_trend_label'):
                self._trend_label.hide()
            # Lazy-create skeleton rects
            if not hasattr(self, '_skel_value'):
                from geoview_pyside6.widgets.skeleton_loader import SkeletonRect
                # Find the text_layout (QVBoxLayout holding value_row + label)
                main_layout = self.layout()  # QHBoxLayout
                text_layout = None
                for i in range(main_layout.count()):
                    item = main_layout.itemAt(i)
                    if item.layout() is not None:
                        text_layout = item.layout()
                        break
                if text_layout is None:
                    return
                self._skel_value = SkeletonRect(width=80, height=24, parent=self)
                self._skel_label = SkeletonRect(width=56, height=12, parent=self)
                text_layout.addWidget(self._skel_value)
                text_layout.addWidget(self._skel_label)
            self._skel_value.show()
            self._skel_label.show()
        else:
            self._value_label.show()
            self._label.show()
            if hasattr(self, '_trend_label'):
                self._trend_label.show()
            if hasattr(self, '_skel_value'):
                self._skel_value.hide()
                self._skel_label.hide()

    # ── Value / Label setters ──

    def set_value(self, value: str, animate: bool = True):
        """Set value. If animate=True, numeric values get a count-up animation."""
        old_text = self._value_label.text()

        if animate:
            old_num = self._parse_number(old_text)
            new_num = self._parse_number(value)
            if old_num is not None and new_num is not None and old_num != new_num:
                self._animate_count(old_num, new_num, value)
                return

        self._value_label.setText(value)
        self.setAccessibleName(f"{self._label.text()}: {value}")

    def _parse_number(self, text: str):
        """Extract number from text. '1,234' -> 1234, '85.3%' -> 85.3, '\u2014' -> None"""
        import re
        cleaned = re.sub(r'[,%]', '', text.strip())
        try:
            if '.' in cleaned:
                return float(cleaned)
            return int(cleaned)
        except (ValueError, TypeError):
            return None

    def _animate_count(self, start, end, final_text: str):
        """Numeric count-up animation (400ms, OutCubic easing)."""
        from PySide6.QtCore import QTimer

        self._count_steps = 20
        self._count_current = 0
        self._count_start = start
        self._count_end = end
        self._count_final = final_text
        self._count_is_float = isinstance(end, float)

        # Determine format from final_text
        self._count_has_comma = ',' in final_text
        self._count_suffix = ''
        if final_text.endswith('%'):
            self._count_suffix = '%'

        self._count_timer = QTimer(self)
        self._count_timer.setInterval(20)  # 20ms * 20 steps = 400ms
        self._count_timer.timeout.connect(self._count_tick)
        self._count_timer.start()

    def _count_tick(self):
        self._count_current += 1
        # OutCubic easing
        t = self._count_current / self._count_steps
        t = 1 - (1 - t) ** 3

        current = self._count_start + (self._count_end - self._count_start) * t

        if self._count_is_float:
            text = f"{current:.1f}"
        else:
            text = str(int(current))

        if self._count_has_comma:
            if self._count_is_float:
                parts = text.split('.')
                parts[0] = f"{int(parts[0]):,}"
                text = '.'.join(parts)
            else:
                text = f"{int(current):,}"

        text += self._count_suffix
        self._value_label.setText(text)

        if self._count_current >= self._count_steps:
            self._count_timer.stop()
            self._value_label.setText(self._count_final)
            self.setAccessibleName(f"{self._label.text()}: {self._count_final}")

    def set_label(self, label: str):
        self._label.setText(label)
