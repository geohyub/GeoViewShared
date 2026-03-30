"""
GeoView Project Context — Data Models
=======================================
프로젝트 컨텍스트 데이터 모델.
JSON 직렬화/역직렬화, 경로 유효성 검증 포함.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ProjectPaths:
    """프로젝트 관련 디렉토리 경로."""

    raw_data: str = ""
    processed_data: str = ""
    qc_output: str = ""
    reports: str = ""
    delivery: str = ""
    nas_primary: str = ""
    nas_backup: str = ""

    def validate(self) -> list[str]:
        """존재하지 않는 경로 목록 반환 (빈 문자열은 무시)."""
        warnings: list[str] = []
        for name in (
            "raw_data", "processed_data", "qc_output",
            "reports", "delivery", "nas_primary", "nas_backup",
        ):
            value = getattr(self, name)
            if value and not Path(value).exists():
                warnings.append(f"{name}: {value}")
        return warnings

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ProjectPaths:
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ProjectContext:
    """
    GeoView 프로젝트 컨텍스트.

    모든 앱이 공유하는 프로젝트 설정 데이터.
    metadata dict로 앱별 확장 필드를 허용.
    """

    # --- 식별 ---
    project_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    project_name: str = ""
    project_code: str = ""

    # --- 프로젝트 정보 ---
    client: str = ""
    vessel: str = ""
    survey_area: str = ""

    # --- 좌표/시간 ---
    crs_epsg: int = 0
    crs_name: str = ""
    timezone_offset: float = 9.0  # KST default

    # --- 경로 ---
    paths: ProjectPaths = field(default_factory=ProjectPaths)

    # --- 연동 ---
    vessel_config_id: Optional[int] = None  # OffsetManager config ID
    line_prefix: str = ""

    # --- 메타 ---
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    # --- 직렬화 ---

    def to_dict(self) -> dict:
        """JSON-호환 dict 반환."""
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> ProjectContext:
        """dict에서 ProjectContext 생성. 알 수 없는 키는 무시."""
        d = dict(data)

        # paths는 nested 처리
        paths_raw = d.pop("paths", {})
        if isinstance(paths_raw, dict):
            paths = ProjectPaths.from_dict(paths_raw)
        else:
            paths = ProjectPaths()

        # 알려진 필드만 추출
        known = {f.name for f in cls.__dataclass_fields__.values()} - {"paths"}
        kwargs = {k: v for k, v in d.items() if k in known}
        kwargs["paths"] = paths

        return cls(**kwargs)

    @classmethod
    def from_json(cls, text: str) -> ProjectContext:
        return cls.from_dict(json.loads(text))

    @classmethod
    def from_file(cls, path: str | Path) -> ProjectContext:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Project context file not found: {p}")
        return cls.from_json(p.read_text(encoding="utf-8"))

    def save_to_file(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json(), encoding="utf-8")

    def touch_updated(self) -> None:
        """updated_at 타임스탬프 갱신."""
        self.updated_at = datetime.now().isoformat(timespec="seconds")

    def validate_paths(self) -> list[str]:
        """경로 유효성 경고 목록."""
        return self.paths.validate()

    def display_name(self) -> str:
        """UI 표시용 이름."""
        if self.project_code and self.project_name:
            return f"[{self.project_code}] {self.project_name}"
        return self.project_name or self.project_code or "(Unnamed Project)"
