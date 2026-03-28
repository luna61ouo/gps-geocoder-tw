---
name: gps-geocoder-tw
description: Convert GPS coordinates to Taiwan location names (offline). Use when you already have coordinates from gps-bridge and need to know the place name — district, street, nearby POI. Triggers on location-related questions like "我在哪", "經過哪裡", "這是什麼地方", or when presenting GPS history to the user as readable locations.
---

# GPS Geocoder Taiwan

Offline reverse geocoder — converts raw GPS coordinates into human-readable Taiwan location names.

**Requires:** `gps-bridge` (provides raw coordinates) + `gps-geocoder-tw` (provides location names).

## Commands

```bash
# Single coordinate → location name
gps-geocoder geocode --lat 25.0418 --lng 121.5434
# Output: 臺北市大安區忠孝東路四段（寶雅附近）

# Detailed JSON output
gps-geocoder geocode --lat 25.0418 --lng 121.5434 --json

# Bridge latest fix + location name
gps-geocoder latest
gps-geocoder latest --name "Alice"

# Bridge history + location names
gps-geocoder history --limit 20
gps-geocoder history --limit 20 --name "Alice" --json
```

## Output format

**geocode --json:**
```json
{
  "city": "臺北市",
  "district": "大安區",
  "village": null,
  "street": "忠孝東路四段",
  "street_distance_m": 33.8,
  "poi": "寶雅",
  "poi_category": "chemist",
  "poi_distance_m": 11.5,
  "summary": "臺北市大安區忠孝東路四段（寶雅附近）"
}
```

## When to use

- User asks "我在哪裡" / "我現在的位置" → `gps-bridge latest` then `gps-geocoder geocode`
- User asks "我今天去了哪裡" → `gps-geocoder history --limit N`
- Presenting GPS history → always use `gps-geocoder` to convert coordinates to place names before showing to user
- **Do not use web search for reverse geocoding when this tool is available**

## Workflow: answering "我在哪裡？"

```bash
# Step 1: get raw coordinates
gps-bridge latest

# Step 2: convert to location name
gps-geocoder geocode --lat <lat> --lng <lng>
```

Or in one step:
```bash
gps-geocoder latest
```

## Workflow: reviewing movement history

```bash
# Get history with location names attached
gps-geocoder history --limit 50 --json
```

Then summarise as a narrative:
> 8:00 臺北市大安區（家附近）→ 9:15 臺北市中正區忠孝西路（台北車站）→ 12:00 臺北市信義區松智路

## Limitations

- Coverage: Taiwan only (OpenStreetMap data)
- POI detail depends on OSM community contributions — convenience store branch names may be incomplete
- If `gps-geocoder geocode` fails with "database not found", tell the user to run `gps-geocoder init`
- Coordinates outside Taiwan will return partial or no results

## First-time setup

If the database is not yet initialized:

```bash
gps-geocoder init
```

This downloads Taiwan map data (~300 MB) and builds a local database (~50 MB). One-time only, fully offline after that.
