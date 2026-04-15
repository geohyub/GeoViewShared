"""
Kingdom assembly helper — Phase A-4 Week 18 A4.4.

Takes a :class:`CPTProject` (or a simple list of soundings) and
drives the Week 16 / 17 per-file helpers in one pass, producing a
:class:`KingdomPackage` that describes every file the Week 18 manifest
and drop helpers will touch.

The builder is **I/O-aware but not folder-bound**: the caller provides
a staging directory where the per-file helpers write their output,
and the returned :class:`KingdomPackage` carries the absolute paths.
The atomic drop helper (:mod:`kingdom.drop_helper`) then renames the
staging directory into place.

The builder never touches the vendor xls / cdf sources — it expects
an already-parsed :class:`CPTProject`, which keeps the Week 18 code
free of parser imports and lets the M4 gate feed synthetic projects
for unit testing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

from geoview_cpt.ags_convert.kingdom.checkshot import (
    SCPTSoundingPicks,
    build_checkshot_csv,
)
from geoview_cpt.ags_convert.kingdom.las_export import build_kingdom_las
from geoview_cpt.ags_convert.kingdom.location import (
    build_location_csv_from_bundles,
)
from geoview_cpt.ags_convert.kingdom.subset import write_kingdom_ags
from geoview_cpt.ags_convert.wrapper import AGSBundle, load_ags

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.writer import ProjectMeta
    from geoview_cpt.model import CPTProject, CPTSounding
    from geoview_cpt.scpt.first_break_picking import FirstBreakPick

__all__ = [
    "KingdomPackage",
    "build_kingdom_bundle",
]


@dataclass
class KingdomPackage:
    """
    Manifest of every file in a Kingdom drop.

    Paths are absolute and point inside the staging directory the
    builder was pointed at. ``checkshot_files`` can contain ``None``
    values — a skipped sounding (no seismic picks) records the skip
    here so the manifest generator can list it with a reason.
    """

    staging_dir: Path
    project_id: str
    crs: str
    ags_files: list[Path] = field(default_factory=list)
    las_files: list[Path] = field(default_factory=list)
    checkshot_files: dict[str, Path | None] = field(default_factory=dict)
    location_csv: Path | None = None
    manifest_path: Path | None = None
    readme_path: Path | None = None
    sounding_ids: list[str] = field(default_factory=list)

    @property
    def sounding_count(self) -> int:
        return len(self.sounding_ids)

    @property
    def checkshot_count(self) -> int:
        return sum(1 for p in self.checkshot_files.values() if p is not None)


def build_kingdom_bundle(
    project: "CPTProject | Sequence[CPTSounding]",
    staging_dir: Path | str,
    *,
    project_meta: "ProjectMeta | None" = None,
    crs: str | None = None,
    picks_map: "dict[str, Sequence[FirstBreakPick]] | None" = None,
    source_offset_m: float = 0.0,
    project_client: str = "",
) -> KingdomPackage:
    """
    Assemble every Kingdom companion file for a CPT project.

    Args:
        project:         :class:`CPTProject` or a bare list of
                         :class:`CPTSounding`. The project_id and
                         sounding name are pulled from the object.
        staging_dir:     target directory. The function creates
                         ``AGS/``, ``LAS/``, ``checkshot/``,
                         ``location/`` subfolders under it and writes
                         the files straight into them. Any pre-existing
                         files are overwritten — callers that need
                         atomicity should route through
                         :mod:`kingdom.drop_helper`.
        project_meta:    passed through to :func:`write_kingdom_ags`
                         (injects PROJ defaults). ``crs`` wins over
                         ``project_meta.crs`` when both are supplied.
        crs:             target Kingdom CRS — stamped into every AGS
                         file's LOCA_GREF and into the checkshot CRS
                         comment line.
        picks_map:       optional ``{loca_id: FirstBreakPick list}``.
                         Missing entries (or empty lists) are recorded
                         as skipped in ``checkshot_files``.
        source_offset_m: forwarded to the checkshot writer.
        project_client:  forwarded to the LAS well section (COMP).

    Returns:
        A :class:`KingdomPackage` whose ``manifest_path`` / ``readme_path``
        are still ``None`` — those are filled by the Week 18 A4.5/A4.6
        steps downstream.
    """
    staging_dir = Path(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    ags_dir = staging_dir / "AGS"
    las_dir = staging_dir / "LAS"
    cs_dir = staging_dir / "checkshot"
    loc_dir = staging_dir / "location"
    for sub in (ags_dir, las_dir, cs_dir, loc_dir):
        sub.mkdir(parents=True, exist_ok=True)

    # Normalise the sounding list + resolve project_id
    soundings, project_id = _extract_soundings(project)

    # Resolve CRS precedence: explicit > project_meta > first header
    target_crs = (crs or "").strip()
    if not target_crs and project_meta is not None:
        target_crs = (project_meta.crs or "").strip()
    if not target_crs and soundings:
        first_header = soundings[0].header
        if first_header is not None:
            target_crs = (first_header.loca_crs or "").strip()

    picks_map = picks_map or {}

    pkg = KingdomPackage(
        staging_dir=staging_dir,
        project_id=project_id,
        crs=target_crs,
        sounding_ids=[s.name for s in soundings],
    )

    bundles: list[AGSBundle] = []
    for sounding in soundings:
        ags_name = _ags_filename(project_id, sounding.name)
        ags_path = ags_dir / ags_name
        write_kingdom_ags(
            sounding, ags_path, project_meta=project_meta, crs=target_crs
        )
        pkg.ags_files.append(ags_path)
        bundles.append(load_ags(ags_path))

        # LAS — one per sounding
        las_path = las_dir / f"{sounding.name}.las"
        build_kingdom_las(sounding, las_path, project_client=project_client)
        pkg.las_files.append(las_path)

        # Checkshot — record skip in manifest when picks absent
        picks = list(picks_map.get(sounding.name, []))
        record = SCPTSoundingPicks(
            loca_id=sounding.name,
            picks=picks,
            crs=target_crs,
            source_offset_m=source_offset_m,
        )
        cs_path = cs_dir / f"{sounding.name}.csv"
        pkg.checkshot_files[sounding.name] = build_checkshot_csv(record, cs_path)

    # Project-wide location CSV
    loc_path = loc_dir / "project_locations.csv"
    build_location_csv_from_bundles(bundles, loc_path)
    pkg.location_csv = loc_path

    return pkg


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _extract_soundings(
    project: "CPTProject | Sequence[CPTSounding]",
) -> tuple[list["CPTSounding"], str]:
    """Normalise the ``project`` argument into a list + project_id."""
    if hasattr(project, "soundings") and not isinstance(project, (list, tuple)):
        soundings = list(getattr(project, "soundings") or [])
        project_id = str(getattr(project, "project_id", "") or "")
    else:
        soundings = list(project)  # type: ignore[arg-type]
        project_id = ""
    if not project_id:
        project_id = "GEOVIEW_CPT"
    return soundings, project_id


def _ags_filename(project_id: str, sounding_name: str) -> str:
    """``<project>_<sounding>.ags`` per Week 16 folder layout."""
    project_slug = project_id.replace(" ", "_").replace("/", "_")
    sounding_slug = sounding_name.replace(" ", "_").replace("/", "_")
    return f"{project_slug}_{sounding_slug}.ags"
