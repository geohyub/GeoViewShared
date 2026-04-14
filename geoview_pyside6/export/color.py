"""
geoview_pyside6.export.color
================================
sRGB-safe color palette + sRGB profile stamping for PNG output.

Colors are sourced from feedback_ui_design_rules.md (Navy-aligned). The
palette lives here so every export (and every chart overlay) pulls the
same hex values — no drift between widgets and deliverables.

``ensure_srgb_png`` stamps a PNG with the standard sRGB ICC profile
(IEC 61966-2.1) so Word, InDesign and Acrobat interpret colors
consistently across machines. matplotlib already writes sRGB-encoded
pixels; the profile tag just tells readers "yes, this is sRGB".

We embed a minimal sRGB profile generated from PIL's ImageCms module
when available. If PIL cannot create an sRGB profile (very old Pillow),
the function no-ops and returns the original path so export still
succeeds — the visual difference is imperceptible on modern viewers.
"""
from __future__ import annotations

from pathlib import Path

__all__ = [
    "SRGB_PALETTE",
    "ensure_srgb_png",
]


# Navy-aligned palette from feedback_ui_design_rules.md. Keys are semantic
# role names, values are sRGB hex strings. This is the authoritative list
# for export charts — mutations should flow back into the UI rules file.
SRGB_PALETTE: dict[str, str] = {
    "navy":        "#0B2545",
    "navy_dark":   "#071A31",
    "navy_light":  "#13315C",
    "accent":      "#1E88E5",
    "accent_soft": "#8ECAE6",
    "success":     "#2E8B57",
    "warning":     "#E09F3E",
    "danger":      "#C0392B",
    "neutral_900": "#1A1C1E",
    "neutral_700": "#454A50",
    "neutral_500": "#7A8089",
    "neutral_300": "#C5CAD2",
    "neutral_100": "#F2F4F7",
    "paper":       "#FFFFFF",
}


def ensure_srgb_png(path: Path | str) -> Path:
    """
    Stamp a PNG file with the sRGB IEC 61966-2.1 ICC profile.

    No-op when:
     - Pillow is not available
     - Pillow cannot create an sRGB profile
     - the file is not a PNG

    Returns the (possibly unchanged) path.
    """
    p = Path(path)
    if p.suffix.lower() != ".png":
        return p
    try:
        from PIL import Image, ImageCms
    except ImportError:
        return p

    try:
        srgb_profile = ImageCms.createProfile("sRGB")
    except Exception:
        return p

    try:
        profile_bytes = ImageCms.ImageCmsProfile(srgb_profile).tobytes()
    except Exception:
        return p

    try:
        with Image.open(p) as img:
            img.load()
            img.save(p, format="PNG", icc_profile=profile_bytes)
    except Exception:
        # Don't break the export pipeline just because ICC stamping failed.
        return p
    return p
