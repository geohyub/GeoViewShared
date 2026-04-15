"""
geoview-ags CLI — Phase A-3 Week 15 A3.5.

Three subcommands:

    geoview-ags convert <src> <dst> [--format FORMAT]
        Convert between ``.ags`` and any supported format. When
        ``--format`` is omitted the CLI infers the target format
        from the ``<dst>`` extension (``.ags`` / ``.xlsx`` /
        ``.csv`` / ``.json`` / ``.parquet`` / ``.las``).

    geoview-ags validate <ags_file> [--strict]
        Run the Rule 1-20 validator against ``<ags_file>``. Exits
        with code 0 when no errors are found, code 2 when there
        are ERROR severity issues. With ``--strict`` warnings are
        promoted to errors and also exit 2.

    geoview-ags round-trip-check <ags_file>
        Verify byte-level dump idempotency (two-pass) by
        load→dump→load→dump and comparing bytes. Exits 0 on pass,
        3 on divergence.

The CLI is registered as a console_script in
``pyproject.toml``::

    [project.scripts]
    geoview-ags = "geoview_cpt.ags_convert.cli:main"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from geoview_cpt.ags_convert.converters import convert as _convert_dispatch
from geoview_cpt.ags_convert.validator import (
    Severity,
    validate_file as _validate_file,
)
from geoview_cpt.ags_convert.wrapper import dump_ags, load_ags

__all__ = ["main", "build_parser"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geoview-ags",
        description="GeoView AGS4 v4.1.1 toolkit (convert / validate / round-trip)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # convert
    conv = sub.add_parser(
        "convert",
        help="Convert between .ags and {xlsx, csv, json, parquet, las}",
    )
    conv.add_argument("src", type=Path, help="source file or directory")
    conv.add_argument("dst", type=Path, help="destination file or directory")
    conv.add_argument(
        "--format",
        choices=("ags", "xlsx", "csv", "json", "parquet", "las"),
        default=None,
        help="force destination format (default: infer from extension)",
    )

    # validate
    val = sub.add_parser(
        "validate",
        help="Run the AGS4 Rule 1-20 validator on an .ags file",
    )
    val.add_argument("ags_file", type=Path)
    val.add_argument(
        "--strict",
        action="store_true",
        help="Promote WARNING severity to ERROR for exit-code purposes",
    )

    # round-trip-check
    rtc = sub.add_parser(
        "round-trip-check",
        help="Verify two-pass byte-level idempotency of an .ags file",
    )
    rtc.add_argument("ags_file", type=Path)

    return parser


def _cmd_convert(args: argparse.Namespace) -> int:
    try:
        out = _convert_dispatch(args.src, args.dst, dst_format=args.format)
    except Exception as exc:
        print(f"convert failed: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {out}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        errors = _validate_file(args.ags_file)
    except Exception as exc:
        print(f"validate failed: {exc}", file=sys.stderr)
        return 1

    fatal_severities = {Severity.ERROR}
    if args.strict:
        fatal_severities.add(Severity.WARNING)
    fatal = [e for e in errors if e.severity in fatal_severities]

    for err in errors:
        print(str(err))
    summary = f"{len(errors)} total, {len(fatal)} fatal"
    print(f"— {summary}")

    return 2 if fatal else 0


def _cmd_roundtrip(args: argparse.Namespace) -> int:
    import tempfile

    try:
        path = Path(args.ags_file)
        raw_v1 = path.read_bytes()
        bundle_v1 = load_ags(path)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            p2 = td / "v2.ags"
            dump_ags(bundle_v1, p2)
            b2 = load_ags(p2)
            p3 = td / "v3.ags"
            dump_ags(b2, p3)
            v2_bytes = p2.read_bytes()
            v3_bytes = p3.read_bytes()
    except Exception as exc:
        print(f"round-trip-check failed: {exc}", file=sys.stderr)
        return 1

    ok = v2_bytes == v3_bytes
    if ok:
        print(f"OK — two-pass idempotent ({len(v2_bytes)} bytes)")
        return 0
    print(
        f"FAIL — v2 and v3 dumps differ ({len(v2_bytes)} vs {len(v3_bytes)} bytes)",
        file=sys.stderr,
    )
    return 3


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "convert":
        return _cmd_convert(args)
    if args.cmd == "validate":
        return _cmd_validate(args)
    if args.cmd == "round-trip-check":
        return _cmd_roundtrip(args)
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
