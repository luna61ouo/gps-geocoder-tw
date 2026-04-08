"""
registry.py — Discover and manage installed map plugins.

Each map plugin lives under gps_geocoder/maps/<id>/ and provides:
    - build.py  with build_db(force=False) -> Path
    - query.py  with reverse_geocode(lat, lng) -> dict
    - __init__.py with MAP_ID, MAP_NAME
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from gps_geocoder import GEOCODER_DIR

MAPS_DIR = GEOCODER_DIR / "maps"


def _discover_map_modules() -> dict[str, object]:
    """Find all installed map plugins under gps_geocoder.maps.*"""
    maps = {}
    try:
        import gps_geocoder.maps as maps_pkg
        for importer, modname, ispkg in pkgutil.iter_modules(maps_pkg.__path__):
            if not ispkg:
                continue
            try:
                mod = importlib.import_module(f"gps_geocoder.maps.{modname}")
                map_id = getattr(mod, "MAP_ID", modname)
                maps[map_id] = mod
            except ImportError:
                pass
    except ImportError:
        pass
    return maps


def list_maps() -> list[dict]:
    """Return info about all available map plugins and their build status."""
    discovered = _discover_map_modules()
    result = []
    for map_id, mod in discovered.items():
        name = getattr(mod, "MAP_NAME", map_id)
        name_local = getattr(mod, "MAP_NAME_LOCAL", "")

        # Check if the DB file exists
        db_files = list(MAPS_DIR.glob(f"{map_id}*.db")) if MAPS_DIR.exists() else []
        built = len(db_files) > 0
        size_mb = sum(f.stat().st_size for f in db_files) / (1024 * 1024) if built else 0

        result.append({
            "id": map_id,
            "name": name,
            "name_local": name_local,
            "installed": True,
            "built": built,
            "size_mb": round(size_mb, 1),
        })
    return result


def get_map_query(map_id: str):
    """Import and return the query module for a specific map."""
    mod = importlib.import_module(f"gps_geocoder.maps.{map_id}.query")
    return mod


def get_map_build(map_id: str):
    """Import and return the build module for a specific map."""
    mod = importlib.import_module(f"gps_geocoder.maps.{map_id}.build")
    return mod
