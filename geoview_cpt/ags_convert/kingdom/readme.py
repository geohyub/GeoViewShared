"""
Kingdom README generator — Phase A-4 Week 18 A4.6.

Renders the operator-facing ``README.md`` that ships inside every
``09_kingdom/`` drop. The Q43 checklist from
``docs/kingdom_folder_layout.md`` pins six mandatory sections:

    1. Project ID
    2. Generation timestamp
    3. Source AGS4 version
    4. CPT sounding count + checkshot count
    5. Kingdom CRS
    6. Troubleshooting — python-ags4 Gap #1 TRAN_DLIM caveat

Language policy (KFW delivery): Korean first, English parallel
translation in italics so external reviewers can read the same
file. The generator treats the two languages as a tuple per section
to keep edits symmetric.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.kingdom.assembly import KingdomPackage
    from geoview_cpt.ags_convert.writer import ProjectMeta

__all__ = [
    "build_readme",
    "write_readme",
]


AGS_VERSION = "4.1"
KINGDOM_SUBSET_VERSION = "A4.0"


def build_readme(
    package: "KingdomPackage",
    *,
    project_meta: "ProjectMeta | None" = None,
    generated_at: datetime | None = None,
) -> str:
    """Return the README.md body as a string (UTF-8 safe)."""
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)
    project_id = package.project_id or "UNKNOWN"
    crs = package.crs or "(unspecified)"
    client = project_meta.client if project_meta else ""
    contractor = project_meta.contractor if project_meta else ""

    # Build the per-sounding table rows
    rows: list[str] = []
    for sid in package.sounding_ids:
        cs = package.checkshot_files.get(sid)
        cs_mark = "✅" if cs is not None else "⏭"
        rows.append(f"| {sid} | ✅ | ✅ | {cs_mark} |")

    lines: list[str] = []
    push = lines.append

    push(f"# Kingdom Drop — {project_id}")
    push("")
    push(f"_Kingdom 납품 패키지 / Kingdom delivery package_")
    push("")
    push("## 1. 프로젝트 개요 / Project overview")
    push("")
    push(f"- **프로젝트 ID / Project ID:** `{project_id}`")
    push(f"- **생성 시각 / Generated at:** `{generated_at.strftime('%Y-%m-%dT%H:%M:%SZ')}` (UTC)")
    push(f"- **AGS4 버전 / AGS4 version:** `{AGS_VERSION}`")
    push(f"- **Kingdom subset 규약 / Kingdom subset spec:** `{KINGDOM_SUBSET_VERSION}`")
    push(f"- **좌표계 / CRS:** `{crs}`")
    if client:
        push(f"- **발주처 / Client:** {client}")
    if contractor:
        push(f"- **작업사 / Contractor:** {contractor}")
    push("")
    push("## 2. 번들 통계 / Bundle statistics")
    push("")
    push(f"- CPT sounding 수 / CPT sounding count: **{package.sounding_count}**")
    push(f"- Checkshot 포함 수 / Checkshot count: **{package.checkshot_count}**")
    push(f"- Location CSV: `location/project_locations.csv`")
    push("")
    push("## 3. 폴더 구조 / Folder layout")
    push("")
    push("```")
    push("09_kingdom/")
    push("├── README.md                 # 본 파일 / this file")
    push("├── manifest.yaml             # SHA-256 체크섬 포함 / SHA-256 checksums")
    push("├── AGS/                      # per-sounding AGS4 (.ags)")
    push("├── LAS/                      # per-sounding LAS 2.0 (.las)")
    push("├── checkshot/                # per-sounding 검쇄 CSV (optional)")
    push("└── location/")
    push("    └── project_locations.csv # 모든 지점 통합 / combined index")
    push("```")
    push("")
    push("## 4. 지점별 파일 목록 / Per-sounding file inventory")
    push("")
    push("| Sounding | AGS | LAS | Checkshot |")
    push("|----------|-----|-----|-----------|")
    for row in rows:
        push(row)
    push("")
    push(
        "_Checkshot ⏭ 표시는 해당 sounding 에 seismic first-break pick 이 "
        "없어 Kingdom CSV 를 생성하지 않은 경우입니다. manifest.yaml 의 "
        "`reason: no_seismic_picks` 항목을 참조하세요._"
    )
    push(
        "_A checkshot marked ⏭ means the sounding has no seismic "
        "first-break picks. See `reason: no_seismic_picks` in "
        "`manifest.yaml`._"
    )
    push("")
    push("## 5. Kingdom 임포트 안내 / Importing into Kingdom")
    push("")
    push(
        "1. Kingdom 에서 프로젝트를 열고 `File → Import → AGS4` 를 선택하세요. "
        "`AGS/` 폴더 내 파일을 개별 임포트하거나 일괄 임포트할 수 있습니다."
    )
    push(
        "   _In Kingdom, open `File → Import → AGS4` and import the files "
        "under `AGS/` individually or as a batch._"
    )
    push(
        "2. 웰 로그 뷰어에서 LAS 파일을 오버레이하려면 `LAS/` 폴더를 동일 프로젝트에 "
        "연결하세요."
    )
    push(
        "   _To overlay well-log curves, wire the `LAS/` folder into the "
        "same project via the Well Log viewer._"
    )
    push(
        "3. 검쇄 분석은 `checkshot/` CSV 를 Velocity Profile 으로 로드합니다. "
        "`# CRS:` 주석 줄은 Kingdom 이 무시합니다."
    )
    push(
        "   _Load each `checkshot/*.csv` as a Velocity Profile. Kingdom "
        "ignores the leading `# CRS:` comment line._"
    )
    push(
        "4. 서베이 그리드를 확인하려면 `location/project_locations.csv` 를 "
        "GeoView Base Map 에 드래그하세요."
    )
    push(
        "   _To plot the survey grid, drag "
        "`location/project_locations.csv` onto the GeoView base map._"
    )
    push("")
    push("## 6. 트러블슈팅 / Troubleshooting")
    push("")
    push(
        "**python-ags4 Gap #1 — TRAN_DLIM 비대칭.** "
        "`.ags` 파일을 한 번 다시 저장하면 `TRAN_DLIM` 셀의 이스케이프된 "
        "큰따옴표가 빈 문자열로 바뀌는 python-ags4 v1.0.0 의 알려진 버그가 "
        "있습니다. 본 번들은 쓰기 시점에 two-pass idempotency 를 통해 "
        "이미 안정화된 상태로 제공됩니다. 의심스러운 경우 `manifest.yaml` 의 "
        "SHA-256 과 대조하여 수정 여부를 확인하세요."
    )
    push("")
    push(
        "**Gap #1 — TRAN_DLIM asymmetry.** python-ags4 v1.0.0 strips "
        "the escaped double-quote in the `TRAN_DLIM` cell on a single "
        "round-trip. This bundle was written with the two-pass "
        "idempotency pattern and is stable as shipped. Verify "
        "integrity by comparing against the SHA-256 hashes in "
        "`manifest.yaml` if in doubt."
    )
    push("")
    push(
        "**SHA-256 검증 / SHA-256 verification.** `manifest.yaml` 의 "
        "`checksums` 맵에 각 파일의 해시가 있습니다. 아래 예시를 참고하세요:"
    )
    push("")
    push("```bash")
    push("python -c \"import hashlib, sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())\" AGS/<file>.ags")
    push("```")
    push("")
    push("---")
    push("")
    push(
        f"_Generated by `geoview_cpt.ags_convert.kingdom` (Phase A-4 {KINGDOM_SUBSET_VERSION}). "
        "R6 policy: standard AGS4 GROUPs only — HoleBASE SI / gINT V8i "
        "compatibility is deferred to v1.1._"
    )
    return "\n".join(lines) + "\n"


def write_readme(
    package: "KingdomPackage",
    path: Path | str | None = None,
    *,
    project_meta: "ProjectMeta | None" = None,
    generated_at: datetime | None = None,
) -> Path:
    """
    Write ``README.md`` to disk. When ``path`` is ``None`` the file
    lands at ``<staging_dir>/README.md``. Stamps
    ``package.readme_path`` so the manifest picks it up on the next
    :func:`build_manifest` call.
    """
    target = Path(path) if path is not None else package.staging_dir / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = build_readme(package, project_meta=project_meta, generated_at=generated_at)
    target.write_text(body, encoding="utf-8")
    package.readme_path = target
    return target
