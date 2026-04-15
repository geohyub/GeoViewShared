# python-ags4 v1.0.0 — Known Gaps

> **Living document.** Recorded against `python-ags4==1.0.0` (the pinned
> dependency for Phase A-3). Each entry lists a reproducer, the AGS4
> v4.1 spec reference, and how we work around it in
> `geoview_cpt.ags_convert`.

Phase A-3 Week 14 A3.3 delivers our own Rule 1–20 validator precisely
because several of these gaps also affect `AGS4.check_file`. The
numbered gaps below map one-to-one with the validator modules that
re-implement the missing behaviour.

## Gap #1 — TRAN_DLIM / TRAN_RCON mangled on reload

**Symptom.** The writer emits
``"TRAN_DLIM","""",`` (AGS4-escaped double quote) which AGS4 v4.1 §3.4
requires to be the single character `"` inside the cell. After one
`AGS4_to_dataframe → dataframe_to_AGS4` cycle the cell becomes `""`
(empty string) — the embedded quote is dropped, not preserved.

**Reproducer.**
```python
from python_ags4 import AGS4
tables, _ = AGS4.AGS4_to_dataframe('sample.ags')
AGS4.dataframe_to_AGS4(tables, headings={}, filepath='out.ags')
# sample.ags and out.ags differ in the TRAN row only: "\""\"" vs ""
```

**Spec reference.** AGS4 v4.1 Rule 3 and TRAN group dictionary.

**Impact.** Byte-level round-trip of Week 14 A3.2 Part 2 cannot assert
`v1 == v2` on the first `write_ags → load_ags → dump_ags` cycle.
Subsequent cycles **are** idempotent, so the test scaffolding uses
two-pass idempotency (`v2 == v3`) and the first-cycle check is
restricted to the SCPT group (see
`test_byte_roundtrip.test_byte_roundtrip_core_fields_preserved`).

**Workaround.** None at the writer level — the AGS4 spec demands the
literal double quote. We rely on the two-pass idempotency check and
the semantic round-trip (`load_ags → field equality`). A PR upstream
would need to fix `python_ags4.AGS4._parse_data_row` to accept escaped
quotes.

## Gap #2 — `AGS4.check_file` is print-only

**Symptom.** The only public validator entry point,
`AGS4.check_file(path)`, writes rule violations to stdout via
`print_output=True` by default and returns an opaque dict keyed by
rule number. There is no structured `ValidationError` class, no
severity, and no per-field pointer, so downstream consumers have no
stable API.

**Reproducer.**
```python
from python_ags4 import AGS4
errors = AGS4.check_file('broken.ags', print_output=False)
# errors is a dict: {'1': [{'line': 3, 'group': ..., 'desc': ...}], ...}
# No stable types for line/group/desc; spec rules 5, 6, 10c absent.
```

**Impact.** Rule 1–20 cannot be consumed programmatically from the
library.

**Workaround.** Phase A-3 Week 14 A3.3 implements
`geoview_cpt.ags_convert.validator` with a typed `ValidationError`
model and one module per rule family (structure / fields / quoting /
dictionary / references / required_groups / naming / files).

## Gap #3 — Rule 10a (KEY uniqueness) incomplete

**Symptom.** `AGS4.check_file` enforces AGS4 Rule 10a only on a
per-row basis and does not detect duplicate composite-key collisions
for groups whose KEY is spread across multiple headings (SAMP KEY is
`(LOCA_ID, SAMP_TOP, SAMP_REF, SAMP_TYPE, SAMP_ID)` — a row with a
duplicate composite KEY silently passes).

**Reproducer.** Two SAMP rows differing only in `SAMP_BASE` but
sharing the five KEY columns pass `check_file` with no Rule 10
violation.

**Impact.** Lab-data pipelines building SAMP from vendor bundles need
the composite-key uniqueness check to catch operator typos.

**Workaround.** Reimplemented in
`validator/dictionary.py::check_rule_10a`. The check fetches the KEY
column list from the standard dictionary and hashes the tuple of
KEY-column values per row.

## Gap #4 — Rule 10c (parent-group reference) incomplete

**Symptom.** AGS4 v4.1 Rule 10c requires that every value in a child
group's reference column exists in the parent group's KEY column. For
example every `GEOL.LOCA_ID` value must appear in `LOCA.LOCA_ID`.
`AGS4.check_file` enforces this for the four built-in parent
relationships (LOCA→GEOL, LOCA→SAMP, ...) but misses relationships
declared via DICT_PGRP on user-defined groups, and misses the SCPT
group entirely.

**Reproducer.** Delete every row from the LOCA group while keeping the
SCPT rows — `check_file` reports 0 Rule 10 errors.

**Impact.** Phase A-3 Week 14 A3.3 ships with strict LOCA → SCPT
coverage because the CPT writer is the primary producer.

**Workaround.** Reimplemented in
`validator/references.py::check_rule_10c`. Traverses DICT_PGRP for
every group in the bundle plus a hardcoded extension list for SCPT /
SCPG / SCPP → LOCA.

## Gap #5 — Rule 13–18 required-group coverage

**Symptom.** `AGS4.check_file` checks that PROJ / TRAN / UNIT / TYPE /
DICT (the five mandatory "file-level" groups per Rule 13) exist but
does not distinguish "group present but zero DATA rows" from "group
missing". The PROJ/TRAN rules actually require a populated DATA row.

**Impact.** A writer producing an empty PROJ group (zero data rows)
passes the library check but fails AGS4 spec.

**Workaround.** `validator/required_groups.py` implements the
"exactly one DATA row" check for PROJ and TRAN and the
"at-least-one-data-row" check for UNIT/TYPE/DICT.

## Gap #6 — HoleBASE SI / gINT V8i exporter compatibility

Out of scope for v1.0; tracked under R6 in the Phase A-3 risk
register. Both vendor apps reject AGS4 files that use non-ASCII
characters inside `GEOL_DESC` (e.g. Korean soil descriptors). Our
writer does not transliterate — vendor compatibility is a v1.1 task
owned by DataForge.

## Gap #7 — UNIT dictionary round-trip sort order

**Symptom.** `dataframe_to_AGS4` sorts the UNIT / TYPE dictionary DATA
rows alphabetically on the first write but re-sorts them on every
subsequent write. This is benign for semantic comparisons but
prevents a strict v1 == v2 byte check.

**Impact.** Contributes (alongside Gap #1) to the `write → load →
dump` non-idempotency we see in Week 14 byte-level testing.

**Workaround.** Our writer builds the UNIT/TYPE dictionaries from a
sorted list already, so successive writes are deterministic; the
first write→load→dump mismatch is entirely driven by Gap #1.

---

## Gaps NOT reimplemented

The following rules are implemented **only** as thin wrappers around
`AGS4.check_file`, because the library implementation is correct and
the value of re-writing them is low:

- Rule 1 — file encoding / UTF-8 BOM detection
- Rule 2 — line endings (CRLF)
- Rule 2a — empty-line separators between groups
- Rule 2b — no line longer than 240 characters (relaxed — advisory
  only)
- Rule 19 / 19a / 19b — heading naming conventions (checked against
  `[A-Z0-9_]{,10}` regex via `validator/naming.py`)

Our validator re-implements Rules 3–12 fully and Rules 13–18 partially
to close Gaps #2–#5 above.

---

*File owner: `geoview_cpt/ags_convert/validator/`. Keep one numbered
gap entry per deviation — do not delete entries when we fix them,
mark them ``~~struck through~~`` with a commit SHA instead.*
