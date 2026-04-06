"""
GeoView PySide6 — Worker Thread Utilities
===========================================
QThread + QObject Worker 보일러플레이트를 최소화하는 유틸리티.
"""

from PySide6.QtCore import QObject, QThread, Signal


class BaseWorker(QObject):
    """
    서브클래스에서 run()을 오버라이드하여 사용.

    Signals:
        progress(int, str): 진행률 (0-100) + 선택적 메시지
        finished(object): 완료 시 결과 반환 (None 가능)
        error(str): 에러 발생 시 메시지
    """
    progress = Signal(int, str)
    finished = Signal(object)
    error = Signal(str)

    def run(self):
        """서브클래스에서 오버라이드. 장시간 작업 수행."""
        raise NotImplementedError

    def emit_progress(self, percent: int, message: str = ""):
        """진행률 emit 헬퍼."""
        self.progress.emit(min(100, max(0, percent)), message)

    def _safe_run(self):
        """내부 실행 래퍼. 예외를 error 시그널로 전환."""
        try:
            result = self.run()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


def run_worker(worker: BaseWorker,
               on_progress=None,
               on_finished=None,
               on_error=None,
               parent: QObject | None = None) -> QThread:
    """
    BaseWorker를 QThread에서 실행하는 헬퍼.

    Args:
        worker: BaseWorker 서브클래스 인스턴스
        on_progress: progress 시그널 핸들러 (optional)
        on_finished: finished 시그널 핸들러 (optional)
        on_error: error 시그널 핸들러 (optional)
        parent: QThread의 부모 (메모리 관리)

    Returns:
        실행 중인 QThread (필요시 중단/대기 가능)

    Usage::

        class MyWorker(BaseWorker):
            def run(self):
                for i in range(100):
                    self.emit_progress(i, f"Processing {i}...")
                    # ... work ...
                return {"count": 100}

        worker = MyWorker()
        thread = run_worker(worker, on_finished=self._on_done)
    """
    thread = QThread(parent)
    worker.moveToThread(thread)

    # Connect signals
    thread.started.connect(worker._safe_run)
    if on_progress:
        worker.progress.connect(on_progress)
    if on_finished:
        worker.finished.connect(on_finished)
    if on_error:
        worker.error.connect(on_error)

    # Cleanup: quit thread and schedule deletion
    worker.finished.connect(thread.quit)
    worker.error.connect(thread.quit)
    thread.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)

    thread.start()
    return thread
