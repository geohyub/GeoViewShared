"""
CPT Suite Autosave — 5분 간격 자동 저장 + 크래시 복구.

참조: plans/wave6_b1_cptprep_plan.md §5.7 이월
      plans/wave8_b3_cptproc_plan.md §7.7 복구

동작:
    - QTimer 5분 간격 → 프로젝트 상태를 .autosave 파일에 저장
    - 앱 시작 시 .autosave 존재 여부 확인 → 복구 제안
    - 정상 종료 시 .autosave 삭제
    - 크래시 시 .autosave 잔존 → 다음 시작 시 복구 경로 제시

Undo 20단계:
    - UndoStack: 최근 20개 상태 보존
    - Ctrl+Z / Ctrl+Shift+Z 로 탐색
"""

from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QTimer


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AutosaveRecord:
    """Autosave 파일에 저장할 상태."""

    app_name: str
    version: str
    timestamp_utc: str
    state: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> "AutosaveRecord":
        data = json.loads(text)
        return cls(**data)


class AutosaveManager:
    """5분 간격 autosave + 크래시 복구."""

    INTERVAL_MS = 5 * 60 * 1000  # 5분

    def __init__(
        self,
        app_name: str,
        version: str,
        save_dir: Path | None = None,
        state_getter: Callable[[], dict[str, Any]] | None = None,
        state_restorer: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._app_name = app_name
        self._version = version
        self._save_dir = save_dir
        self._state_getter = state_getter
        self._state_restorer = state_restorer
        self._timer = QTimer()
        self._timer.setInterval(self.INTERVAL_MS)
        self._timer.timeout.connect(self._do_autosave)
        self._active = False

    @property
    def autosave_path(self) -> Path | None:
        if self._save_dir is None:
            return None
        return self._save_dir / f".{self._app_name.lower()}_autosave.json"

    @property
    def is_active(self) -> bool:
        return self._active

    def start(self, save_dir: Path | None = None) -> None:
        """Autosave 시작. save_dir 지정 시 갱신."""
        if save_dir is not None:
            self._save_dir = save_dir
        if self._save_dir is not None:
            self._active = True
            self._timer.start()

    def stop(self) -> None:
        """Autosave 중지."""
        self._timer.stop()
        self._active = False

    def cleanup(self) -> None:
        """정상 종료 시 autosave 파일 삭제."""
        path = self.autosave_path
        if path is not None and path.exists():
            path.unlink(missing_ok=True)

    def has_recovery(self) -> bool:
        """크래시 복구 가능 여부."""
        path = self.autosave_path
        return path is not None and path.exists()

    def recover(self) -> AutosaveRecord | None:
        """Autosave 파일에서 상태 복구. 성공 시 restorer 호출."""
        path = self.autosave_path
        if path is None or not path.exists():
            return None
        try:
            record = AutosaveRecord.from_json(path.read_text(encoding="utf-8"))
            if self._state_restorer is not None:
                self._state_restorer(record.state)
            return record
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def _do_autosave(self) -> None:
        if self._state_getter is None or self._save_dir is None:
            return
        path = self.autosave_path
        if path is None:
            return
        try:
            state = self._state_getter()
            record = AutosaveRecord(
                app_name=self._app_name,
                version=self._version,
                timestamp_utc=_utc_now(),
                state=state,
            )
            self._save_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(record.to_json(), encoding="utf-8")
        except Exception:
            pass  # autosave 실패 시 앱 중단 금지


# ---------------------------------------------------------------------------
# UndoStack — 최근 20 상태
# ---------------------------------------------------------------------------

_UNDO_MAX = 20


class UndoStack:
    """파라미터 변경 Undo/Redo (최대 20 단계)."""

    def __init__(self, max_depth: int = _UNDO_MAX) -> None:
        self._max = max_depth
        self._stack: deque[dict[str, Any]] = deque(maxlen=max_depth)
        self._redo_stack: list[dict[str, Any]] = []
        self._current: dict[str, Any] = {}

    @property
    def can_undo(self) -> bool:
        return len(self._stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def depth(self) -> int:
        return len(self._stack)

    def push(self, state: dict[str, Any]) -> None:
        """현재 상태를 스택에 push, 새 상태를 current 로."""
        if self._current:
            self._stack.append(dict(self._current))
        self._current = dict(state)
        self._redo_stack.clear()

    def undo(self) -> dict[str, Any] | None:
        """이전 상태로 복원. 반환: 복원된 상태 (없으면 None)."""
        if not self._stack:
            return None
        self._redo_stack.append(dict(self._current))
        self._current = self._stack.pop()
        return dict(self._current)

    def redo(self) -> dict[str, Any] | None:
        """Redo. 반환: 복원된 상태."""
        if not self._redo_stack:
            return None
        self._stack.append(dict(self._current))
        self._current = self._redo_stack.pop()
        return dict(self._current)

    @property
    def current(self) -> dict[str, Any]:
        return dict(self._current)


__all__ = [
    "AutosaveManager",
    "AutosaveRecord",
    "UndoStack",
]
