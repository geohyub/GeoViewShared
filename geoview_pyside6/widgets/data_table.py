"""
GeoView Data Table Widget
===========================
QTableView 기반 테이블. 전체 폰트 통일(Pretendard), 정렬 통일(전부 좌측).
"""

from PySide6.QtWidgets import (
    QTableView, QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel, QModelIndex
from typing import Any

from geoview_pyside6.constants import Font


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

        # 모든 셀 좌측 정렬로 통일
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # SortRole: numeric columns use raw value for proper numeric sorting
        if role == Qt.ItemDataRole.UserRole:
            value = self._data[index.row()][index.column()]
            if index.column() in self._numeric_cols and isinstance(value, (int, float)):
                return value
            return str(value).lower() if value is not None else ""

        # FontRole 반환하지 않음 — 전체 폰트 통일 (QApplication 기본 폰트 사용)
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                return self._headers[section]
            # 헤더도 전부 좌측 정렬
            if role == Qt.ItemDataRole.TextAlignmentRole:
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def update_data(self, data: list[list[Any]]):
        self.beginResetModel()
        self._data = data
        self.endResetModel()


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

        self.verticalHeader().setDefaultSectionSize(36)

        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy.setSortRole(Qt.ItemDataRole.UserRole)

        self._model: GVTableModel | None = None

    def set_data(
        self,
        headers: list[str],
        data: list[list[Any]],
        numeric_cols: list[int] | None = None
    ):
        self._model = GVTableModel(headers, data)
        if numeric_cols:
            self._model.set_numeric_columns(numeric_cols)
        self._proxy.setSourceModel(self._model)
        super().setModel(self._proxy)

    def update_data(self, data: list[list[Any]]):
        if self._model:
            self._model.update_data(data)
