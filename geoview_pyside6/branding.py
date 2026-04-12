"""GeoView app branding presets for icons and splash screens."""

from __future__ import annotations

from dataclasses import dataclass, replace

from geoview_pyside6.constants import Category, CATEGORY_THEMES


@dataclass(frozen=True)
class AppBranding:
    primary: str
    secondary: str
    icon_name: str
    badge_icon: str
    tagline: str
    features: tuple[str, ...]


_CATEGORY_DEFAULTS: dict[Category, AppBranding] = {
    Category.QC: AppBranding(
        primary="#3B82F6",
        secondary="#DBEAFE",
        icon_name="check-circle",
        badge_icon="star",
        tagline="Quality control workspace",
        features=("Review", "Analyze", "Export"),
    ),
    Category.PROCESSING: AppBranding(
        primary="#2563EB",
        secondary="#DBEAFE",
        icon_name="settings",
        badge_icon="activity",
        tagline="Processing workspace",
        features=("Prepare", "Process", "Deliver"),
    ),
    Category.PREPROCESSING: AppBranding(
        primary="#F59E0B",
        secondary="#FEF3C7",
        icon_name="shuffle",
        badge_icon="filter",
        tagline="Preprocessing workspace",
        features=("Clean", "Arrange", "Stage"),
    ),
    Category.MANAGEMENT: AppBranding(
        primary="#4C6A92",
        secondary="#E2EAF5",
        icon_name="layout-dashboard",
        badge_icon="check-square",
        tagline="Management workspace",
        features=("Track", "Coordinate", "Report"),
    ),
    Category.VALIDATION: AppBranding(
        primary="#0F766E",
        secondary="#D7F3EC",
        icon_name="search",
        badge_icon="check-square",
        tagline="Validation workspace",
        features=("Verify", "Compare", "Sign off"),
    ),
    Category.UTILITIES: AppBranding(
        primary="#64748B",
        secondary="#E2E8F0",
        icon_name="star",
        badge_icon="settings",
        tagline="Utility workspace",
        features=("Inspect", "Assist", "Automate"),
    ),
    Category.AI: AppBranding(
        primary="#EC4899",
        secondary="#FCE7F3",
        icon_name="activity",
        badge_icon="zap",
        tagline="AI workspace",
        features=("Detect", "Assist", "Accelerate"),
    ),
}


_APP_BRANDS: dict[str, AppBranding] = {
    "MagQC": AppBranding(
        primary="#B86A3E",
        secondary="#EED7C9",
        icon_name="magnet",
        badge_icon="line-chart",
        tagline="Magnetic line quality cockpit",
        features=("Mag map", "GPS match", "Story export"),
    ),
    "SonarQC": AppBranding(
        primary="#147D8A",
        secondary="#D9F1F4",
        icon_name="waves",
        badge_icon="radar",
        tagline="Sidescan route and image review",
        features=("Waterfall", "Route map", "Mosaic"),
    ),
    "SeismicQC": AppBranding(
        primary="#C7771D",
        secondary="#F7E2C6",
        icon_name="activity",
        badge_icon="scan-line",
        tagline="Seismic trace diagnostics and DQR",
        features=("SEG-Y", "SNR", "Anomaly"),
    ),
    "MBESQC": AppBranding(
        primary="#2563EB",
        secondary="#DCE8FF",
        icon_name="layers",
        badge_icon="grid-3x3",
        tagline="Bathymetry, swath, and DQR control",
        features=("Swath QC", "3D bathy", "Crossline"),
    ),
    "NavQC": AppBranding(
        primary="#0F766E",
        secondary="#D7F1EC",
        icon_name="navigation",
        badge_icon="anchor",
        tagline="Navigation standards and export cockpit",
        features=("Track", "Standards", "P-format"),
    ),
    "QCHub": AppBranding(
        primary="#4C6A92",
        secondary="#E2EAF5",
        icon_name="layout-dashboard",
        badge_icon="check-square",
        tagline="Portfolio health and workflow hub",
        features=("Health", "QC items", "Sync"),
    ),
}


def get_app_branding(
    app_name: str,
    category: Category,
    *,
    primary: str | None = None,
    secondary: str | None = None,
    icon_name: str | None = None,
    badge_icon: str | None = None,
    tagline: str | None = None,
    features: tuple[str, ...] | list[str] | None = None,
) -> AppBranding:
    """Return a stable branding bundle for an app."""
    spec = _APP_BRANDS.get(app_name, _CATEGORY_DEFAULTS.get(category))
    if spec is None:
        theme = CATEGORY_THEMES[Category.PROCESSING]
        spec = AppBranding(
            primary=theme.accent,
            secondary="#E5E7EB",
            icon_name="star",
            badge_icon="star",
            tagline=f"{app_name} workspace",
            features=("Open", "Review", "Export"),
        )
    updates = {}
    if primary:
        updates["primary"] = primary
    if secondary:
        updates["secondary"] = secondary
    if icon_name:
        updates["icon_name"] = icon_name
    if badge_icon:
        updates["badge_icon"] = badge_icon
    if tagline:
        updates["tagline"] = tagline
    if features:
        updates["features"] = tuple(features)
    return replace(spec, **updates) if updates else spec
