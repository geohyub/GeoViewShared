"""
geoview_cpt.parsers._xml_sanitize
===================================
Numeric-tag mangling for CPeT-IT ``.cpt`` XML.

CPeT-IT writes element names that start with a digit (e.g. ``<87616>``,
``<1>``, ``<2>``). These are **invalid XML** per the W3C Name production
(``NameStartChar`` excludes digits). Stock lxml refuses to parse such
documents.

The fix used by :mod:`cpet_it_v30` is to pre-process the raw text,
prefixing every numeric tag with a stable marker so lxml can build a
tree; every read/write goes through this module so round-trip is
reversible.

The marker is :data:`NUMERIC_TAG_PREFIX` (``"n_"``). On the write side
:func:`unmangle` restores the exact original bytes — verified by the
test suite via a mangle → unmangle round-trip.

This is the only place in the codebase that touches raw CPT XML bytes.
"""
from __future__ import annotations

import re

__all__ = [
    "NUMERIC_TAG_PREFIX",
    "mangle",
    "unmangle",
    "is_mangled_tag",
    "original_tag",
]


NUMERIC_TAG_PREFIX = "n_"

# Matches <87616>, </87616>, <87616/>, <87616 attr="x">
#   group(1) = optional leading "/"
#   group(2) = the digits
#   group(3) = the character right after the digits (space, "/", or ">")
_MANGLE_RE = re.compile(r"<(/?)(\d+)([/> ])")

# The reverse: finds the prefixed form ("<n_DDD>", "</n_DDD>", etc.) and
# strips the prefix only when the remainder is all digits.
_UNMANGLE_RE = re.compile(
    r"<(/?)" + re.escape(NUMERIC_TAG_PREFIX) + r"(\d+)([/> ])"
)


def mangle(xml_text: str) -> str:
    """
    Rewrite numeric element names as ``n_DDD`` so lxml will accept them.

    Idempotent: applying ``mangle`` twice is the same as applying it once
    because the second pass never matches (already prefixed names don't
    start with a digit).
    """
    return _MANGLE_RE.sub(
        lambda m: f"<{m.group(1)}{NUMERIC_TAG_PREFIX}{m.group(2)}{m.group(3)}",
        xml_text,
    )


def unmangle(xml_text: str) -> str:
    """Reverse of :func:`mangle` — restore the original numeric tags."""
    return _UNMANGLE_RE.sub(
        lambda m: f"<{m.group(1)}{m.group(2)}{m.group(3)}",
        xml_text,
    )


def is_mangled_tag(tag: str) -> bool:
    """Return True when ``tag`` was produced by :func:`mangle`."""
    if not tag.startswith(NUMERIC_TAG_PREFIX):
        return False
    rest = tag[len(NUMERIC_TAG_PREFIX):]
    return bool(rest) and rest.isdigit()


def original_tag(tag: str) -> str:
    """
    Return the original CPeT-IT tag name for a possibly-mangled ``tag``.

    If ``tag`` is not a mangled numeric tag the input is returned unchanged,
    so this function is safe to call on every element regardless of origin.
    """
    if is_mangled_tag(tag):
        return tag[len(NUMERIC_TAG_PREFIX):]
    return tag
