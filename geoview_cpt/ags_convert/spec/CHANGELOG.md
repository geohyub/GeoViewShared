# AGS4 Specification Change Log

This folder bundles the authoritative AGS4 specification and Rule 1-20
matrix used by :mod:`geoview_cpt.ags_convert` (Phase A-3, Week 12).
Update this file whenever a new spec version ships.

## Current version

| File | Version | Published | Size | SHA-256 |
|---|---|---|---|---|
| `AGS4.1.pdf` | AGS4 v4.1 | December 2020 | 7,408,484 bytes | `a91cf9d9ec5227130c736e2282eaff4f0944925d7a9a9ed8983e0762e5f80340` |

Source: <https://www.ags.org.uk/content/uploads/2020/12/AGS4-v-4.1-December-2020-1.pdf>
License: © Association of Geotechnical and Geoenvironmental Specialists
          (freely redistributable for tool integration per AGS website
          guidance — confirm before shipping in a commercial deliverable)

## Version history

- **2026-04-15 — Week 12 A3.6** initial commit of AGS4 v4.1 December
  2020 PDF + Rule 1-20 matrix (`rules_1_20.md`). No prior version
  archived; future CHANGELOG entries should note:
    - old → new version
    - what rules changed (adds/removes/modifies)
    - which tests need a fixture refresh
    - checksum bump

## Downstream consumers (Week 12 → Week 15)

| Consumer | File used | Epic |
|---|---|---|
| `ags_convert.wrapper.load_ags` | bundled python-ags4 dict (not the PDF) | A3.1 |
| `ags_convert.validator.Rule1 … Rule20` | `rules_1_20.md` | A3.3 (Week 14) |
| `geoview-ags check` CLI | `rules_1_20.md` | A3.5 (Week 15) |
| Wave 3 M3' byte round-trip | `AGS4.1.pdf` | A3.4 (Week 15) |

The PDF itself is not parsed programmatically — it's a reference for
humans reading the Rule table and for Week 14 validator commit
messages ("rule X section Y.Z of AGS4 v4.1 Dec 2020").

## Verification

```bash
# From _shared/ repo root:
python -c "import hashlib; print(hashlib.sha256(open('geoview_cpt/ags_convert/spec/AGS4.1.pdf','rb').read()).hexdigest())"
# expected: a91cf9d9ec5227130c736e2282eaff4f0944925d7a9a9ed8983e0762e5f80340
```
