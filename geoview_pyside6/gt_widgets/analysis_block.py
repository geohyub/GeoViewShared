"""
N4 AnalysisBlock — atomic 분석 단위 (Wave 6 Week 20 Day 2 scaffold)

참조: plans/new_widgets_spec.md §3
목적: input params + chart + status + trace 를 한 블록에 묶어 재현성 확보.
Day 3 정오 fallback 체크포인트 4 기준 중 기준 1 (stale/fresh 전환) 대비.

Depends on (read-only, Day 2 tip):
    (none — pure PySide6, 본 Day 2 scaffold 는 WIP 파일 import 0 개)
    effects.py / animated_stack.py 와 공개 API 결합은 Day 4+ 로 연기
WIP owner 영향 범위: 없음. Day 2 scaffold 는 _shared/ pre-existing WIP 8 파일에
    대해 독립적이다. M5 §5.8 감사성 축 "재현성" 요건 충족.

4 상태 머신:
    fresh     : 파라미터 up-to-date, 결과 유효
    stale     : 파라미터 변경됨, [Rerun ⟳] 필요
    running   : 실행 중 (비동기 작업 placeholder)
    error     : 마지막 실행 실패

Trace 영속 경로:
    <project_root>/.gt_trace/<block_id>/<timestamp>.json
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    import pyqtgraph as _pg

    _PYQTGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover — optional dependency
    _pg = None  # type: ignore[assignment]
    _PYQTGRAPH_AVAILABLE = False


BlockStatus = Literal["fresh", "stale", "running", "error"]

_STATUS_STRIPE: dict[BlockStatus, str] = {
    "fresh": "#4ADE80",
    "stale": "#FBBF24",
    "running": "#60A5FA",
    "error": "#F87171",
}

_VALID_STATUSES: frozenset[BlockStatus] = frozenset(
    ("fresh", "stale", "running", "error")
)


# ---------------------------------------------------------------------------
# TraceRecord — 재현성의 근본 단위
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TraceRecord:
    """파라미터 + 입력 + 출력 + 메타의 영속 레코드.

    M5 §5.8 감사성 요건:
    - timestamp_utc 는 반드시 UTC ISO 8601 (로컬 타임 금지)
    - params_hash + input_sounding_hash 로 동일 입력 재실행 시 동일 hash 검증
    """

    block_id: str
    method: str
    params_hash: str
    params: dict[str, Any]
    input_sounding_hash: str
    output_summary: dict[str, Any]
    timestamp_utc: str
    runtime_ms: int
    user: str = "unknown"
    app_version: str = "0.1.0-dev"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> "TraceRecord":
        data = json.loads(text)
        return cls(**data)


def compute_params_hash(params: dict[str, Any]) -> str:
    canonical = json.dumps(params, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_SAFE_BLOCK_ID_RE = re.compile(r"[^A-Za-z0-9_\-]")


def _safe_block_dir_name(block_id: str) -> str:
    if not block_id:
        raise ValueError("block_id must be non-empty")
    return _SAFE_BLOCK_ID_RE.sub("_", block_id)


def trace_directory(project_root: Path, block_id: str) -> Path:
    return Path(project_root) / ".gt_trace" / _safe_block_dir_name(block_id)


def write_trace(project_root: Path, record: TraceRecord) -> Path:
    directory = trace_directory(project_root, record.block_id)
    directory.mkdir(parents=True, exist_ok=True)
    safe_ts = record.timestamp_utc.replace(":", "-")
    path = directory / f"{safe_ts}.json"
    path.write_text(record.to_json(), encoding="utf-8")
    return path


def read_traces(project_root: Path, block_id: str) -> list[TraceRecord]:
    directory = trace_directory(project_root, block_id)
    if not directory.exists():
        return []
    records: list[TraceRecord] = []
    for path in sorted(directory.glob("*.json")):
        try:
            records.append(TraceRecord.from_json(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, TypeError, KeyError):
            # §5.7 graceful degrade — 손상된 trace 는 무시, 앱 중단 금지
            continue
    return records


# ---------------------------------------------------------------------------
# AnalysisBlock — QFrame 기반 atomic 분석 블록
# ---------------------------------------------------------------------------


class AnalysisBlock(QFrame):
    """Params + Chart placeholder + Status stripe + Footer toolbar."""

    sig_params_changed = Signal(dict)
    sig_rerun_requested = Signal()
    sig_status_changed = Signal(str)

    def __init__(
        self,
        block_id: str,
        method: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not block_id:
            raise ValueError("block_id must be non-empty")
        self._block_id = block_id
        self._method = method
        self._params: dict[str, Any] = {}
        self._status: BlockStatus = "fresh"
        self._last_runtime_ms: int = 0
        self._last_output: dict[str, Any] = {}
        self._build_ui()

    # ---- UI 구성 ----------------------------------------------------------

    def _build_ui(self) -> None:
        self.setObjectName("Surface")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Status stripe (left 4 px)
        self._stripe = QFrame(self)
        self._stripe.setFixedHeight(4)
        self._stripe.setStyleSheet(f"background: {_STATUS_STRIPE['fresh']};")
        root.addWidget(self._stripe)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        self._title_label = QLabel(f"{self._method}")
        self._title_label.setStyleSheet("font-weight: 600;")
        self._status_label = QLabel("fresh")
        self._status_label.setProperty("role", "secondary")
        self._runtime_label = QLabel("—")
        self._runtime_label.setProperty("role", "secondary")
        header.addWidget(self._title_label)
        header.addStretch(1)
        header.addWidget(self._status_label)
        header.addWidget(self._runtime_label)
        root.addLayout(header)

        # Chart — pyqtgraph PlotWidget (Week 22 Day 4 embed) with QLabel fallback
        self._chart_widget: QWidget
        if _PYQTGRAPH_AVAILABLE:
            assert _pg is not None
            plot = _pg.PlotWidget()
            plot.setMinimumHeight(120)
            plot.setBackground(None)  # transparent — parent theme 에 위임
            plot.showGrid(x=True, y=True, alpha=0.2)
            self._chart_widget = plot
            self._chart_plot = plot
        else:
            fallback = QLabel(
                f"[chart placeholder · {self._method}]",
                alignment=Qt.AlignmentFlag.AlignCenter,
            )
            fallback.setMinimumHeight(120)
            fallback.setProperty("role", "secondary")
            self._chart_widget = fallback
            self._chart_plot = None
        self._chart_placeholder = self._chart_widget  # 호환성 유지 (Day 2 명)
        root.addWidget(self._chart_widget, 1)

        # Footer
        footer = QHBoxLayout()
        footer.setContentsMargins(12, 8, 12, 8)
        self._rerun_button = QPushButton("Rerun ⟳")
        self._rerun_button.clicked.connect(self._on_rerun_clicked)
        self._trace_button = QPushButton("Trace ▸")
        self._trace_button.setEnabled(False)  # Day 2: 미구현 스텁
        footer.addStretch(1)
        footer.addWidget(self._rerun_button)
        footer.addWidget(self._trace_button)
        root.addLayout(footer)

    # ---- Public API -------------------------------------------------------

    @property
    def block_id(self) -> str:
        return self._block_id

    @property
    def method(self) -> str:
        return self._method

    @property
    def status(self) -> BlockStatus:
        return self._status

    @property
    def params(self) -> dict[str, Any]:
        return dict(self._params)

    def set_params(self, params: dict[str, Any]) -> None:
        """파라미터 업데이트. 이전과 다르면 stale 전환."""
        if params == self._params:
            return
        self._params = dict(params)
        self.sig_params_changed.emit(dict(self._params))
        if self._status == "fresh":
            self.set_status("stale")

    def set_status(self, status: BlockStatus) -> None:
        if status not in _VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")
        if status == self._status:
            return
        self._status = status
        self._status_label.setText(status)
        self._stripe.setStyleSheet(f"background: {_STATUS_STRIPE[status]};")
        self.sig_status_changed.emit(status)

    def set_result(
        self,
        output_summary: dict[str, Any],
        runtime_ms: int,
    ) -> None:
        """실행 성공 결과 반영. fresh 로 전환."""
        self._last_output = dict(output_summary)
        self._last_runtime_ms = int(runtime_ms)
        self._runtime_label.setText(f"{runtime_ms} ms")
        self.set_status("fresh")

    def set_error(self, message: str) -> None:
        self._runtime_label.setText("error")
        if hasattr(self._chart_widget, "setText"):
            self._chart_widget.setText(f"[error] {message}")  # QLabel fallback 경로
        elif self._chart_plot is not None:
            self._chart_plot.clear()
            self._chart_plot.setTitle(f"error: {message}")
        self.set_status("error")

    # Day 4 B1.8: chart 에 실제 데이터 그리기 (pyqtgraph 가용 시)
    def plot_series(
        self,
        depth: list[float],
        values: list[float],
        *,
        label: str = "",
    ) -> bool:
        """depth vs value 시리즈를 chart 에 그린다. pyqtgraph 없으면 False."""
        if self._chart_plot is None:
            return False
        self._chart_plot.clear()
        self._chart_plot.plot(depth, values, pen=_pg.mkPen(width=1.5))
        if label:
            self._chart_plot.setTitle(label)
        return True

    @property
    def chart_is_pyqtgraph(self) -> bool:
        return self._chart_plot is not None

    def make_trace_record(
        self,
        input_sounding_hash: str,
        user: str = "unknown",
        app_version: str = "0.1.0-dev",
    ) -> TraceRecord:
        return TraceRecord(
            block_id=self._block_id,
            method=self._method,
            params_hash=compute_params_hash(self._params),
            params=dict(self._params),
            input_sounding_hash=input_sounding_hash,
            output_summary=dict(self._last_output),
            timestamp_utc=utc_now_iso(),
            runtime_ms=self._last_runtime_ms,
            user=user,
            app_version=app_version,
        )

    # ---- private ----------------------------------------------------------

    def _on_rerun_clicked(self) -> None:
        self.set_status("running")
        self.sig_rerun_requested.emit()


__all__ = [
    "AnalysisBlock",
    "BlockStatus",
    "TraceRecord",
    "compute_params_hash",
    "utc_now_iso",
    "trace_directory",
    "write_trace",
    "read_traces",
]
