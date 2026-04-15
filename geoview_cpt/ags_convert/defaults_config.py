"""
geoview_cpt.ags_convert.defaults_config
===========================================
``on_missing='inject_default'`` support — Week 14 A3.2 Part 2.

The writer normally emits empty strings for fields the A-2 parser
cannot recover from vendor bundles (Week 13 ``on_missing='omit'``).
Under ``inject_default`` the caller supplies a per-project **defaults
map** whose keys correspond to :class:`ProjectMeta` fields; any field
on the incoming :class:`ProjectMeta` left at its dataclass default is
filled from the defaults map **without** overriding the ones the
caller already populated.

Two input channels are supported:

 1. **In-process dict** set via :func:`set_process_defaults` — handy
    for tests and for Phase B CPTPrep UI injection.
 2. **YAML file on disk** set via :envvar:`GEOVIEW_CPT_AGS4_DEFAULTS`
    (absolute path). Parsed lazily, cached per run. The dict channel
    wins when both are supplied so tests can override without env
    side-effects.

The config file itself is a flat mapping ``field_name: value`` whose
keys must be a subset of :class:`ProjectMeta` fields — unknown keys
raise :class:`AgsConvertError` so typos are caught early.

Week 15 A3.4 converters will reuse this module when the xlsx / csv /
las → ags pipelines need site-specific defaults.
"""
from __future__ import annotations

import os
from dataclasses import fields, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from geoview_cpt.ags_convert.wrapper import AgsConvertError

if TYPE_CHECKING:
    from geoview_cpt.ags_convert.writer import ProjectMeta

__all__ = [
    "DEFAULTS_ENV_VAR",
    "apply_defaults",
    "load_defaults_file",
    "set_process_defaults",
    "clear_process_defaults",
]


DEFAULTS_ENV_VAR = "GEOVIEW_CPT_AGS4_DEFAULTS"

_process_defaults: dict[str, Any] | None = None
_file_defaults_cache: dict[str, dict[str, Any]] = {}


def set_process_defaults(defaults: Mapping[str, Any] | None) -> None:
    """Register an in-process defaults map. ``None`` clears it."""
    global _process_defaults
    if defaults is None:
        _process_defaults = None
        return
    _validate_keys(defaults)
    _process_defaults = dict(defaults)


def clear_process_defaults() -> None:
    """Shortcut for ``set_process_defaults(None)``."""
    set_process_defaults(None)


def load_defaults_file(path: str | Path) -> dict[str, Any]:
    """
    Parse a YAML defaults file and return a validated dict.

    The file path is cached so repeated calls are cheap. Call
    :func:`clear_defaults_cache` to invalidate during tests.
    """
    key = str(Path(path).resolve())
    if key in _file_defaults_cache:
        return _file_defaults_cache[key]

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover — yaml is a hard dep via pandas
        raise AgsConvertError(
            "pyyaml is required for on_missing='inject_default'"
        ) from exc

    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise AgsConvertError(
            f"defaults file {path!s} could not be read: {exc}"
        ) from exc

    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise AgsConvertError(
            f"defaults file {path!s} must contain a top-level mapping"
        )
    _validate_keys(data)
    _file_defaults_cache[key] = data
    return data


def clear_defaults_cache() -> None:
    """Wipe the file-level defaults cache (tests only)."""
    _file_defaults_cache.clear()


def apply_defaults(meta: "ProjectMeta | None") -> "ProjectMeta":
    """
    Merge defaults into a :class:`ProjectMeta`.

    Precedence (highest wins):
        1. Fields already set on ``meta`` (non-default values)
        2. :func:`set_process_defaults` dict
        3. File pointed at by :envvar:`GEOVIEW_CPT_AGS4_DEFAULTS`

    Passing ``None`` returns a fresh ``ProjectMeta`` pre-populated from
    the defaults map.
    """
    from geoview_cpt.ags_convert.writer import ProjectMeta  # local — circular safe

    defaults: dict[str, Any] = {}
    env_path = os.environ.get(DEFAULTS_ENV_VAR, "").strip()
    if env_path:
        defaults.update(load_defaults_file(env_path))
    if _process_defaults:
        defaults.update(_process_defaults)

    if not defaults:
        return meta if meta is not None else ProjectMeta()

    if meta is None:
        return ProjectMeta.from_dict(defaults)

    # Field-by-field merge: caller wins when value != dataclass default.
    field_defaults = {f.name: f.default for f in fields(ProjectMeta)}
    updates: dict[str, Any] = {}
    for name, def_val in field_defaults.items():
        current = getattr(meta, name)
        if current == def_val and name in defaults:
            updates[name] = defaults[name]
    return replace(meta, **updates) if updates else meta


def _validate_keys(data: Mapping[str, Any]) -> None:
    from geoview_cpt.ags_convert.writer import ProjectMeta

    known = {f.name for f in fields(ProjectMeta)}
    unknown = sorted(set(data.keys()) - known)
    if unknown:
        raise AgsConvertError(
            f"unknown ProjectMeta defaults: {unknown!r} (known: {sorted(known)})"
        )
