# AGS4 Rule 1-20 Matrix

Reference for :mod:`geoview_cpt.ags_convert.validator` (Phase A-3 Week 14
A3.3). Copied from the master plan §5.3 — consult `AGS4.1.pdf` December
2020 for the authoritative wording.

Columns:

- **Rule** — number from the AGS4 v4.1 specification
- **Title** — short description
- **Category** — structural / content / spec
- **Validator** — our wrapper module / class (``TBD`` = Week 14)
- **Implementation notes** — v1 scope, known python-ags4 delegation

| Rule | Title | Category | Validator | Notes |
|---:|---|---|---|---|
| 1 | File is ASCII / UTF-8 with no BOM | structural | `validator.Rule1_FileEncoding` | Delegate to python-ags4 `check_file` |
| 2 | Line-end is CRLF | structural | `validator.Rule2_LineEnd` | Load-time, not just validate — the writer must emit `\r\n` |
| 3 | Each line is one complete data row | structural | `validator.Rule3_OneRowPerLine` | python-ags4 handles |
| 4 | Each field is enclosed in double quotes | structural | `validator.Rule4_FieldQuoting` | python-ags4 handles |
| 5 | Each field is separated by a single comma | structural | `validator.Rule5_CommaSeparator` | python-ags4 handles |
| 6 | Double quotes inside fields are doubled | structural | `validator.Rule6_QuoteEscape` | python-ags4 handles |
| 7 | Each GROUP has a single `GROUP` descriptor line | structural | `validator.Rule7_GroupDescriptor` | python-ags4 handles |
| 8 | `HEADING`, `UNIT`, `TYPE`, `DATA` row order | structural | `validator.Rule8_RowOrder` | python-ags4 handles |
| 9 | Each HEADING matches the dictionary | content | `validator.Rule9_HeadingInDict` | Needs standard dictionary (bundled with python-ags4 v4.1.1) |
| 10a | Mandatory parent GROUPs present | content | `validator.Rule10a_MandatoryParents` | **Our wrapper re-implements** — master plan §5.3 calls this out |
| 10b | Unique rows in GROUP / KEY | content | `validator.Rule10b_UniqueKeys` | python-ags4 helper + our guard |
| 10c | Data type matches TYPE row | content | `validator.Rule10c_TypeCheck` | **Our wrapper re-implements** — tighter than python-ags4 |
| 11 | Numeric fields have leading zero | content | `validator.Rule11_NumericLeadingZero` | Writer-side |
| 12 | Dates in ISO format | content | `validator.Rule12_DateFormat` | Writer-side |
| 13 | `FILE` references are valid paths | content | `validator.Rule13_FileRef` | Skip for v1 — AGS4 writer doesn't emit FILE links |
| 14 | TRAN_DLIM / TRAN_RCON metadata present | content | `validator.Rule14_TranMetadata` | Writer inserts defaults |
| 15 | Character set respects UNIT row | content | `validator.Rule15_UnitCharset` | python-ags4 handles |
| 16 | GROUP name casing is UPPER | structural | `validator.Rule16_GroupCase` | python-ags4 handles |
| 17 | TYPE `DT` date fields use ISO-8601 | content | `validator.Rule17_DTIsoDate` | Writer-side |
| 18 | ABBR codes exist in ABBR group | content | `validator.Rule18_AbbrCodes` | **Week 14** — needs ABBR join |
| 19 | Numeric TYPE fields stay numeric | content | `validator.Rule19_NumericType` | python-ags4 handles |
| 20 | No trailing whitespace inside fields | content | `validator.Rule20_TrailingWhitespace` | python-ags4 handles |

## Implementation split

- **Delegated to python-ags4** (structural rules): 1, 3, 4, 5, 6, 7, 8,
  15, 16, 19, 20 — our validator just forwards the library's error
  report without re-parsing.
- **Our wrapper re-implements** (content rules): 9, 10a, 10b, 10c, 11,
  12, 14, 17, 18. These depend on the AGS4 dictionary and our canonical
  project model.
- **Writer-side** (enforced at dump time): 2, 11, 12, 14, 17. The
  writer is responsible for producing valid output in the first place.

## Validator entry point (Week 14 preview)

```python
from geoview_cpt.ags_convert import load_ags
from geoview_cpt.ags_convert.validator import validate_bundle

bundle = load_ags("survey.ags")
report = validate_bundle(bundle)          # → ValidationReport
for issue in report.issues:
    print(issue.rule, issue.severity, issue.description)
```

The validator is **not wired yet** — this file is the contract Week 14
(A3.3) fills in.

## Rule priority

Week 14 implementation order (from highest to lowest blocker impact):

1. Rule 10a / 10c / 10b (content integrity — blocks byte round-trip)
2. Rule 9 (heading dictionary lookup)
3. Rule 14 (TRAN metadata — writer side)
4. Rule 18 (ABBR join — requires dictionary ingestion)
5. Remaining rules via python-ags4 delegation

## Master plan cross-reference

See `plans/CPT_HARNESS_AND_SUITE_PLAN.md` §5.3 for the full matrix
with Wave 0 acceptance test mapping.
