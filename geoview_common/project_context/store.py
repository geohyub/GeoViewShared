"""
GeoView Project Context — Store
=================================
JSON 파일 기반 프로젝트 컨텍스트 저장소.
active_project.json + projects/ 디렉토리 구조.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from geoview_common.project_context.models import ProjectContext

logger = logging.getLogger(__name__)

# 기본 저장 경로: E:/Software/.geoview/
_DEFAULT_ROOT = Path("E:/Software/.geoview")


class ProjectContextStore:
    """
    프로젝트 컨텍스트 저장소.

    디렉토리 구조::

        {root}/
          active_project.json   <- 현재 활성 프로젝트 ID 참조
          projects/
            {project_id}.json   <- 프로젝트별 전체 데이터
            ...

    active_project.json 형식::

        {"active_id": "abc123def456"}
    """

    def __init__(self, root: str | Path | None = None):
        self._root = Path(root) if root else _DEFAULT_ROOT
        self._projects_dir = self._root / "projects"
        self._active_file = self._root / "active_project.json"
        self._ensure_dirs()

    @property
    def root(self) -> Path:
        return self._root

    @property
    def projects_dir(self) -> Path:
        return self._projects_dir

    @property
    def active_file(self) -> Path:
        return self._active_file

    # ── 디렉토리 관리 ──

    def _ensure_dirs(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        self._projects_dir.mkdir(parents=True, exist_ok=True)

    # ── 활성 프로젝트 ──

    def get_active_id(self) -> Optional[str]:
        """현재 활성 프로젝트 ID 반환. 없으면 None."""
        if not self._active_file.exists():
            return None
        try:
            data = json.loads(self._active_file.read_text(encoding="utf-8"))
            return data.get("active_id")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("active_project.json 읽기 실패: %s", e)
            return None

    def set_active_id(self, project_id: str) -> None:
        """활성 프로젝트 ID 설정."""
        self._active_file.write_text(
            json.dumps({"active_id": project_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear_active(self) -> None:
        """활성 프로젝트 해제."""
        if self._active_file.exists():
            self._active_file.write_text(
                json.dumps({"active_id": None}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def load_active(self) -> Optional[ProjectContext]:
        """현재 활성 프로젝트 로드. 없거나 파일 오류면 None."""
        active_id = self.get_active_id()
        if not active_id:
            return None
        return self.load(active_id)

    # ── 프로젝트 CRUD ──

    def _project_file(self, project_id: str) -> Path:
        return self._projects_dir / f"{project_id}.json"

    def load(self, project_id: str) -> Optional[ProjectContext]:
        """ID로 프로젝트 로드."""
        f = self._project_file(project_id)
        if not f.exists():
            logger.warning("프로젝트 파일 없음: %s", f)
            return None
        try:
            return ProjectContext.from_file(f)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("프로젝트 로드 실패 (%s): %s", project_id, e)
            return None

    def save(self, ctx: ProjectContext) -> None:
        """프로젝트 저장 (생성/갱신)."""
        ctx.touch_updated()
        ctx.save_to_file(self._project_file(ctx.project_id))

    def save_and_activate(self, ctx: ProjectContext) -> None:
        """저장 후 활성 프로젝트로 설정."""
        self.save(ctx)
        self.set_active_id(ctx.project_id)

    def delete(self, project_id: str) -> bool:
        """프로젝트 파일 삭제. 활성이면 해제."""
        f = self._project_file(project_id)
        if not f.exists():
            return False

        # 활성 해제
        if self.get_active_id() == project_id:
            self.clear_active()

        f.unlink()
        return True

    def exists(self, project_id: str) -> bool:
        return self._project_file(project_id).exists()

    # ── 목록 조회 ──

    def get_all(self) -> list[ProjectContext]:
        """전체 프로젝트 목록 (updated_at 내림차순)."""
        results: list[ProjectContext] = []
        for f in self._projects_dir.glob("*.json"):
            try:
                ctx = ProjectContext.from_file(f)
                results.append(ctx)
            except Exception as e:
                logger.warning("프로젝트 파싱 실패 (%s): %s", f.name, e)
        results.sort(key=lambda c: c.updated_at, reverse=True)
        return results

    def get_recent(self, count: int = 5) -> list[ProjectContext]:
        """최근 수정된 프로젝트 N개."""
        return self.get_all()[:count]

    def get_by_code(self, code: str) -> Optional[ProjectContext]:
        """project_code로 검색."""
        for ctx in self.get_all():
            if ctx.project_code == code:
                return ctx
        return None

    def search(self, query: str) -> list[ProjectContext]:
        """이름/코드/클라이언트/선박 검색."""
        q = query.lower()
        results: list[ProjectContext] = []
        for ctx in self.get_all():
            if any(q in getattr(ctx, attr, "").lower()
                   for attr in ("project_name", "project_code", "client", "vessel")):
                results.append(ctx)
        return results
