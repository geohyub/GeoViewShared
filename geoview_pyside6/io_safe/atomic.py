"""
geoview_pyside6.io_safe.atomic
================================
Atomic file writes + user-data guards.

Design decisions:
 - **Temp file in the same directory** as the target so ``os.replace`` can
   perform an atomic rename (cross-device renames are not atomic on any OS).
 - **fsync by default** — pay the cost; the whole point of this module is
   "never leave torn files on disk". Callers who know they are writing to
   a scratch dir can pass ``fsync=False``.
 - **Directory fsync is best-effort** — Windows does not support it, POSIX
   does. Silently skip on platforms where ``os.open(dir, O_RDONLY)`` is
   refused.
 - **Rollback on exception** — if the caller's writer raises mid-stream, the
   temp file is unlinked and the target is left untouched.
 - **Guard lesson: never rmtree symlinks** (cotidal NC 133건 삭제 사고).
   ``safe_rmtree`` refuses symlinks outright and requires the resolved target
   to live inside a declared ``temp_roots`` whitelist. Callers can't even
   "opt out" — if you want to nuke real user data, call ``shutil.rmtree``
   directly and own the risk.
 - ``safe_unlink`` refuses directories; ``safe_rmdir`` refuses non-empty
   directories. Both are thin wrappers that exist so the rest of the codebase
   has an obvious "safe" vocabulary.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Iterator, Sequence

__all__ = [
    "UserDataGuardError",
    "is_within",
    "assert_within_roots",
    "atomic_write_bytes",
    "atomic_write_text",
    "atomic_writer",
    "safe_unlink",
    "safe_rmdir",
    "safe_rmtree",
]


# ---------------------------------------------------------------------------
# Guard primitives
# ---------------------------------------------------------------------------


class UserDataGuardError(Exception):
    """Raised when a destructive operation would touch unapproved territory."""

    def __init__(self, message: str, *, path: Path | None = None) -> None:
        super().__init__(message)
        self.path = path

    def __str__(self) -> str:
        base = super().__str__()
        if self.path is not None:
            return f"{base} (path={self.path})"
        return base


def _resolve(path: Path) -> Path:
    # Use strict=False so non-existent files still canonicalize (we care
    # about the parent). ``os.path.realpath`` handles symlinks on POSIX and
    # the Win32 reparse points we care about.
    return Path(os.path.realpath(path))


def is_within(path: Path | str, root: Path | str) -> bool:
    """Return True when ``path`` resolves to a location inside ``root``."""
    p = _resolve(Path(path))
    r = _resolve(Path(root))
    try:
        p.relative_to(r)
    except ValueError:
        return False
    return True


def assert_within_roots(path: Path | str, roots: Sequence[Path | str]) -> Path:
    """
    Raise :class:`UserDataGuardError` unless ``path`` resolves inside one of
    the supplied ``roots``. Returns the resolved path on success so the
    caller can act on a canonical form.
    """
    p = Path(path)
    if not roots:
        raise UserDataGuardError(
            "no temp roots declared — refusing destructive op",
            path=p,
        )
    resolved = _resolve(p)
    for root in roots:
        if is_within(resolved, root):
            return resolved
    raise UserDataGuardError(
        f"path escapes declared temp roots {[str(r) for r in roots]}",
        path=p,
    )


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def _fsync_dir(directory: Path) -> None:
    """Best-effort fsync on a directory handle. Silently skip on Windows."""
    if os.name == "nt":
        return
    fd = None
    try:
        fd = os.open(directory, os.O_RDONLY)
        os.fsync(fd)
    except OSError:
        pass
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


@contextmanager
def atomic_writer(
    path: Path | str,
    *,
    mode: str = "wb",
    encoding: str | None = None,
    fsync: bool = True,
) -> Iterator[IO]:
    """
    Context manager that yields an open temp file next to ``path``.

    On clean exit the temp file is ``os.replace``'d over ``path`` (atomic).
    On exception the temp file is unlinked and the target is untouched.

    Supported modes: ``"wb"`` (default), ``"w"``. Append modes are refused
    because they undermine atomicity — if you need append, read-modify-write
    with ``atomic_write_bytes``.
    """
    if mode not in ("wb", "w"):
        raise ValueError(f"atomic_writer supports 'wb' or 'w', got {mode!r}")
    target = Path(path)
    parent = target.parent
    if not parent.exists():
        raise FileNotFoundError(
            f"parent directory does not exist: {parent}"
        )

    # Create temp file in the same directory so os.replace is atomic.
    # delete=False so we can manage the lifecycle ourselves across platforms
    # (NamedTemporaryFile on Windows can't be reopened while open).
    is_text = mode == "w"
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=target.name + ".",
        suffix=".tmp",
        dir=parent,
    )
    tmp_path = Path(tmp_name)

    try:
        if is_text:
            fh: IO = os.fdopen(tmp_fd, "w", encoding=encoding or "utf-8", newline="")
        else:
            fh = os.fdopen(tmp_fd, "wb")
        tmp_fd = -1  # ownership transferred to fh
        try:
            yield fh
            fh.flush()
            if fsync:
                try:
                    os.fsync(fh.fileno())
                except OSError:
                    pass
        finally:
            fh.close()
    except BaseException:
        # Rollback: nuke the temp file, leave target alone.
        if tmp_fd != -1:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    # Commit.
    os.replace(tmp_path, target)
    if fsync:
        _fsync_dir(parent)


def atomic_write_bytes(
    path: Path | str,
    data: bytes,
    *,
    fsync: bool = True,
) -> Path:
    """Write ``data`` to ``path`` atomically. Returns the resolved path."""
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(
            f"atomic_write_bytes expects bytes-like, got {type(data).__name__}"
        )
    with atomic_writer(path, mode="wb", fsync=fsync) as fh:
        fh.write(bytes(data))
    return Path(path)


def atomic_write_text(
    path: Path | str,
    text: str,
    *,
    encoding: str = "utf-8",
    fsync: bool = True,
) -> Path:
    """Write ``text`` to ``path`` atomically using ``encoding``."""
    if not isinstance(text, str):
        raise TypeError(
            f"atomic_write_text expects str, got {type(text).__name__}"
        )
    with atomic_writer(path, mode="w", encoding=encoding, fsync=fsync) as fh:
        fh.write(text)
    return Path(path)


# ---------------------------------------------------------------------------
# Safe removal helpers
# ---------------------------------------------------------------------------


def safe_unlink(path: Path | str) -> None:
    """
    Remove a single file (or symlink). Refuses real directories.

    Symlinks are removed via ``os.unlink`` so the target is never followed.
    Missing paths are silently ignored (idempotent).
    """
    p = Path(path)
    try:
        if p.is_symlink():
            os.unlink(p)
            return
        if not p.exists():
            return
        if p.is_dir():
            raise UserDataGuardError(
                "safe_unlink refuses directories — use safe_rmdir or safe_rmtree",
                path=p,
            )
        os.unlink(p)
    except FileNotFoundError:
        return


def safe_rmdir(path: Path | str) -> None:
    """
    Remove an empty directory. Refuses symlinks and non-empty dirs.

    Missing paths are silently ignored.
    """
    p = Path(path)
    if p.is_symlink():
        raise UserDataGuardError(
            "safe_rmdir refuses symlinks — use safe_unlink",
            path=p,
        )
    if not p.exists():
        return
    if not p.is_dir():
        raise UserDataGuardError(
            "safe_rmdir target is not a directory",
            path=p,
        )
    try:
        os.rmdir(p)
    except OSError as exc:
        raise UserDataGuardError(
            f"rmdir failed (directory not empty?): {exc}",
            path=p,
        ) from exc


def safe_rmtree(
    path: Path | str,
    *,
    temp_roots: Sequence[Path | str],
) -> None:
    """
    Recursively remove ``path`` **only** when it resolves inside one of the
    supplied ``temp_roots``.

    Guards enforced:
      - symlinks are refused outright (cotidal lesson);
      - the resolved path must live inside at least one temp root;
      - the resolved path must not *be* one of the temp roots themselves
        (nuking the whitelist root is almost always a bug);
      - missing paths are silently ignored.
    """
    p = Path(path)
    if p.is_symlink():
        raise UserDataGuardError(
            "safe_rmtree refuses symlinks — use safe_unlink",
            path=p,
        )
    if not p.exists():
        return
    if not p.is_dir():
        raise UserDataGuardError(
            "safe_rmtree target is not a directory",
            path=p,
        )
    resolved = assert_within_roots(p, temp_roots)
    for root in temp_roots:
        if resolved == _resolve(Path(root)):
            raise UserDataGuardError(
                "safe_rmtree refuses to delete the temp root itself",
                path=p,
            )
    shutil.rmtree(resolved)
