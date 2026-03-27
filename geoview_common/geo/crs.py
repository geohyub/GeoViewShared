"""
GeoView CRS Utilities
=====================
Coordinate Reference System transformations using pyproj.
Shared by P190_NavConverter, CoordConverter, and Calculator tools.
"""

import math
from typing import Tuple, Optional


def dd_to_dms(dd: float) -> Tuple[int, int, float]:
    """Decimal degrees → Degrees, Minutes, Seconds."""
    negative = dd < 0
    dd = abs(dd)
    d = int(dd)
    m = int((dd - d) * 60)
    s = (dd - d - m / 60) * 3600
    if negative:
        d = -d
    return d, m, s


def dd_to_dmm(dd: float) -> Tuple[int, float]:
    """Decimal degrees → Degrees, Decimal Minutes."""
    negative = dd < 0
    dd = abs(dd)
    d = int(dd)
    m = (dd - d) * 60
    if negative:
        d = -d
    return d, m


def dms_to_dd(d: int, m: int, s: float) -> float:
    """Degrees, Minutes, Seconds → Decimal degrees."""
    sign = -1 if d < 0 else 1
    return sign * (abs(d) + m / 60 + s / 3600)


def format_dms(dd: float, is_lat: bool = True) -> str:
    """Format decimal degrees as DMS string."""
    d, m, s = dd_to_dms(dd)
    direction = ""
    if is_lat:
        direction = "N" if dd >= 0 else "S"
    else:
        direction = "E" if dd >= 0 else "W"
    return f"{abs(d):d}\u00b0 {m:02d}' {s:08.5f}\" {direction}"


def format_dmm(dd: float, is_lat: bool = True) -> str:
    """Format decimal degrees as DMM string."""
    d, m = dd_to_dmm(dd)
    direction = ""
    if is_lat:
        direction = "N" if dd >= 0 else "S"
    else:
        direction = "E" if dd >= 0 else "W"
    return f"{abs(d):d}\u00b0 {m:09.6f}' {direction}"


def haversine(lat1: float, lon1: float,
              lat2: float, lon2: float) -> Tuple[float, float]:
    """
    Calculate distance (meters) and bearing (degrees) between two points.

    Parameters:
        lat1, lon1, lat2, lon2: Coordinates in decimal degrees

    Returns:
        (distance_m, bearing_deg)
    """
    R = 6371000.0  # Earth radius in meters

    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    y = math.sin(dlon) * math.cos(lat2_r)
    x = (math.cos(lat1_r) * math.sin(lat2_r) -
         math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon))
    bearing = math.degrees(math.atan2(y, x))
    bearing = (bearing + 360) % 360

    return distance, bearing


def calculate_endpoint(lat: float, lon: float,
                       bearing_deg: float, distance_m: float
                       ) -> Tuple[float, float, float]:
    """
    Calculate destination point from start, bearing, and distance.

    Returns:
        (lat2, lon2, reverse_bearing)
    """
    R = 6371000.0
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    brg_r = math.radians(bearing_deg)
    d_R = distance_m / R

    lat2 = math.asin(
        math.sin(lat_r) * math.cos(d_R) +
        math.cos(lat_r) * math.sin(d_R) * math.cos(brg_r)
    )
    lon2 = lon_r + math.atan2(
        math.sin(brg_r) * math.sin(d_R) * math.cos(lat_r),
        math.cos(d_R) - math.sin(lat_r) * math.sin(lat2)
    )

    lat2_deg = math.degrees(lat2)
    lon2_deg = math.degrees(lon2)

    _, rev_bearing = haversine(lat2_deg, lon2_deg, lat, lon)

    return lat2_deg, lon2_deg, rev_bearing


def utm_zone(lon: float) -> int:
    """Get UTM zone number from longitude."""
    return int((lon + 180) / 6) + 1


def grid_convergence(lat: float, lon: float) -> dict:
    """
    Calculate UTM grid convergence angle and scale factor.

    Returns:
        {"zone": int, "convergence_deg": float, "scale_factor": float}
    """
    zone = utm_zone(lon)
    central_meridian = (zone - 1) * 6 - 180 + 3
    dlon = lon - central_meridian

    lat_r = math.radians(lat)
    dlon_r = math.radians(dlon)

    convergence = dlon_r * math.sin(lat_r)
    convergence_deg = math.degrees(convergence)

    # Approximate scale factor
    k0 = 0.9996
    cos_lat = math.cos(lat_r)
    scale = k0 * (1 + (dlon_r * cos_lat) ** 2 / 2)

    return {
        "zone": zone,
        "convergence_deg": convergence_deg,
        "scale_factor": scale,
        "central_meridian": central_meridian,
    }


def polygon_area_shoelace(coords: list) -> Tuple[float, float, int]:
    """
    Calculate polygon area and perimeter using Shoelace formula.

    Parameters:
        coords: List of (lat, lon) tuples in decimal degrees

    Returns:
        (area_m2, perimeter_m, num_vertices)
    """
    n = len(coords)
    if n < 3:
        return 0.0, 0.0, n

    # Convert to approximate meters using first point as reference
    ref_lat = coords[0][0]
    m_per_deg_lat = 111132.92
    m_per_deg_lon = 111132.92 * math.cos(math.radians(ref_lat))

    xy = []
    for lat, lon in coords:
        x = (lon - coords[0][1]) * m_per_deg_lon
        y = (lat - coords[0][0]) * m_per_deg_lat
        xy.append((x, y))

    # Shoelace formula
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += xy[i][0] * xy[j][1]
        area -= xy[j][0] * xy[i][1]
    area = abs(area) / 2.0

    # Perimeter
    perimeter = 0.0
    for i in range(n):
        j = (i + 1) % n
        dist, _ = haversine(coords[i][0], coords[i][1],
                            coords[j][0], coords[j][1])
        perimeter += dist

    return area, perimeter, n


def validate_geographic_coords(lat: float, lon: float) -> bool:
    """Check if coordinates are valid geographic."""
    return -90 <= lat <= 90 and -180 <= lon <= 180
