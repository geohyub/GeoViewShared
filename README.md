# geoview-common

GeoView Shared Library - 전체 소프트웨어 포트폴리오 공유 패키지

## Modules

| Module | Description |
|--------|-------------|
| `styles/colors.py` | GeoView brand color palette |
| `styles/fonts.py` | Platform-aware font families |
| `styles/themes.py` | Light/Dark theme configurations |
| `reporting/design_system.py` | 19 document styles (Word/PPT/Excel) |
| `reporting/excel_writer.py` | Excel report engine with branding |
| `geo/crs.py` | Coordinate transforms, haversine, grid convergence |
| `segy/reader.py` | SEG-Y file reader (segyio wrapper) |
| `ctk_widgets/base_app.py` | CustomTkinter app base class |
| `ctk_widgets/styled_widgets.py` | Reusable UI components |
| `ctk_widgets/chart_frame.py` | Matplotlib chart frame for CTk |

## Install

```bash
# Editable install (recommended for development)
pip install -e ".[gui]"

# With all optional dependencies
pip install -e ".[gui,segy,docs,geo]"
```

## Used By

- GeoView Calculator Pro
- SeismicQC Suite (Phase 2)
- Calibration Pro (Phase 4)
- All future GeoView desktop apps

---

*Copyright (c) 2025-2026 Geoview Co., Ltd.*
