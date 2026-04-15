# Kingdom Drop — `09_kingdom/` Folder Layout (Recon)

> **Status:** Phase A-4 Week 16 reconnaissance draft. Used as input
> for Week 17–18 A4.4 implementation. References:
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

## Open questions for Week 17

1. **Kingdom `06_Kingdom` vs `09_kingdom` reconciliation.** Today the
   HandoverPackage profile uses `06_Kingdom` for the combined SBP /
   UHRS workflow. The CPT-side `09_kingdom/` is intentionally
   separate so the two pipelines don't fight over the folder. Final
   numbering decision lives with the package generator team — Week
   18 A4.4 will pick one. **Decision deadline:** Week 18 mid.
2. **Multi-sounding AGS bundling.** Does Kingdom prefer one `.ags`
   per sounding or one combined `.ags` with multiple LOCA rows? Week
   16 ships per-sounding; Week 17 should test the combined variant
   on a sandbox install.
3. **Checkshot file format.** Some Kingdom installs expect SEG-Y
   checkshot rather than CSV. The CSV variant is simpler; SEG-Y is
   on the v1.1 wishlist (Phase B).
4. **README content.** Week 18 A4.6 will draft the operator-facing
   README. Content should include: how to import into Kingdom, CRS
   note, expected curves, troubleshooting for the python-ags4
   round-trip TRAN_DLIM gap (Gap #1).

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
