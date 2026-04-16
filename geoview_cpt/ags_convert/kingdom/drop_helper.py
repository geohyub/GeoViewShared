"""
Atomic Kingdom drop — Phase A-4 Week 18 A4.7.

The Week 18 A4.4 assembly writes a full ``09_kingdom/`` layout into a
staging directory; this module moves that staging directory into the
final destination atomically so a half-completed drop never
overwrites a prior successful drop.

Strategy:

    1. Staging lives under ``tempfile.mkdtemp`` (caller-managed or
       internal). The assembly helper writes there.
    2. If ``dest_dir`` already exists, rename it to
       ``<dest_dir>.backup.<yyyyMMdd_HHmmss>`` before the move.
    3. ``shutil.move(staging, dest_dir)`` places the staging contents
       as the new ``dest_dir``.
    4. Any exception rolls back: the partial dest (if present) is
       removed and the backup is renamed back.

All file-level I/O is delegated to :mod:`shutil`, so Windows / Linux
semantics match. On Windows cross-volume moves fall back to
``shutil.copytree`` under the hood (``shutil.move`` handles the
distinction automatically).
"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from geoview_cpt.ags_convert.wrapper import AgsConvertError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.kingdom.assembly import KingdomPackage

__all__ = [
    "drop_to_kingdom_folder",
    "backup_existing",
]


def drop_to_kingdom_folder(
    package: "KingdomPackage",
    dest_dir: Path | str,
    *,
    backup_existing_dir: bool = True,
) -> Path:
    """
    Atomically move the staging directory into ``dest_dir``.

    Args:
        package:              :class:`KingdomPackage` whose
                              ``staging_dir`` holds the full bundle.
        dest_dir:             target path — the final
                              ``09_kingdom/`` location.
        backup_existing_dir:  when ``True`` (default) an existing
                              ``dest_dir`` is renamed to
                              ``<dest_dir>.backup.<timestamp>`` before
                              the move. When ``False`` the existing
                              directory is removed outright.

    Returns:
        The resolved ``dest_dir`` path.

    Raises:
        AgsConvertError: when the staging directory is missing or
                         the move fails; any partial state is rolled
                         back.
    """
    staging = Path(package.staging_dir)
    dest = Path(dest_dir)

    if not staging.exists() or not staging.is_dir():
        raise AgsConvertError(
            f"staging directory missing: {staging!s}"
        )

    dest.parent.mkdir(parents=True, exist_ok=True)

    backup_path: Path | None = None
    if dest.exists():
        if backup_existing_dir:
            backup_path = backup_existing(dest)
        else:
            shutil.rmtree(dest)

    try:
        shutil.move(str(staging), str(dest))
    except Exception as exc:
        # Roll back: if the move partially created dest, wipe it and
        # restore the backup so the user is not left in an
        # inconsistent state.
        if dest.exists():
            try:
                shutil.rmtree(dest)
            except OSError:
                pass
        if backup_path is not None and backup_path.exists():
            try:
                shutil.move(str(backup_path), str(dest))
            except OSError:
                pass
        raise AgsConvertError(
            f"atomic drop failed for {dest!s}: {exc}"
        ) from exc

    return dest


def backup_existing(dest: Path) -> Path:
    """
    Rename ``dest`` to ``<dest>.backup.<timestamp>`` and return the
    new path. Used as a rollback anchor by
    :func:`drop_to_kingdom_folder`.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = dest.with_name(f"{dest.name}.backup.{stamp}")
    i = 1
    while backup.exists():
        backup = dest.with_name(f"{dest.name}.backup.{stamp}_{i}")
        i += 1
    shutil.move(str(dest), str(backup))
    return backup
