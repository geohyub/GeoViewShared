"""GeoView 자동 스크린샷 모드.

GEOVIEW_SCREENSHOT_DIR + GEOVIEW_SCREENSHOT_APP 환경변수가 있으면 활성화.
QT_QPA_PLATFORM=offscreen 환경에서 호출되어 화면 점유 없이 모든
panel·tab을 grab으로 캡처한 뒤 QApplication.quit().

활용:
- _shared/geoview_pyside6/app_base.py GeoViewApp.__init__ 끝에서 호출
- capture_harness가 환경변수 + offscreen platform으로 subprocess 실행
"""
from __future__ import annotations

import os
import re
import sys
import traceback
from pathlib import Path

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QTabWidget, QStackedWidget, QWidget,
    )
except Exception:  # pragma: no cover
    QTimer = None
    QApplication = None
    QMainWindow = None
    QTabWidget = None
    QStackedWidget = None
    QWidget = None


def _safe(text: str, max_len: int = 28) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    text = re.sub(r"[^\w\-가-힣]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len]


def _save_grab(widget, path: Path) -> bool:
    try:
        pix = widget.grab()
        ok = pix.save(str(path), "PNG")
        return bool(ok)
    except Exception:
        return False


def _wait_paint(ms: int = 350):
    """이벤트 루프 비우고 잠깐 대기 — repaint 보장."""
    if QApplication is None:
        return
    app = QApplication.instance()
    if app is None:
        return
    app.processEvents()
    # offscreen에서도 sleep로 충분 (paint pending 처리)
    import time
    time.sleep(ms / 1000.0)
    app.processEvents()


def _capture_panel_tabs(window, panel: QWidget, name_prefix: str,
                        out_dir: Path, captured: list[str]):
    """panel 안의 QTabWidget·QStackedWidget 순회 캡처."""
    # QTabWidget 순회
    for ti, tw in enumerate(panel.findChildren(QTabWidget)):
        try:
            for i in range(tw.count()):
                try:
                    tw.setCurrentIndex(i)
                    _wait_paint()
                    title = tw.tabText(i) or f"tab{i+1}"
                    safe_t = _safe(title) or f"tab{i+1}"
                    p = out_dir / f"{name_prefix}_T{ti+1:02d}_{i+1:02d}_{safe_t}.png"
                    if _save_grab(window, p):
                        captured.append(p.name)
                except Exception as e:
                    print(f"[shot] tab err: {e}", file=sys.stderr)
        except Exception:
            continue


def _do_capture(window):
    out_dir = Path(os.environ["GEOVIEW_SCREENSHOT_DIR"])
    app_name = os.environ.get("GEOVIEW_SCREENSHOT_APP", "app")
    out_dir.mkdir(parents=True, exist_ok=True)

    captured: list[str] = []
    try:
        # 0) 베이스라인 (현재 활성 panel 상태)
        baseline = out_dir / f"{app_name}_00_main.png"
        if _save_grab(window, baseline):
            captured.append(baseline.name)

        # 1) 메인창 직접 자식 QTabWidget (sidebar 없는 앱 대응)
        _capture_panel_tabs(window, window, f"{app_name}_M", out_dir, captured)

        # 2) GeoViewApp의 패널 순회 — _panel_order + _panels 사용
        panel_order = getattr(window, "_panel_order", None)
        panels = getattr(window, "_panels", None)
        switch = getattr(window, "_switch_panel", None)
        if panel_order and panels and callable(switch):
            for si, panel_name in enumerate(panel_order):
                try:
                    switch(panel_name)
                    _wait_paint(450)
                    safe_p = _safe(panel_name) or f"panel{si+1}"
                    p = out_dir / f"{app_name}_S{si+1:02d}_{safe_p}.png"
                    if _save_grab(window, p):
                        captured.append(p.name)
                    # 패널 안의 탭 순회
                    panel_widget = panels.get(panel_name)
                    if panel_widget is not None:
                        prefix = f"{app_name}_S{si+1:02d}_{safe_p}"
                        _capture_panel_tabs(window, panel_widget, prefix, out_dir, captured)
                except Exception as e:
                    print(f"[shot] panel '{panel_name}' err: {e}", file=sys.stderr)

        print(f"[shot] {app_name}: {len(captured)} captured to {out_dir}")
    except Exception:
        print(f"[shot] fatal:\n{traceback.format_exc()}", file=sys.stderr)
    finally:
        try:
            QApplication.quit()
        except Exception:
            os._exit(0)


def _register_korean_fallback():
    """offscreen에서 한글 폰트 fallback 강제. 3단계:
    1. 시스템 malgun.ttf를 ApplicationFont로 등록 (Qt가 인식 보장)
    2. QFont substitution: 영문 폰트 → 한글 폰트 fallback
    3. QApplication.setFont로 default font 변경 (QSS 미명시 위젯)
    """
    families_loaded = []
    try:
        from PySide6.QtGui import QFontDatabase, QFont
        from PySide6.QtWidgets import QApplication

        # 1) 시스템 한글 폰트 직접 등록
        font_paths = [
            r"C:\Windows\Fonts\malgun.ttf",
            r"C:\Windows\Fonts\malgunbd.ttf",
            r"C:\Windows\Fonts\malgunsl.ttf",
            r"C:\Windows\Fonts\gulim.ttc",
            r"C:\Windows\Fonts\batang.ttc",
        ]
        for p in font_paths:
            if not os.path.exists(p):
                continue
            fid = QFontDatabase.addApplicationFont(p)
            if fid >= 0:
                fams = QFontDatabase.applicationFontFamilies(fid)
                families_loaded.extend(fams)
        if families_loaded:
            print(f"[shot] loaded korean fonts: {families_loaded[:3]}", file=sys.stderr)

        # 2) substitution: Pretendard 등 → Malgun Gothic fallback
        primary_families = [
            "Pretendard", "Wanted Sans Std", "WantedSansStd",
            "Inter", "Segoe UI", "Arial", "Helvetica", "sans-serif",
        ]
        for primary in primary_families:
            QFont.insertSubstitutions(primary, ["Malgun Gothic", "맑은 고딕", "Gulim"])

        # 3) application font 강제 (QSS 미명시 위젯에 한글 가능)
        app = QApplication.instance()
        if app is not None:
            app.setFont(QFont("Malgun Gothic", 10))
    except Exception as e:
        print(f"[shot] font setup err: {e}", file=sys.stderr)


def maybe_screenshot_mode(window) -> bool:
    """환경변수 활성 시 2.5초 후 자동 캡처. 비활성이면 no-op.

    호출 위치: GeoViewApp.__init__ 끝 (또는 main의 window.show() 직후).
    """
    if QTimer is None:
        return False
    if not os.environ.get("GEOVIEW_SCREENSHOT_DIR"):
        return False
    _register_korean_fallback()
    # 폰트 substitution 후 위젯 다시 그리기 강제
    try:
        window.update()
        for child in window.findChildren(QWidget):
            child.update()
    except Exception:
        pass
    QTimer.singleShot(2500, lambda: _do_capture(window))
    return True
