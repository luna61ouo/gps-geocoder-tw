"""
query.py — Reverse geocoding queries against the local Japan map database.

Given (lat, lng), returns structured location info:
    {
        "city":     "台北市",
        "district": "大安區",
        "village":  "龍生里",
        "street":   "忠孝東路四段",
        "poi":      "捷運忠孝復興站",
        "summary":  "台北市大安區忠孝東路四段（捷運忠孝復興站附近）"
    }
"""

from __future__ import annotations

import math
import sqlite3
from pathlib import Path

from gps_geocoder import GEOCODER_DIR

DB_FILE = GEOCODER_DIR / "maps" / "japan.db"

# Search radii in degrees (approximate)
ADMIN_SEARCH_RADIUS = 0.05   # ~5 km
STREET_SEARCH_RADIUS = 0.005  # ~500 m
POI_SEARCH_RADIUS = 0.003     # ~300 m


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in meters between two points."""
    R = 6_371_000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_conn() -> sqlite3.Connection:
    if not DB_FILE.exists():
        from gps_geocoder.maps.jp.build import build_db
        import click
        click.echo("Japan map not found. Downloading and building (this may take several minutes)...")
        build_db()
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


def _find_admin(conn: sqlite3.Connection, lat: float, lng: float, level: int) -> str | None:
    """Find the closest administrative area at the specified level."""
    r = ADMIN_SEARCH_RADIUS
    rows = conn.execute(
        """
        SELECT a.name, a.lat, a.lng
        FROM admin_areas a
        JOIN admin_areas_rtree rt ON a.id = rt.id
        WHERE rt.min_lat <= ? AND rt.max_lat >= ?
          AND rt.min_lng <= ? AND rt.max_lng >= ?
          AND a.level = ?
        """,
        (lat + r, lat - r, lng + r, lng - r, level),
    ).fetchall()

    if not rows:
        return None

    best = min(rows, key=lambda row: _haversine(lat, lng, row["lat"], row["lng"]))
    return best["name"]


def _find_nearest_street(conn: sqlite3.Connection, lat: float, lng: float) -> tuple[str | None, float]:
    """Find the nearest named street. Returns (name, distance_meters)."""
    r = STREET_SEARCH_RADIUS
    rows = conn.execute(
        """
        SELECT s.name, s.lat, s.lng
        FROM streets s
        JOIN streets_rtree rt ON s.id = rt.id
        WHERE rt.min_lat <= ? AND rt.max_lat >= ?
          AND rt.min_lng <= ? AND rt.max_lng >= ?
        """,
        (lat + r, lat - r, lng + r, lng - r),
    ).fetchall()

    if not rows:
        return None, float("inf")

    best = min(rows, key=lambda row: _haversine(lat, lng, row["lat"], row["lng"]))
    dist = _haversine(lat, lng, best["lat"], best["lng"])
    return best["name"], dist


def _find_nearest_poi(conn: sqlite3.Connection, lat: float, lng: float) -> tuple[str | None, str | None, float]:
    """Find the nearest POI. Returns (name, category, distance_meters)."""
    r = POI_SEARCH_RADIUS
    rows = conn.execute(
        """
        SELECT p.name, p.category, p.subcategory, p.lat, p.lng
        FROM pois p
        JOIN pois_rtree rt ON p.id = rt.id
        WHERE rt.min_lat <= ? AND rt.max_lat >= ?
          AND rt.min_lng <= ? AND rt.max_lng >= ?
        """,
        (lat + r, lat - r, lng + r, lng - r),
    ).fetchall()

    if not rows:
        return None, None, float("inf")

    best = min(rows, key=lambda row: _haversine(lat, lng, row["lat"], row["lng"]))
    dist = _haversine(lat, lng, best["lat"], best["lng"])
    cat = best["subcategory"] or best["category"]
    return best["name"], cat, dist


ADDRESS_SEARCH_RADIUS = 0.002  # ~200 m


def _find_nearest_address(conn: sqlite3.Connection, lat: float, lng: float) -> tuple[str | None, float]:
    """Find the nearest address (street + housenumber). Returns (full_address, distance_meters)."""
    r = ADDRESS_SEARCH_RADIUS
    rows = conn.execute(
        """
        SELECT a.street, a.housenumber, a.lat, a.lng
        FROM addresses a
        JOIN addresses_rtree rt ON a.id = rt.id
        WHERE rt.min_lat <= ? AND rt.max_lat >= ?
          AND rt.min_lng <= ? AND rt.max_lng >= ?
        """,
        (lat + r, lat - r, lng + r, lng - r),
    ).fetchall()

    if not rows:
        return None, float("inf")

    best = min(rows, key=lambda row: _haversine(lat, lng, row["lat"], row["lng"]))
    dist = _haversine(lat, lng, best["lat"], best["lng"])
    return f"{best['street']}{best['housenumber']}", dist


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Reverse geocode a GPS coordinate to a Taiwan location.

    Returns:
        {
            "city":     str | None,
            "district": str | None,
            "village":  str | None,
            "street":   str | None,
            "street_distance_m": float,
            "poi":      str | None,
            "poi_category": str | None,
            "poi_distance_m": float,
            "summary":  str,
        }
    """
    conn = _get_conn()
    try:
        city = _find_admin(conn, lat, lng, 4) or _find_admin(conn, lat, lng, 5)
        district = _find_admin(conn, lat, lng, 7)
        village = _find_admin(conn, lat, lng, 8)
        street, street_dist = _find_nearest_street(conn, lat, lng)
        address, addr_dist = _find_nearest_address(conn, lat, lng)
        poi, poi_cat, poi_dist = _find_nearest_poi(conn, lat, lng)
    finally:
        conn.close()

    # Build summary string
    parts = []
    if city:
        parts.append(city)
    if district:
        parts.append(district)
    if village:
        parts.append(village)
    # Prefer exact address over street name
    if address and addr_dist < 100:
        parts.append(address)
    elif street and street_dist < 500:
        parts.append(street)

    summary = "".join(parts) if parts else f"{lat:.4f}, {lng:.4f}"

    if poi and poi_dist < 200:
        summary += f"（{poi}附近）"
    elif poi and poi_dist < 500:
        summary += f"（{poi}方向）"

    return {
        "city": city,
        "district": district,
        "village": village,
        "address": address if address and addr_dist < 100 else None,
        "address_distance_m": round(addr_dist, 1),
        "street": street if street and street_dist < 500 else None,
        "street_distance_m": round(street_dist, 1),
        "poi": poi if poi and poi_dist < 500 else None,
        "poi_category": poi_cat if poi and poi_dist < 500 else None,
        "poi_distance_m": round(poi_dist, 1),
        "summary": summary,
    }
