"""
geoview_pyside6.qc_engine.loader
================================
YAML → RulePack loader with pluggable check resolution (Step 3).

Two resolution modes for the ``check:`` field in YAML:

1. **Registry lookup** (preferred) — data-first authors register check
   functions by short name via :meth:`RuleCheckRegistry.register`,
   and YAML references them by that name. This keeps YAML decoupled
   from the Python module layout.

2. **Dotted import fallback** — if the registry does not know the name,
   the loader attempts ``importlib.import_module`` on the leading
   package segments and ``getattr`` for the final attribute. Enabled
   by default; set ``allow_import=False`` on :func:`load_yaml` to lock
   resolution down to the registry (recommended in production).
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable

import yaml

from geoview_pyside6.qc_engine.rules import Rule, RulePack, RuleCheck, Severity
from geoview_pyside6.qc_engine.schema import RulePackSchema, RuleSchema

__all__ = ["RuleCheckRegistry", "load_yaml", "LoaderError"]


class LoaderError(Exception):
    """Raised when YAML cannot be converted into a RulePack."""


class RuleCheckRegistry:
    """Name → callable registry for YAML-declared rule checks."""

    def __init__(self) -> None:
        self._entries: dict[str, Callable[..., list]] = {}

    def register(self, name: str, fn: Callable[..., list]) -> None:
        if not name:
            raise ValueError("registry key must be non-empty")
        if not callable(fn):
            raise TypeError(f"{name!r} is not callable")
        if name in self._entries:
            raise ValueError(f"check {name!r} already registered")
        self._entries[name] = fn

    def get(self, name: str) -> Callable[..., list] | None:
        return self._entries.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._entries

    def __len__(self) -> int:
        return len(self._entries)


def _resolve_dotted(path: str) -> Callable[..., list]:
    if "." not in path:
        raise LoaderError(
            f"check {path!r} is not in the registry and is not a dotted path"
        )
    module_name, _, attr = path.rpartition(".")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise LoaderError(f"cannot import module {module_name!r}: {exc}") from exc
    try:
        fn = getattr(module, attr)
    except AttributeError as exc:
        raise LoaderError(
            f"module {module_name!r} has no attribute {attr!r}"
        ) from exc
    if not callable(fn):
        raise LoaderError(f"{path!r} resolved to a non-callable {type(fn).__name__}")
    return fn


def _resolve_check(
    name: str,
    registry: RuleCheckRegistry | None,
    allow_import: bool,
) -> Callable[..., list]:
    if registry is not None:
        hit = registry.get(name)
        if hit is not None:
            return hit
    if not allow_import:
        raise LoaderError(
            f"check {name!r} not found in registry and allow_import=False"
        )
    return _resolve_dotted(name)


def _build_rule(
    spec: RuleSchema,
    registry: RuleCheckRegistry | None,
    allow_import: bool,
) -> Rule:
    check = _resolve_check(spec.check, registry, allow_import)
    auto_fix = None
    if spec.auto_fix:
        auto_fix = _resolve_check(spec.auto_fix, registry, allow_import)
    return Rule(
        id=spec.id,
        title=spec.title,
        severity=Severity.coerce(spec.severity),
        category=spec.category,
        check=check,
        auto_fix=auto_fix,
        description=spec.description,
        parameters=dict(spec.parameters),
    )


def load_yaml(
    path: str | Path,
    *,
    registry: RuleCheckRegistry | None = None,
    allow_import: bool = True,
) -> RulePack:
    """
    Load a YAML RulePack file.

    Args:
        path:          Path to the ``.yaml`` file.
        registry:      Optional :class:`RuleCheckRegistry` for name resolution.
        allow_import:  If True (default), unknown check names fall back to
                       dotted-path import. Set False to lock down to the registry.

    Returns:
        A :class:`RulePack` with all checks resolved to real callables.

    Raises:
        LoaderError:   on YAML parse errors or unresolvable checks.
        pydantic.ValidationError: on schema violations.
    """
    p = Path(path)
    if not p.exists():
        raise LoaderError(f"YAML file not found: {p}")
    try:
        raw: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LoaderError(f"invalid YAML: {exc}") from exc
    if raw is None:
        raise LoaderError(f"YAML file {p} is empty")
    if not isinstance(raw, dict):
        raise LoaderError(f"YAML root must be a mapping, got {type(raw).__name__}")

    spec = RulePackSchema.model_validate(raw)
    rules = [_build_rule(r, registry, allow_import) for r in spec.rules]
    return RulePack(
        name=spec.name,
        version=spec.version,
        domain=spec.domain,
        rules=rules,
        description=spec.description,
    )
