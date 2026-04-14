"""
geoview_pyside6.io_safe
================================
Safe filesystem primitives for the GeoView software suite (Phase A-1 A1.3).

Two responsibilities:

1. **Atomic writes** — write to a sibling temp file, fsync, then ``os.replace``
   so readers never observe a half-written file. Covers both raw bytes and
   text, plus a context-manager form for streaming writes.

2. **User-data guards** — refuse destructive operations (``unlink``, ``rmdir``,
   ``rmtree``) on paths that look like real user data. The guard enforces:
     - symlinks are never followed for removal (lesson: cotidal NC 133 삭제 사고);
     - ``safe_rmtree`` only accepts paths resolving inside a caller-supplied
       ``temp_roots`` whitelist;
     - directories are refused unless explicitly allowed.

Public API:

    atomic_write_bytes, atomic_write_text, atomic_writer
    UserDataGuardError, assert_within_roots, is_within
    safe_unlink, safe_rmdir, safe_rmtree

Consumers (Phase A-2+):
    geoview_cpt.export.*            atomic project-file writes
    geoview_cpt.tempdir.scrub        build-harness temp cleanup
    MBES/Mag/Seismic export engines (A1.5)
"""
from __future__ import annotations

from geoview_pyside6.io_safe.atomic import (
    UserDataGuardError,
    assert_within_roots,
    atomic_write_bytes,
    atomic_write_text,
    atomic_writer,
    is_within,
    safe_rmdir,
    safe_rmtree,
    safe_unlink,
)

__all__ = [
    "atomic_write_bytes",
    "atomic_write_text",
    "atomic_writer",
    "UserDataGuardError",
    "assert_within_roots",
    "is_within",
    "safe_unlink",
    "safe_rmdir",
    "safe_rmtree",
]
