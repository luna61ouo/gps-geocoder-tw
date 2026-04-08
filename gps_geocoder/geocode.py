"""
geocode.py — Unified reverse geocoding router.

Query flow:
    1. Try each installed map plugin (check if coordinate is in range)
    2. Check places DB for nearby personal markers
    3. Fallback: return raw coordinates with "no map data" note
"""

from __future__ import annotations

from gps_geocoder.registry import list_maps, get_map_query


# Bounding boxes for each map region (lat_min, lat_max, lng_min, lng_max)
MAP_BOUNDS = {
    "tw": (21.8, 26.5, 119.2, 122.2),
    # "jp": (24.0, 46.0, 122.9, 153.99),
    # "kr": (33.0, 38.7, 124.5, 132.0),
}


def _in_bounds(lat: float, lng: float, bounds: tuple[float, float, float, float]) -> bool:
    lat_min, lat_max, lng_min, lng_max = bounds
    return lat_min <= lat <= lat_max and lng_min <= lng <= lng_max


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    Reverse geocode a coordinate using all available sources.

    Returns dict with at least: summary, source, lat, lng
    """
    # 1. Try installed map plugins
    available_maps = list_maps()
    for m in available_maps:
        map_id = m["id"]
        if not m["built"]:
            continue
        bounds = MAP_BOUNDS.get(map_id)
        if bounds and not _in_bounds(lat, lng, bounds):
            continue
        try:
            query_mod = get_map_query(map_id)
            result = query_mod.reverse_geocode(lat, lng)
            if result and result.get("summary"):
                result["source"] = f"map:{map_id}"
                return result
        except (FileNotFoundError, ImportError):
            continue

    # 2. Try places DB for nearby personal markers
    try:
        from gps_geocoder.places import find_nearest_place
        place = find_nearest_place(lat, lng, radius_m=500)
        if place:
            return {
                "summary": f"{place['name']}（{place['address'] or f'{lat:.4f}, {lng:.4f}'}）",
                "place_name": place["name"],
                "address": place["address"],
                "source": "places",
                "city": None,
                "district": None,
                "village": None,
                "street": None,
                "poi": place["name"],
                "poi_distance_m": place["distance_m"],
            }
    except (ImportError, FileNotFoundError):
        pass

    # 3. Fallback: raw coordinates
    return {
        "summary": f"{lat:.5f}, {lng:.5f}",
        "source": "none",
        "city": None,
        "district": None,
        "village": None,
        "street": None,
        "poi": None,
    }
