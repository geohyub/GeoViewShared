"""
geoview_cpt.parsers._xml_fix
================================
The **mandatory** entry point for parsing Geologismiki CPeT-IT v30 ``.cpt``
XML. Every reader in this package must go through :func:`parse_cpet_it_xml`
— direct use of ``lxml.etree.fromstring`` on the inflated bytes is
forbidden because the document contains numeric element names that violate
XML 1.0's ``NameStartChar`` production (``<87616>``, ``<1>`` … ``<13>``).

Contract (enforced by master brief
``plans/cpt_wave0_docs/cpet_it_v30_schema.md`` ⚠️ section, commit ``6ddff13``):

 - :func:`parse_cpet_it_xml` takes the inflated ``.cpt`` bytes and returns
   the parsed ``_Element`` root.
 - :func:`real_tag` accepts either an element or a raw tag string and
   returns the original CPeT-IT tag name, stripping the leading ``_``
   that the fix-up regex inserted when the tag name is purely numeric.
 - :func:`serialize_cpet_it_xml` is the round-trip partner for A2.0c
   writer: it takes an ``_Element`` or raw serialized bytes produced by
   lxml and restores the original numeric tags so CPeT-IT can re-open the
   file.

Regex strategy (matches the master brief verbatim):

    fixed = re.sub(rb'<(/?)(\\d)', rb'<\\1_\\2', inflated_bytes)

Only the first digit right after ``<`` (or ``</``) is the replacement
target — the remaining digits are preserved as-is because the pattern
captures exactly three characters. So ``<87616>`` becomes ``<_87616>``
and ``</13>`` becomes ``</_13>``, without touching attribute content or
element text.

Non-numeric tags (``<Various>``, ``<CPTName>``, …) never match the
pattern because their first character is a letter.
"""
from __future__ import annotations

import re
from typing import Union

from lxml import etree
from lxml.etree import _Element

__all__ = [
    "parse_cpet_it_xml",
    "real_tag",
    "serialize_cpet_it_xml",
]


# --- Forward fix (parse side) -----------------------------------------------

_NUMERIC_TAG_PATTERN = re.compile(rb"<(/?)(\d)")


def _fix_numeric_tags(inflated_bytes: bytes) -> bytes:
    """Apply the ``<(/?)(\\d)  →  <\\1_\\2`` substitution from the master brief."""
    return _NUMERIC_TAG_PATTERN.sub(rb"<\1_\2", inflated_bytes)


def parse_cpet_it_xml(inflated_bytes: bytes) -> _Element:
    """
    Parse a Geologismiki ``.cpt`` v30 XML payload into an lxml tree.

    Args:
        inflated_bytes: ``zlib.decompress()`` output from a ``.cpt`` file.

    Returns:
        The parsed lxml ``_Element`` root (always ``<CPT Version="30">``
        for a well-formed v30 document).

    Raises:
        lxml.etree.XMLSyntaxError: if the document is still malformed
                                   after the numeric-tag fix-up (callers
                                   should translate this to the domain
                                   exception their module defines).
    """
    if not isinstance(inflated_bytes, (bytes, bytearray, memoryview)):
        raise TypeError(
            f"parse_cpet_it_xml expects bytes-like, got "
            f"{type(inflated_bytes).__name__}"
        )
    fixed = _fix_numeric_tags(bytes(inflated_bytes))
    return etree.fromstring(fixed)


# --- Tag recovery (traverse side) -------------------------------------------

_RESTORE_TAG_RE = re.compile(r"^_(\d+)$")


def real_tag(element_or_tag: Union[_Element, str]) -> str:
    """
    Return the original CPeT-IT tag name for an element (or raw tag string).

    Strips the leading ``_`` inserted by :func:`parse_cpet_it_xml` only
    when the remaining characters are all digits. Non-numeric tags
    (e.g. ``_foo``, ``CPTName``) pass through unchanged so this function
    is safe to call unconditionally while walking a tree.
    """
    if hasattr(element_or_tag, "tag"):
        tag = element_or_tag.tag
    else:
        tag = element_or_tag
    if not isinstance(tag, str):
        return tag  # lxml comment / PI — pass through
    m = _RESTORE_TAG_RE.match(tag)
    if m:
        return m.group(1)
    return tag


# --- Reverse fix (writer side) ----------------------------------------------

_RESTORE_ELEMENT_PATTERN = re.compile(rb"<(/?)_(\d)")


def serialize_cpet_it_xml(tree_or_bytes: Union[_Element, bytes]) -> bytes:
    """
    Serialize an lxml element (or pre-serialized bytes) back to the
    CPeT-IT wire format, reversing the numeric-tag fix-up.

    Intended for the A2.0c writer. Safe for round-trip on raw bytes that
    still contain the ``_DDDDD`` prefix (e.g. the ``chart_config_raw``
    blobs preserved on :class:`CPTSounding`).
    """
    if isinstance(tree_or_bytes, (bytes, bytearray, memoryview)):
        raw = bytes(tree_or_bytes)
    else:
        raw = etree.tostring(tree_or_bytes)
    return _RESTORE_ELEMENT_PATTERN.sub(rb"<\1\2", raw)
