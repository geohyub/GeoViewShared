"""
GeoView Project Context — Signals
====================================
파일 기반 변경 감지 (QFileSystemWatcher).
앱 A가 active_project.json을 변경하면 앱 B/C가 자동 감지.

Qt 없이도 import 가능하도록 PySide6는 지연 임포트.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from geoview_common.project_context.models import ProjectContext

logger = logging.getLogger(__name__)

# 기본 감시 파일
_DEFAULT_ACTIVE_FILE = Path("E:/Software/.geoview/active_project.json")


def _try_import_qt():
    """PySide6 지연 임포트. 없으면 None."""
    try:
        from PySide6.QtCore import QObject, Signal, QFileSystemWatcher, QTimer
        return QObject, Signal, QFileSystemWatcher, QTimer
    except ImportError:
        return None


def create_watcher(
    active_file: str | Path | None = None,
    store=None,
):
    """
    ProjectContextWatcher 인스턴스 생성.

    PySide6 미설치 시 None 반환 (CLI 환경).

    Parameters
    ----------
    active_file : 감시할 active_project.json 경로
    store : ProjectContextStore 인스턴스 (옵션)
    """
    qt = _try_import_qt()
    if qt is None:
        logger.debug("PySide6 미설치 — ProjectContextWatcher 비활성")
        return None

    QObject, Signal, QFileSystemWatcher, QTimer = qt

    class ProjectContextWatcher(QObject):
        """
        active_project.json 변경 감지 → context_changed 시그널 발행.

        QFileSystemWatcher를 사용하며, 일부 OS에서 원자적 쓰기 시
        감시가 끊기는 문제를 보완하기 위해 debounce + re-watch 로직 포함.
        """

        context_changed = Signal(object)  # ProjectContext or None

        def __init__(self, active_file: str | Path | None = None, store=None, parent=None):
            super().__init__(parent)

            self._file = Path(active_file) if active_file else _DEFAULT_ACTIVE_FILE
            self._store = store
            self._last_active_id: Optional[str] = None

            self._watcher = QFileSystemWatcher(self)
            self._debounce = QTimer(self)
            self._debounce.setSingleShot(True)
            self._debounce.setInterval(200)  # 200ms debounce
            self._debounce.timeout.connect(self._on_debounced)

            self._watcher.fileChanged.connect(self._on_file_changed)

        def start(self) -> None:
            """감시 시작. 파일이 없으면 디렉토리 감시로 폴백."""
            self._add_watch()
            # 초기 상태 읽기
            self._last_active_id = self._read_active_id()

        def stop(self) -> None:
            """감시 중지."""
            paths = self._watcher.files()
            if paths:
                self._watcher.removePaths(paths)
            dirs = self._watcher.directories()
            if dirs:
                self._watcher.removePaths(dirs)

        def _add_watch(self) -> None:
            """감시 대상 (재)등록."""
            if self._file.exists():
                self._watcher.addPath(str(self._file))
            else:
                # 파일이 아직 없으면 부모 디렉토리 감시
                parent = self._file.parent
                if parent.exists():
                    self._watcher.addPath(str(parent))

        def _on_file_changed(self, path: str) -> None:
            """파일 변경 감지 — debounce 시작."""
            self._debounce.start()
            # 원자적 쓰기 후 감시가 끊길 수 있으므로 재등록
            self._add_watch()

        def _on_debounced(self) -> None:
            """debounce 후 실제 처리."""
            new_id = self._read_active_id()
            if new_id == self._last_active_id:
                return  # 변경 없음

            self._last_active_id = new_id
            ctx = self._load_context(new_id)
            self.context_changed.emit(ctx)

        def _read_active_id(self) -> Optional[str]:
            if not self._file.exists():
                return None
            try:
                data = json.loads(self._file.read_text(encoding="utf-8"))
                return data.get("active_id")
            except (json.JSONDecodeError, OSError):
                return None

        def _load_context(self, project_id: Optional[str]):
            """ProjectContext 로드. store 있으면 store 사용, 없으면 직접."""
            if project_id is None:
                return None
            if self._store:
                return self._store.load(project_id)
            # store 없이 직접 로드 시도
            from geoview_common.project_context.models import ProjectContext
            f = self._file.parent / "projects" / f"{project_id}.json"
            if f.exists():
                try:
                    return ProjectContext.from_file(f)
                except Exception:
                    return None
            return None

        def force_refresh(self) -> None:
            """강제로 현재 상태 읽고 시그널 발행."""
            new_id = self._read_active_id()
            self._last_active_id = new_id
            ctx = self._load_context(new_id)
            self.context_changed.emit(ctx)

    return ProjectContextWatcher(active_file=active_file, store=store)
