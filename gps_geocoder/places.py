"""
places.py — Personal place markers (import from Google Takeout, query, search).

Storage: ~/.gps-geocoder/places.db (SQLite)

Supports two Google Takeout formats:
    - Labeled places: properties.name + properties.address
    - Saved places: properties.location.name + properties.location.address
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

from gps_geocoder import GEOCODER_DIR

PLACES_DB = GEOCODER_DIR / "places.db"


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return distance in meters between two points."""
    R = 6_371_000
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _get_conn() -> sqlite3.Connection:
    GEOCODER_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(PLACES_DB))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            owner    TEXT NOT NULL DEFAULT '',
            name     TEXT NOT NULL,
            lat      REAL NOT NULL,
            lng      REAL NOT NULL,
            address  TEXT,
            category TEXT,
            source   TEXT DEFAULT 'google',
            date     TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_places_owner ON places(owner)
    """)
    conn.commit()
    return conn


def import_google_takeout(filepath: str, owner: str = "") -> int:
    """
    Import places from a Google Takeout GeoJSON file.
    Handles both labeled places and saved places formats.
    Returns the number of places imported.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    features = data.get("features", [])
    conn = _get_conn()
    count = 0

    for feat in features:
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])
        lng, lat = coords[0], coords[1]

        # Skip invalid coordinates
        if lat == 0 and lng == 0:
            continue

        props = feat.get("properties", {})

        # Detect format: labeled vs saved
        if "location" in props:
            # Saved places format
            loc = props["location"]
            name = loc.get("name", "")
            address = loc.get("address", "")
            category = "saved"
            date = props.get("date")
        else:
            # Labeled places format
            name = props.get("name", "")
            address = props.get("address", "")
            category = "labeled"
            date = props.get("date")

        if not name:
            continue

        # Check for duplicates (same owner + name + similar coordinates)
        existing = conn.execute(
            "SELECT id FROM places WHERE owner = ? AND name = ? AND ABS(lat - ?) < 0.0001 AND ABS(lng - ?) < 0.0001",
            (owner, name, lat, lng),
        ).fetchone()
        if existing:
            continue

        conn.execute(
            "INSERT INTO places (owner, name, lat, lng, address, category, source, date) VALUES (?, ?, ?, ?, ?, ?, 'google', ?)",
            (owner, name, lat, lng, address, category, date),
        )
        count += 1

    conn.commit()
    conn.close()
    return count


def list_places(owner: str | None = None, category: str | None = None) -> list[dict]:
    """List all places, optionally filtered by owner and/or category."""
    conn = _get_conn()
    query = "SELECT * FROM places WHERE 1=1"
    params: list = []
    if owner is not None:
        query += " AND owner = ?"
        params.append(owner)
    if category is not None:
        query += " AND category = ?"
        params.append(category)
    query += " ORDER BY name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def search_places(keyword: str, owner: str | None = None) -> list[dict]:
    """Search places by name (partial match)."""
    conn = _get_conn()
    query = "SELECT * FROM places WHERE name LIKE ?"
    params: list = [f"%{keyword}%"]
    if owner is not None:
        query += " AND owner = ?"
        params.append(owner)
    query += " ORDER BY name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_nearest_place(lat: float, lng: float, radius_m: float = 500, owner: str | None = None) -> dict | None:
    """Find the nearest place within radius_m meters."""
    # Rough degree filter (~radius in degrees)
    r_deg = radius_m / 111_000
    conn = _get_conn()
    query = "SELECT * FROM places WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?"
    params: list = [lat - r_deg, lat + r_deg, lng - r_deg, lng + r_deg]
    if owner is not None:
        query += " AND owner = ?"
        params.append(owner)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return None

    best = None
    best_dist = float("inf")
    for row in rows:
        dist = _haversine(lat, lng, row["lat"], row["lng"])
        if dist < best_dist and dist <= radius_m:
            best = dict(row)
            best_dist = dist

    if best:
        best["distance_m"] = round(best_dist, 1)
    return best


def near_places(lat: float, lng: float, radius_m: float = 1000, owner: str | None = None, limit: int = 20) -> list[dict]:
    """Find all places within radius_m meters, sorted by distance."""
    r_deg = radius_m / 111_000
    conn = _get_conn()
    query = "SELECT * FROM places WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?"
    params: list = [lat - r_deg, lat + r_deg, lng - r_deg, lng + r_deg]
    if owner is not None:
        query += " AND owner = ?"
        params.append(owner)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = []
    for row in rows:
        dist = _haversine(lat, lng, row["lat"], row["lng"])
        if dist <= radius_m:
            entry = dict(row)
            entry["distance_m"] = round(dist, 1)
            results.append(entry)

    results.sort(key=lambda x: x["distance_m"])
    return results[:limit]
