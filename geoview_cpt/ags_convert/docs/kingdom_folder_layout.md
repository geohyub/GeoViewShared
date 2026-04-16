# Kingdom Drop — `09_kingdom/` Folder Layout

> **Status:** Phase A-4 Week 18 — **COMPLETE**. Originally a Week 16
> reconnaissance draft; Week 17 closed Q40-Q43 and Week 18 delivered
> the assembly / manifest / README / atomic-drop helpers + M4 gate.
> Layout implemented verbatim. References:
> - `Management/HandoverPackageGenerator/profiles/generated/KFW_2026_OfECC_Geophysical.yaml`
>   (lines 177 / 232 / 299–303 — `06_Kingdom` placeholder for SBP+UHRS)
> - `plans/CPT_HARNESS_AND_SUITE_PLAN.md` §5.4 Phase A-4
> - `docs/a3_jako_missing_fields.md` (Week 12 audit)

The HandoverPackage profile currently treats `06_Kingdom` as the
*combined* SBP+UHRS interpretation drop. **Phase A-4 introduces a
distinct `09_kingdom/`** owned by the CPT pipeline so the two
workflows do not collide on the same folder. The numbering is
provisional — Week 18 A4.4 will reconcile it with the final
`KFW_2026_*.yaml` revision before Phase A termination.

## Top-level layout (Week 18 A4.4 target)

```
09_kingdom/
├── manifest.yaml              # Week 18 A4.5 — drop summary + checksums
├── AGS/                       # Week 16 A4.0 — Kingdom-subset .ags files
│   ├── <project>_<sounding>.ags
│   └── ...                    # one .ags per sounding
├── LAS/                       # Week 17 A4.1 — depth-domain LAS curves
│   ├── <sounding>.las
│   └── ...
├── checkshot/                 # Week 17 A4.2 — Vp/Vs checkshot CSVs
│   ├── <sounding>_vp.csv
│   ├── <sounding>_vs.csv
│   └── ...
├── location/                  # Week 17 A4.3 — Kingdom-style location CSV
│   └── locations.csv
└── README.md                  # Week 18 A4.6 — drop instructions
```

## Naming conventions

| Slot | Pattern | Source |
| --- | --- | --- |
| `AGS/*.ags` | `<project>_<sounding_id>.ags` | `geoview_cpt.ags_convert.kingdom.write_kingdom_ags` |
| `LAS/*.las` | `<sounding_id>.las` | A4.1 (lasio writer) |
| `checkshot/*.csv` | `<sounding_id>_<vp|vs>.csv` | A4.2 |
| `location/locations.csv` | single file | A4.3 |
| `manifest.yaml` | single file | A4.5 |

`<project>` is the `PROJ_ID` value injected via
`on_missing='inject_default'` from the per-project YAML — for the
JAKO benchmark that is `JAKO-2025`.

## Per-format scope

### `AGS/` — Week 16 A4.0 (this Epic)

- One Kingdom-subset `.ags` per sounding (no multi-sounding files).
- Generated from the A-3 writer output via
  `build_kingdom_subset(load_ags(...))`.
- Groups: `PROJ`, `TRAN`, `UNIT`, `TYPE`, `LOCA`, `SCPG`, `SCPT`,
  `SCPP`, `GEOL` (per `kingdom.subset.KINGDOM_GROUPS`).
- LOCA_GREF stamped to the Kingdom CRS (EPSG:5179 / 4326 default).
- Rule 1–20 validator must pass with **zero** ERROR severity issues.

### `LAS/` — Week 17 A4.1

- Optional but recommended; consumed by Kingdom's well-log overlay.
- Depth-domain LAS 2.0, one curve set per sounding (DEPT + qc + fs +
  u₂ + qt + Fr + Bq + Ic).
- Reuses `geoview_cpt.ags_convert.converters.las_fmt.to_las` with a
  Kingdom-flavoured header (TYPE = `CPT`, COMP = `<PROJ_CLNT>`,
  WELL = `<LOCA_ID>`).
- LAS dependency stays optional (`pip install geoview-common[las]`).

### `checkshot/` — Week 17 A4.2

- Two CSVs per sounding when checkshot data is available:
  `<sounding>_vp.csv` (P-wave) and `<sounding>_vs.csv` (S-wave).
- Schema: `Depth_m,TWT_ms,Velocity_m_per_s,Quality`.
- Skipped (no file emitted) when the A-2 sounding lacks Vp/Vs
  channels — Kingdom tolerates missing curves.

### `location/locations.csv` — Week 17 A4.3

- Single CSV listing every sounding in the drop with columns
  `sounding_id,easting,northing,crs,water_depth_m,seafloor_elev_m`.
- Pulled from each sounding's `CPTHeader` and stamped with the same
  CRS as the Kingdom AGS subset.
- Used by Kingdom to plot the survey grid before users open the
  individual `.ags` files.

### `manifest.yaml` — Week 18 A4.5

Week 18 design — outline only:

```yaml
schema_version: "1.0"
project_id: JAKO-2025
crs: EPSG:5179
generated_at: 2025-10-15T12:34:56Z
soundings:
  - id: CPT01
    ags: AGS/JAKO-2025_CPT01.ags
    las: LAS/CPT01.las
    checkshot:
      vp: checkshot/CPT01_vp.csv
      vs: checkshot/CPT01_vs.csv
    sha256:
      ags: <sha>
      las: <sha>
locations: location/locations.csv
```

The manifest closes A4.5 and feeds the M4 gate.

## Resolved questions (Week 17 decisions)

1. **✅ Q40 — `06_Kingdom` vs `09_kingdom` reconciliation.**
   Decision: **keep them separate.** `06_Kingdom` remains the
   SBP / UHRS combined drop owned by the geophysics team and
   defined in `KFW_2026_OfECC_Geophysical.yaml`. `09_kingdom/` is
   the CPT-side drop owned by this package. The Week 18 manifest
   makes the split explicit so operators don't conflate the two
   workflows.
2. **✅ Q41 — multi-sounding AGS bundling.**
   Decision: **hybrid.** Each sounding gets its own
   `09_kingdom/AGS/<project>_<sounding>.ags` (Kingdom's per-well
   convention) **plus** a single `09_kingdom/location/project_locations.csv`
   that lists every sounding for the survey-grid plot. Per-sounding
   is the import unit; the location CSV is the cross-sounding
   index.
3. **✅ Q42 — checkshot file format.**
   Decision: **CSV** (Kingdom's standard import).
   `Depth_m` and `TWT_ms` are mandatory; `Interval_Vs_m_s`,
   `Average_Vs_m_s`, `Source_Offset_m`, `Quality_Flag` are
   recommended. The first line carries a `# CRS:` comment that
   Kingdom's parser ignores. SEG-Y checkshot stays on the v1.1
   wishlist.
4. **✅ Q43 — README content (Week 18 A4.6 outline).**
   The README will list: project ID, generation timestamp, source
   AGS4 spec version, CPT sounding count, checkshot count,
   Kingdom CRS, the four 09_kingdom subdirectories with one-line
   descriptions, and a troubleshooting section pointing at
   `python_ags4_gaps.md` Gap #1 (TRAN_DLIM idempotency caveat).
   Generated alongside the manifest in A4.5/A4.6.

## Reference flow (Phase A-4 end-to-end)

```
A-2 parse_jako_xls
        │
        ▼
CPTSounding (with strata)
        │
        ▼
A-3 write_ags(on_missing='inject_default') ──► full .ags
        │                                           │
        │                                           ▼
        │                              load_ags + build_kingdom_subset
        │                                           │
        │                                           ▼
        │                                  09_kingdom/AGS/*.ags  (Week 16)
        │
        ▼
to_las  ─────────────────────────────────► 09_kingdom/LAS/*.las  (Week 17)
to_checkshot_csv ─────────────────────────► 09_kingdom/checkshot/  (Week 17)
to_location_csv  ─────────────────────────► 09_kingdom/location/   (Week 17)
build_manifest ──────────────────────────► 09_kingdom/manifest.yaml (Week 18)

──► M4 gate (Phase A termination — Week 18)
```
