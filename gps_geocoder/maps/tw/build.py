"""
build.py — Download Taiwan OSM PBF and build the local geocoder database.

Data source: Geofabrik Taiwan extract (.osm.pbf), parsed with osmiter (pure Python)
Output: ~/.gps-geocoder-tw/taiwan_map.db (SQLite with R-tree spatial index)

Tables:
    admin_areas  — Administrative boundaries (city, district, village)
    streets      — Named streets/roads
    pois         — Points of interest (shops, stations, landmarks, etc.)
"""

from __future__ import annotations

import logging
import sqlite3
import sys
from pathlib import Path

import click
import requests

logger = logging.getLogger("gps_geocoder.maps.tw.build")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

from gps_geocoder import GEOCODER_DIR

MAPS_DIR = GEOCODER_DIR / "maps"
DB_FILE = MAPS_DIR / "taiwan.db"
PBF_FILE = MAPS_DIR / "taiwan-latest.osm.pbf"
GEOFABRIK_URL = "https://download.geofabrik.de/asia/taiwan-latest.osm.pbf"

ADMIN_LEVELS = {4, 6, 7, 8}

POI_TAG_KEYS = ["railway", "public_transport", "station", "amenity", "shop", "tourism", "historic", "leisure"]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download_pbf(force: bool = False) -> Path:
    """Download Taiwan OSM PBF from Geofabrik."""
    MAPS_DIR.mkdir(parents=True, exist_ok=True)
    if PBF_FILE.exists() and not force:
        size_mb = PBF_FILE.stat().st_size / (1024 * 1024)
        click.echo(f"PBF already exists: {PBF_FILE} ({size_mb:.0f} MB)")
        click.echo("Use --force to re-download.")
        return PBF_FILE

    click.echo(f"Downloading Taiwan OSM data (~200 MB)...")
    click.echo(f"  Source: {GEOFABRIK_URL}")

    resp = requests.get(GEOFABRIK_URL, stream=True, timeout=60)
    resp.raise_for_status()

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(PBF_FILE, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded * 100 // total
                mb = downloaded // (1024 * 1024)
                total_mb = total // (1024 * 1024)
                sys.stdout.write(f"\r  {mb}/{total_mb} MB ({pct}%)")
                sys.stdout.flush()

    click.echo(f"\n  Saved: {PBF_FILE}")
    return PBF_FILE


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS admin_areas (
            id      INTEGER PRIMARY KEY,
            level   INTEGER NOT NULL,
            name    TEXT    NOT NULL,
            name_en TEXT,
            lat     REAL    NOT NULL,
            lng     REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS streets (
            id      INTEGER PRIMARY KEY,
            name    TEXT    NOT NULL,
            name_en TEXT,
            lat     REAL    NOT NULL,
            lng     REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pois (
            id       INTEGER PRIMARY KEY,
            name     TEXT    NOT NULL,
            name_en  TEXT,
            category TEXT    NOT NULL,
            subcategory TEXT,
            lat      REAL   NOT NULL,
            lng      REAL   NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS admin_areas_rtree USING rtree(
            id, min_lat, max_lat, min_lng, max_lng
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS streets_rtree USING rtree(
            id, min_lat, max_lat, min_lng, max_lng
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS pois_rtree USING rtree(
            id, min_lat, max_lat, min_lng, max_lng
        );
    """)


# ---------------------------------------------------------------------------
# Parse PBF
# ---------------------------------------------------------------------------


def _extract_poi_category(tags: dict) -> tuple[str, str | None] | None:
    """Return (category, subcategory) if this is a POI we care about, else None."""
    for key in POI_TAG_KEYS:
        if key in tags:
            return key, tags[key]
    return None


def parse_and_build(pbf_path: Path, db_path: Path) -> None:
    """Parse the PBF file and populate the SQLite database."""
    import osmiter

    conn = sqlite3.connect(str(db_path))
    _create_schema(conn)

    admin_batch = []
    admin_rtree_batch = []
    street_batch = []
    street_rtree_batch = []
    poi_batch = []
    poi_rtree_batch = []

    node_count = 0
    way_count = 0
    rel_count = 0
    total_nodes = 0

    # Single pass: PBF is ordered node -> way -> relation.
    # osmiter uses "tag" (not "tags"), "nd" (not "refs"), "member" (not "members").
    # Admin relation members are mostly ways, so we also store way centers.
    click.echo("  Single-pass reading PBF (nodes -> ways -> relations)...")
    node_coords: dict[int, tuple[float, float]] = {}
    way_coords: dict[int, tuple[float, float]] = {}  # way center points
    total_ways = 0

    for entity in osmiter.iter_from_osm(str(pbf_path)):
        etype = entity["type"]
        tags = entity.get("tag", {})

        if etype == "node":
            lat = entity.get("lat")
            lon = entity.get("lon")
            if lat is not None and lon is not None:
                nid = entity["id"]
                node_coords[nid] = (lat, lon)
                total_nodes += 1

                if total_nodes % 5_000_000 == 0:
                    click.echo(f"    Nodes: {total_nodes:,}...")

                # Check if this node is a named POI
                name = tags.get("name")
                if name:
                    cat_info = _extract_poi_category(tags)
                    if cat_info:
                        category, subcategory = cat_info
                        poi_batch.append((nid, name, tags.get("name:en"), category, subcategory, lat, lon))
                        poi_rtree_batch.append((nid, lat, lat, lon, lon))
                        node_count += 1

        elif etype == "way":
            if total_nodes > 0 and total_ways == 0:
                click.echo(f"    Nodes done: {total_nodes:,} total, {node_count:,} POIs")

            refs = entity.get("nd", [])
            coords = [node_coords[r] for r in refs if r in node_coords]
            total_ways += 1

            if coords:
                # Store every way's center for admin boundary resolution
                mid = coords[len(coords) // 2]
                way_coords[entity["id"]] = mid

                # Streets: named highways
                if "highway" in tags and "name" in tags:
                    lats = [c[0] for c in coords]
                    lngs = [c[1] for c in coords]
                    wid = entity["id"]
                    name = tags["name"]
                    street_batch.append((wid, name, tags.get("name:en"), mid[0], mid[1]))
                    street_rtree_batch.append((wid, min(lats), max(lats), min(lngs), max(lngs)))
                    way_count += 1

                    if way_count % 50000 == 0:
                        click.echo(f"    Streets: {way_count:,}...")

            if total_ways % 500_000 == 0:
                click.echo(f"    Ways: {total_ways:,}...")

        elif etype == "relation":
            # Admin boundaries
            if tags.get("boundary") == "administrative":
                level_str = tags.get("admin_level", "")
                if level_str.isdigit() and int(level_str) in ADMIN_LEVELS:
                    name = tags.get("name")
                    if name:
                        members = entity.get("member", [])
                        member_coords = []
                        for m in members:
                            ref = m.get("ref")
                            if not ref:
                                continue
                            mtype = m.get("type", "")
                            if mtype == "node" and ref in node_coords:
                                member_coords.append(node_coords[ref])
                            elif mtype == "way" and ref in way_coords:
                                member_coords.append(way_coords[ref])

                        if member_coords:
                            avg_lat = sum(c[0] for c in member_coords) / len(member_coords)
                            avg_lng = sum(c[1] for c in member_coords) / len(member_coords)
                            level = int(level_str)
                            rid = entity["id"]
                            r = {4: 0.5, 6: 0.1, 7: 0.05, 8: 0.02}.get(level, 0.1)
                            admin_batch.append((rid, level, name, tags.get("name:en"), avg_lat, avg_lng))
                            admin_rtree_batch.append((rid, avg_lat - r, avg_lat + r, avg_lng - r, avg_lng + r))
                            rel_count += 1

    click.echo(f"    Ways done: {total_ways:,}, Streets: {way_count:,}, Admin areas: {rel_count:,}")

    # Free memory
    del node_coords
    del way_coords

    # Write to database
    click.echo("  Writing to database...")

    conn.executemany(
        "INSERT OR REPLACE INTO admin_areas (id, level, name, name_en, lat, lng) VALUES (?, ?, ?, ?, ?, ?)",
        admin_batch,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO admin_areas_rtree (id, min_lat, max_lat, min_lng, max_lng) VALUES (?, ?, ?, ?, ?)",
        admin_rtree_batch,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO streets (id, name, name_en, lat, lng) VALUES (?, ?, ?, ?, ?)",
        street_batch,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO streets_rtree (id, min_lat, max_lat, min_lng, max_lng) VALUES (?, ?, ?, ?, ?)",
        street_rtree_batch,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO pois (id, name, name_en, category, subcategory, lat, lng) VALUES (?, ?, ?, ?, ?, ?, ?)",
        poi_batch,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO pois_rtree (id, min_lat, max_lat, min_lng, max_lng) VALUES (?, ?, ?, ?, ?)",
        poi_rtree_batch,
    )

    conn.commit()

    admin_count = conn.execute("SELECT COUNT(*) FROM admin_areas").fetchone()[0]
    street_count = conn.execute("SELECT COUNT(*) FROM streets").fetchone()[0]
    poi_count = conn.execute("SELECT COUNT(*) FROM pois").fetchone()[0]
    conn.close()

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    click.echo(f"\n  Database: {db_path}")
    click.echo(f"  Size: {db_size_mb:.1f} MB")
    click.echo(f"  Admin areas: {admin_count:,}")
    click.echo(f"  Streets: {street_count:,}")
    click.echo(f"  POIs: {poi_count:,}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_db(force: bool = False) -> Path:
    """Download PBF and build the geocoder database. Returns DB path."""
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    if DB_FILE.exists() and not force:
        click.echo(f"Database already exists: {DB_FILE}")
        click.echo("Use --force to rebuild.")
        return DB_FILE

    # Download
    pbf_path = download_pbf(force=force)

    # Build
    if DB_FILE.exists():
        DB_FILE.unlink()

    click.echo("\nBuilding geocoder database (this may take a few minutes)...")
    parse_and_build(pbf_path, DB_FILE)

    return DB_FILE
