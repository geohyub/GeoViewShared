# JAKO Korea CPT01 — AGS4 Missing Field Audit (Week 12)

R-new closure. Produced by
:func:`geoview_cpt.ags_convert.jako_audit.audit_missing_fields` against
the JAKO CPT01 vendor bundle parsed by
:func:`geoview_cpt.parsers.cpt_text_bundle.parse_cdf_bundle`. Week 13
(A3.2 writer) consumes this list to decide which HEADINGs to
synthesize, which to prompt for user override, and which can be
omitted.

## Summary

| GROUP | Populated | Missing | Status |
|---|---:|---:|---|
| PROJ | 3 | 4 | ⚠️ `PROJ_ID` / `PROJ_LOC` / `PROJ_ENG` / `PROJ_MEMO` |
| LOCA | 2 | 10 | ❗ `LOCA_NATE` / `LOCA_NATN` not in vendor export |
| SCPG | 3 | 6 | ⚠️ `SCPG_CREW` / `SCPG_TESN` / `SCPG_DTIM` not in vendor export |
| SCPT | 7 | 1 | ✅ raw + derived channels all present |
| SCPP | 3 | 5 | ⚠️ `SCPP_COH` / `SCPP_PHI` / `SCPP_DEN` — derivation pending |

## PROJ

Populated by parser: `PROJ_NAME`, `PROJ_CLNT`, `PROJ_CONT`.

Missing — Week 13 writer must inject:

- **`PROJ_ID`** — JAKO bundles carry the vendor push name (`CPT01`)
  but no project-level ID. Writer policy: synthesize from
  `sounding.header.project_name + "-" + borehole_id` or prompt the
  operator.
- **`PROJ_LOC`** — GPS/address descriptor. Not in the vendor text
  bundle; populate from user input or from the CPeT-IT ``<Various>/<Location>``
  block when the same project carries a ``.cpt`` artefact.
- **`PROJ_ENG`** — responsible engineer. Operator override only.
- **`PROJ_MEMO`** — free-form notes. Leave blank.

## LOCA

Populated by parser: `LOCA_ID`, `LOCA_GL` (via `water_depth_m`).

Missing:

- **`LOCA_NATE` / `LOCA_NATN`** — CRS-projected coordinates. JAKO
  export records these in the CPeT-IT ``<CPTProperties>`` block as
  `XCoord1` / `YCoord1` (all zero for JAKO CPT01 since the operator
  left them blank). **Writer: read from CPeT-IT ``CPTProject`` when
  available, else require user override.**
- **`LOCA_GREF`** — CRS identifier string. Defaults to "UTM 52N
  (EPSG:32652)" for JAKO Korea unless overridden.
- **`LOCA_TYPE` / `LOCA_STAT`** — free-form labels. Default to
  "Marine CPT" / "Completed".
- **`LOCA_FDEP` / `LOCA_ENDD`** — final depth + end date. Derive from
  the sounding's max depth and the last `.CLog` timestamp.
- **`LOCA_CLNT` / `LOCA_PURP`** — mirror PROJ counterparts.

## SCPG

Populated by parser: `LOCA_ID`, `SCPG_CARD` (cone base area 200 mm²),
`SCPG_CAR` (area ratio 0.7032), `SCPG_TYPE` (WISON-APB).

Missing:

- **`SCPG_CREW`** — push crew names. Not in any vendor file. **User
  override prompt.**
- **`SCPG_TESN`** — test number sequence. Synthesize from the vendor
  push name suffix (`CPT010001` → `1`).
- **`SCPG_TESD` / `SCPG_TESM`** — test date / method code. `TESD`
  from the Deck Baseline timestamp; `TESM` defaults to "UUS" (usually
  undrained static).
- **`SCPG_DTIM`** — total duration (s). Compute from Deck→Post
  Baseline timestamps on the event list.
- **`SCPG_FARD`** — friction sleeve area. JAKO does not record this
  separately; default 150 cm² or prompt.

## SCPT

Populated by parser + derivation:

- `LOCA_ID`, `SCPT_DPTH`, `SCPT_RES` (qc), `SCPT_FRES` (fs),
  `SCPT_PWP2` (u₂), `SCPT_QT` (corrected qt), `SCPT_FR`
  (friction ratio), **all** after the derivation chain runs.

Missing:

- **`SCPT_TESN`** — test number. Mirror `SCPG_TESN`.

SCPT is the cleanest group — the writer can emit it without prompting
once the derivation chain has run.

## SCPP

Populated: `LOCA_ID`, `SCPP_DPTH`, `SCPP_IC` (after Qtn iterative).

Missing:

- **`SCPP_TESN`** — mirror `SCPG_TESN`.
- **`SCPP_COH`** — cohesion intercept c'. Not derivable from CPT
  alone; pull from lab `LabSample.effective_cohesion_kpa` when
  available or leave blank.
- **`SCPP_PHI`** — effective friction angle φ'. Same story — lab
  sample `effective_friction_angle_deg` or blank.
- **`SCPP_DEN`** — dry density γd. From density log
  (`DensityLog.density_g_cm3` × 0.981) or blank.
- **`SCPP_REM`** — remarks. Free-form; leave blank.

Note: `SCPP_NKT` is populated from the CPeT-IT Various block default
(Nkt = 15 / 30 Wave 0 pair). The writer should emit one row per Nkt
if both are requested, or a single row with the Wave 0 default.

## Notes

- JAKO vendor bundle lacks `PROJ_ID` / `LOCA_GREF` / `SCPG_CREW`.
  Week 13 writer must either prompt the user, accept a config
  override file, or inject documented sentinel values.
- `SCPT` derived columns (`QT`, `FR`, `BQ`) populate only after the
  derivation chain (`geoview_cpt.correction` + `geoview_cpt.derivation`)
  runs. The writer must assert the chain has been executed or run it
  itself.
- `SCPP_IC` uses the Robertson 2009 iterative Ic (Q36b). Writer must
  not accept Qt1-based Ic as `SCPP_IC`.
- Coordinates (`LOCA_NATE / NATN`) are the biggest gap — JAKO CPT01
  ships zeros. Week 13 writer should either refuse to emit LOCA when
  coordinates are zero/missing, or tag the row with `LOCA_STAT =
  "coordinates pending"`.

## Audit regeneration

```python
from geoview_cpt.ags_convert.jako_audit import audit_missing_fields
from geoview_cpt.parsers.cpt_text_bundle import parse_cdf_bundle
# (plus the derivation chain from M3 demo)

sounding = parse_cdf_bundle("H:/자코/.../CPT01/CPT010001.cdf")
# ... run derivation chain ...
report = audit_missing_fields(sounding)
print(report.as_markdown())
```

Regenerate this file whenever the canonical CPTSounding shape or the
`AGS4_CORE_GROUPS` list in `jako_audit.py` changes.
