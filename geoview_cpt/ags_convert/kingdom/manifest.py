"""
Kingdom manifest generator — Phase A-4 Week 18 A4.5.

Builds the ``09_kingdom/manifest.yaml`` that travels with every drop
so the Kingdom operator (and downstream integrity checks) can audit
which files belong to the bundle, verify their SHA-256 hashes, and
record which soundings were skipped from the checkshot export.

Schema (v1.0)::

    schema_version: "1.0"
    project_id: JAKO-2025
    generated_at: 2025-11-14T12:34:56Z
    ags_version: "4.1"
    kingdom_subset_version: "A4.0"
    crs: EPSG:5179
    sounding_count: 13
    checkshot_count: 10
    soundings:
      - id: CPT01
        ags: AGS/JAKO-2025_CPT01.ags
        las: LAS/CPT01.las
        checkshot: checkshot/CPT01.csv   # or null + reason
        reason: null                      # 'no_seismic_picks' when checkshot is null
    files:
      location: location/project_locations.csv
      readme: README.md
    checksums:
      AGS/JAKO-2025_CPT01.ags: <sha256>
      ...
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from geoview_cpt.ags_convert.wrapper import AgsConvertError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.kingdom.assembly import KingdomPackage
    from geoview_cpt.ags_convert.writer import ProjectMeta

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "build_manifest",
    "write_manifest",
]


MANIFEST_SCHEMA_VERSION = "1.0"
AGS_VERSION = "4.1"
KINGDOM_SUBSET_VERSION = "A4.0"


def build_manifest(
    package: "KingdomPackage",
    *,
    project_meta: "ProjectMeta | None" = None,
    generated_at: datetime | None = None,
) -> dict:
    """
    Build the manifest dictionary for ``package``.

    Args:
        package:       Week 18 :class:`KingdomPackage` from A4.4.
        project_meta:  optional ProjectMeta for richer header fields.
        generated_at:  override for the timestamp — defaults to the
                       current UTC instant. Tests pin this to a fixed
                       datetime so the manifest bytes are stable.

    Returns:
        A YAML-dumpable dict with the schema described in the module
        docstring.
    """
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    # Sounding entries
    soundings: list[dict] = []
    for sounding_id, ags_path in zip(package.sounding_ids, package.ags_files):
        entry: dict = {
            "id": sounding_id,
            "ags": _relpath(ags_path, package.staging_dir),
        }
        # LAS: find the matching file by basename
        las_match = next(
            (p for p in package.las_files if p.stem == sounding_id), None
        )
        entry["las"] = (
            _relpath(las_match, package.staging_dir) if las_match else None
        )
        # Checkshot
        cs_path = package.checkshot_files.get(sounding_id)
        if cs_path is not None:
            entry["checkshot"] = _relpath(cs_path, package.staging_dir)
            entry["reason"] = None
        else:
            entry["checkshot"] = None
            entry["reason"] = "no_seismic_picks"
        soundings.append(entry)

    files_map: dict[str, str | None] = {}
    if package.location_csv is not None:
        files_map["location"] = _relpath(package.location_csv, package.staging_dir)
    if package.readme_path is not None:
        files_map["readme"] = _relpath(package.readme_path, package.staging_dir)

    checksums = _build_checksums(package)

    manifest: dict = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "project_id": package.project_id,
        "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ags_version": AGS_VERSION,
        "kingdom_subset_version": KINGDOM_SUBSET_VERSION,
        "crs": package.crs or "",
        "sounding_count": package.sounding_count,
        "checkshot_count": package.checkshot_count,
        "soundings": soundings,
        "files": files_map,
        "checksums": checksums,
    }
    if project_meta is not None:
        manifest["project_name"] = project_meta.project_name
        manifest["client"] = project_meta.client
        manifest["contractor"] = project_meta.contractor
    return manifest


def write_manifest(
    package: "KingdomPackage",
    path: Path | str | None = None,
    *,
    project_meta: "ProjectMeta | None" = None,
    generated_at: datetime | None = None,
) -> Path:
    """
    Build + write the manifest YAML.

    When ``path`` is ``None`` the manifest lands at
    ``<staging_dir>/manifest.yaml`` (the Week 16 folder-layout default)
    and the returned path is stamped into ``package.manifest_path``.
    """
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover
        raise AgsConvertError(
            "manifest writer requires pyyaml — install with "
            "`pip install geoview-common[ags]`"
        ) from exc

    target = Path(path) if path is not None else package.staging_dir / "manifest.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        package, project_meta=project_meta, generated_at=generated_at
    )
    target.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    package.manifest_path = target
    return target


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _relpath(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _build_checksums(package: "KingdomPackage") -> dict[str, str]:
    """Compute SHA-256 for every real file in the package."""
    checksums: dict[str, str] = {}
    candidates: list[Path] = []
    candidates.extend(package.ags_files)
    candidates.extend(package.las_files)
    candidates.extend(p for p in package.checkshot_files.values() if p is not None)
    if package.location_csv is not None:
        candidates.append(package.location_csv)
    if package.readme_path is not None:
        candidates.append(package.readme_path)

    for path in candidates:
        if not path.exists():
            continue
        key = _relpath(path, package.staging_dir)
        checksums[key] = _sha256(path)
    return dict(sorted(checksums.items()))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
