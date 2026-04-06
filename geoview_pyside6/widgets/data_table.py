"""
GeoView Data Table Widget
===========================
QTableView with professional styling. All colors via c(), fonts via Font.

Background: c().BG
Alternate row: c().BG_ALT
Border: 1px solid c().BORDER, 8px radius
Header: c().BG_ALT bg, c().MUTED text, 11px uppercase semibold
Row hover: subtle background (c().DARK)
Cell padding: 8px 12px
Selection: accent_dim background
"""

from PySide6.QtWidgets import (
    QTableView, QHeaderView, QAbstractItemView, QLabel,
    QFrame, QVBoxLayout, QPushButton, QSizePolicy,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle,
)
from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QAbstractTableModel,
    QModelIndex, Signal, QTimer, QRect, QSize,
)
from PySide6.QtGui import (
    QPixmap, QShortcut, QKeySequence, QPainter, QColor, QFont, QPen, QBrush,
)
from typing import Any

from geoview_pyside6.constants import Font, Space, Radius, Opacity
from geoview_pyside6.theme_aware import c

try:
    from geoview_pyside6.icons import icon_pixmap as _icon_pixmap
except Exception:
    _icon_pixmap = None


# =============================================
# Empty State Overlay (internal)
# =============================================

class _EmptyStateOverlay(QFrame):
    """Table empty state overlay: icon + message + optional action button."""

    action_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent; border: none;")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(Space.SM)
        layout.setContentsMargins(Space.XXL, Space.XXL, Space.XXL, Space.XXL)

        # Icon
        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(48, 48)
        self._icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(Space.XS)

        # Title message
        self._title_label = QLabel("No data available")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(
            f"color: {c().MUTED};"
            f" font-size: {Font.MD}px;"
            f" font-family: \"{Font.SANS}\";"
            f" font-weight: {Font.MEDIUM};"
            f" background: transparent;"
        )
        layout.addWidget(self._title_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Subtitle
        self._subtitle_label = QLabel()
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setStyleSheet(
            f"color: {c().DIM};"
            f" font-size: {Font.XS}px;"
            f" font-family: \"{Font.SANS}\";"
            f" background: transparent;"
        )
        self._subtitle_label.setVisible(False)
        layout.addWidget(self._subtitle_label, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(Space.MD)

        # Action button
        self._action_btn = QPushButton()
        self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._action_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._action_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {c().GREEN};"
            f"  color: {c().BG};"
            f"  border: none;"
            f"  border-radius: {Radius.SM}px;"
            f"  font-size: {Font.SM}px;"
            f"  font-family: \"{Font.SANS}\";"
            f"  font-weight: {Font.SEMIBOLD};"
            f"  padding: 6px 20px;"
            f"}}"
            f"QPushButton:hover {{ background: {c().GREEN_H}; }}"
        )
        self._action_btn.setVisible(False)
        self._action_btn.clicked.connect(self.action_clicked)
        layout.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignCenter)

        self._current_icon_name = ""
        self._lbl = self._title_label
        self._sub = self._subtitle_label
        self._btn = self._action_btn

        # Floating animation for icon
        self._float_offset = 0.0
        self._float_direction = 1
        self._float_timer = QTimer(self)
        self._float_timer.setInterval(50)
        self._float_timer.timeout.connect(self._float_tick)

    def _float_tick(self):
        self._float_offset += self._float_direction * 0.4
        if abs(self._float_offset) > 6:
            self._float_direction *= -1
        margin = int(self._float_offset)
        self._icon_label.setContentsMargins(0, margin, 0, 0)

    def refresh_theme(self):
        """Re-apply theme colors to all child labels."""
        self._lbl.setStyleSheet(
            f"color: {c().MUTED};"
            f" font-size: {Font.MD}px;"
            f" font-family: \"{Font.SANS}\";"
            f" font-weight: {Font.MEDIUM};"
            f" background: transparent;"
        )
        self._sub.setStyleSheet(
            f"color: {c().DIM};"
            f" font-size: {Font.XS}px;"
            f" font-family: \"{Font.SANS}\";"
            f" background: transparent;"
        )
        self._btn.setStyleSheet(
            f"QPushButton {{"
            f"  background: {c().GREEN};"
            f"  color: {c().BG};"
            f"  border: none;"
            f"  border-radius: {Radius.SM}px;"
            f"  font-size: {Font.SM}px;"
            f"  font-family: \"{Font.SANS}\";"
            f"  font-weight: {Font.SEMIBOLD};"
            f"  padding: 6px 20px;"
            f"}}"
            f"QPushButton:hover {{ background: {c().GREEN_H}; }}"
        )
        # Re-tint icon if present
        if self._current_icon_name and _icon_pixmap is not None:
            pm = _icon_pixmap(self._current_icon_name, size=48, color=c().DIM)
            self._icon_label.setPixmap(pm)

    def configure(self, message: str = "No data available",
                  icon_name: str = "database",
                  subtitle: str = "",
                  action_text: str = ""):
        """Update icon, message, subtitle, and action button."""
        if icon_name != self._current_icon_name:
            self._current_icon_name = icon_name
            if _icon_pixmap is not None and icon_name:
                pm = _icon_pixmap(icon_name, size=48, color=c().DIM)
                self._icon_label.setPixmap(pm)
            else:
                self._icon_label.clear()
            self._icon_label.setVisible(bool(icon_name))

        self._title_label.setText(message)

        if subtitle:
            self._subtitle_label.setText(subtitle)
            self._subtitle_label.setVisible(True)
        else:
            self._subtitle_label.setVisible(False)

        if action_text:
            self._action_btn.setText(action_text)
            self._action_btn.setVisible(True)
        else:
            self._action_btn.setVisible(False)

        if icon_name:
            from geoview_pyside6.effects import anim_duration
            if anim_duration(100) > 0:
                self._float_offset = 0.0
                self._float_direction = 1
                self._float_timer.start()
            else:
                self._float_timer.stop()
        else:
            self._float_timer.stop()


# =============================================
# Table Model
# =============================================

class GVTableModel(QAbstractTableModel):

    def __init__(self, headers: list[str], data: list[list[Any]], parent=None):
        super().__init__(parent)
        self._headers = headers
        self._data = data
        self._numeric_cols: set[int] = set()

    def set_numeric_columns(self, cols: list[int]):
        self._numeric_cols = set(cols)

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            value = self._data[index.row()][index.column()]
            if index.column() in self._numeric_cols and isinstance(value, (int, float)):
                return f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"
            return str(value) if value is not None else "\u2014"

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # SortRole: numeric columns use raw value for proper numeric sorting
        if role == Qt.ItemDataRole.UserRole:
            value = self._data[index.row()][index.column()]
            if index.column() in self._numeric_cols and isinstance(value, (int, float)):
                return value
            return str(value).lower() if value is not None else ""

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def update_data(self, data: list[list[Any]]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


# =============================================
# Table View
# =============================================

def _build_table_qss() -> str:
    """Build the full QSS for the table. Called at construction to pick up
    current theme colors via c()."""
    return (
        # Main table frame
        f"QTableView {{"
        f"  background: {c().BG};"
        f"  alternate-background-color: {c().BG_ALT};"
        f"  color: {c().TEXT};"
        f"  border: 1px solid {c().BORDER};"
        f"  border-radius: {Radius.BASE}px;"
        f"  font-size: {Font.SM}px;"
        f"  font-family: \"{Font.SANS}\";"
        f"  gridline-color: transparent;"
        f"  outline: none;"
        f"}}"

        # Cell items
        f"QTableView::item {{"
        f"  padding: {Space.SM}px {Space.MD}px;"
        f"  border: none;"
        f"  border-bottom: 1px solid {c().BORDER};"
        f"}}"

        # Hover
        f"QTableView::item:hover {{"
        f"  background: {c().DARK};"
        f"}}"

        # Selection
        f"QTableView::item:selected {{"
        f"  background: {c().CYAN}{Opacity.LOW};"
        f"  color: {c().TEXT_BRIGHT};"
        f"}}"

        # Header: uppercase, muted, sticky feel
        f"QHeaderView::section {{"
        f"  background: {c().BG_ALT};"
        f"  color: {c().MUTED};"
        f"  font-size: {Font.XS}px;"
        f"  font-weight: {Font.SEMIBOLD};"
        f"  text-transform: uppercase;"
        f"  letter-spacing: {Font.TRACK_XS};"
        f"  border: none;"
        f"  border-bottom: 1px solid {c().BORDER};"
        f"  padding: {Space.SM}px {Space.MD}px;"
        f"}}"

        # Sort indicator
        f"QHeaderView::down-arrow {{"
        f"  image: none; subcontrol-position: right center;"
        f"}}"
        f"QHeaderView::up-arrow {{"
        f"  image: none; subcontrol-position: right center;"
        f"}}"

        # Scrollbar
        f"QScrollBar:vertical {{"
        f"  background: transparent; width: 6px; border: none;"
        f"}}"
        f"QScrollBar::handle:vertical {{"
        f"  background: {c().BORDER_H}; border-radius: 3px; min-height: 20px;"
        f"}}"
        f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{"
        f"  height: 0; border: none;"
        f"}}"
        f"QScrollBar:horizontal {{"
        f"  background: transparent; height: 6px; border: none;"
        f"}}"
        f"QScrollBar::handle:horizontal {{"
        f"  background: {c().BORDER_H}; border-radius: 3px; min-width: 20px;"
        f"}}"
        f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{"
        f"  width: 0; border: none;"
        f"}}"

        # Corner
        f"QTableView QTableCornerButton::section {{"
        f"  background: {c().BG_ALT}; border: none;"
        f"}}"
    )


class GVTableView(QTableView):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setSortingEnabled(True)

        h = self.horizontalHeader()
        h.setStretchLastSection(True)
        h.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        h.setDefaultSectionSize(120)
        h.setMinimumSectionSize(60)
        h.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        h.setHighlightSections(False)

        self.verticalHeader().setDefaultSectionSize(40)

        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)

        self._model: GVTableModel | None = None

        # Apply professional styling
        self.setStyleSheet(_build_table_qss())

        # Ctrl+C copy shortcut
        QShortcut(QKeySequence.StandardKey.Copy, self, self._copy_selection)

        # Context menu (right-click on table body)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Column visibility toggle (right-click on header)
        h.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        h.customContextMenuRequested.connect(self._show_column_menu)

        # Empty state overlay
        self._empty_overlay = _EmptyStateOverlay(self)
        self._empty_overlay.setVisible(False)

    # -- Data management --

    def set_data(
        self,
        headers: list[str],
        data: list[list[Any]],
        numeric_cols: list[int] | None = None,
        animate: bool = True,
    ):
        self._model = GVTableModel(headers, data)
        if numeric_cols:
            self._model.set_numeric_columns(numeric_cols)
        self._proxy.setSourceModel(self._model)
        super().setModel(self._proxy)

        if animate:
            self._stagger_rows()

    def _stagger_rows(self):
        """Stagger-reveal first 20 rows with 30ms delay each."""
        from geoview_pyside6.effects import anim_duration
        if anim_duration(100) == 0:
            return

        model = self.model()
        if not model:
            return
        row_count = min(20, model.rowCount())

        for row in range(row_count):
            self.setRowHidden(row, True)

        for row in range(row_count):
            QTimer.singleShot(row * 30, lambda r=row: self._reveal_row(r))

    def _reveal_row(self, row: int):
        self.setRowHidden(row, False)

    def update_data(self, data: list[list[Any]]):
        if self._model:
            self._model.update_data(data)

    # -- Empty state --

    def show_empty_state(self, message: str = "No data available",
                         icon_name: str = "database",
                         subtitle: str = "",
                         action_text: str = ""):
        self._empty_overlay.configure(
            message=message, icon_name=icon_name,
            subtitle=subtitle, action_text=action_text,
        )
        self._empty_overlay.setGeometry(self.viewport().rect())
        self._empty_overlay.raise_()
        self._empty_overlay.setVisible(True)

    def hide_empty_state(self):
        self._empty_overlay._float_timer.stop()
        self._empty_overlay.setVisible(False)

    def set_filter_text(self, text: str):
        """Apply proxy filter + auto-show empty message."""
        if self._proxy:
            self._proxy.setFilterFixedString(text)
            self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            if text and self._proxy.rowCount() == 0:
                source = self._proxy.sourceModel()
                if source and source.rowCount() > 0:
                    self.show_empty_state(
                        "No results matching filter",
                        icon_name="search",
                        subtitle="Try a different search term",
                    )
                    return
            self.hide_empty_state()

    @property
    def empty_state(self) -> _EmptyStateOverlay:
        return self._empty_overlay

    # -- Skeleton loading --

    def show_skeleton(self, rows: int = 5):
        if not hasattr(self, '_skeleton_overlay'):
            from geoview_pyside6.widgets.skeleton_loader import SkeletonTableRows
            cols = self.model().columnCount() if self.model() else 4
            self._skeleton_overlay = SkeletonTableRows(
                rows=rows, columns=cols, parent=self
            )
        self._skeleton_overlay.setGeometry(self.viewport().rect())
        self._skeleton_overlay.raise_()
        self._skeleton_overlay.show()

    def hide_skeleton(self):
        if hasattr(self, '_skeleton_overlay') and self._skeleton_overlay:
            self._skeleton_overlay.hide()

    # -- Clipboard / Context Menu --

    def _copy_selection(self):
        from PySide6.QtWidgets import QApplication
        selection = self.selectionModel().selectedIndexes()
        if not selection:
            return

        rows: dict[int, dict[int, str]] = {}
        for idx in selection:
            source = self._proxy.mapToSource(idx) if self._proxy else idx
            row = source.row()
            col = source.column()
            if row not in rows:
                rows[row] = {}
            rows[row][col] = str(source.data() or "")

        lines = []
        for row_num in sorted(rows):
            cols = rows[row_num]
            line = "\t".join(cols.get(c_idx, "") for c_idx in range(max(cols.keys()) + 1))
            lines.append(line)

        QApplication.clipboard().setText("\n".join(lines))

    def _show_context_menu(self, pos):
        from geoview_pyside6.widgets.context_menu import create_context_menu

        index = self.indexAt(pos)
        items = []

        if index.isValid():
            items.append(("Copy Cell", lambda: self._copy_cell(index)))
            items.append(("Copy Row", lambda: self._copy_row(index)))
        items.append(None)  # separator
        items.append(("Copy All", self._copy_all))

        menu = create_context_menu(self, items)
        menu.exec(self.viewport().mapToGlobal(pos))

    def _copy_cell(self, index):
        from PySide6.QtWidgets import QApplication
        source = self._proxy.mapToSource(index) if self._proxy else index
        QApplication.clipboard().setText(str(source.data() or ""))

    def _copy_row(self, index):
        from PySide6.QtWidgets import QApplication
        source = self._proxy.mapToSource(index) if self._proxy else index
        model = source.model()
        if not model:
            return
        row = source.row()
        cols = model.columnCount()
        parts = [str(model.index(row, c_idx).data() or "") for c_idx in range(cols)]
        QApplication.clipboard().setText("\t".join(parts))

    def _copy_all(self):
        from PySide6.QtWidgets import QApplication
        model = self._model
        if not model:
            return

        lines = []
        headers = [
            str(model.headerData(c_idx, Qt.Orientation.Horizontal) or "")
            for c_idx in range(model.columnCount())
        ]
        lines.append("\t".join(headers))

        for r in range(model.rowCount()):
            parts = [str(model.index(r, c_idx).data() or "") for c_idx in range(model.columnCount())]
            lines.append("\t".join(parts))

        QApplication.clipboard().setText("\n".join(lines))

    def _show_column_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        from PySide6.QtGui import QAction

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background: {c().NAVY}; color: {c().TEXT}; "
            f"border: 1px solid {c().BORDER}; border-radius: {Radius.SM}px; padding: 4px; "
            f"font-family: \"{Font.SANS}\"; font-size: {Font.XS}px; }}"
            f"QMenu::item {{ padding: 4px 12px; border-radius: 4px; margin: 1px 4px; }}"
            f"QMenu::item:selected {{ background: {c().SLATE}; }}"
        )

        model = self.model()
        if not model:
            return
        for col in range(model.columnCount()):
            header_text = model.headerData(col, Qt.Orientation.Horizontal) or f"Column {col}"
            action = QAction(str(header_text), menu)
            action.setCheckable(True)
            action.setChecked(not self.isColumnHidden(col))
            action.toggled.connect(lambda checked, c_idx=col: self.setColumnHidden(c_idx, not checked))
            menu.addAction(action)
        menu.exec(self.horizontalHeader().mapToGlobal(pos))

    # -- Theme --

    def refresh_theme(self):
        """Re-apply all theme-dependent QSS after a theme switch."""
        self.setStyleSheet(_build_table_qss())
        self._empty_overlay.refresh_theme()

    # -- Events --

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._empty_overlay.isVisible():
            self._empty_overlay.setGeometry(self.viewport().rect())
        if (hasattr(self, '_skeleton_overlay')
                and self._skeleton_overlay
                and self._skeleton_overlay.isVisible()):
            self._skeleton_overlay.setGeometry(self.viewport().rect())
