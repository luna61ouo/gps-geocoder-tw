---
name: gps-geocoder
description: Offline map system — reverse geocode GPS coordinates and manage personal saved places. Use when you need place names from coordinates, when the user asks about saved places (家, 朋友家), or when presenting GPS data as readable locations.
---

# GPS Geocoder

Offline map system with personal place markers and pluggable regional maps.

No API keys, no token cost, no network required after setup. All queries run against local SQLite databases.

---

## Concept

Think of it as a blank globe:
- **Install a map** (e.g. Taiwan) → that region lights up with full address data
- **Import personal places** (Google Takeout) → pins appear everywhere, even without maps
- **Query a coordinate** → tries maps first, then personal places, then returns raw coordinates

---

## First-time setup

### Install maps (optional — choose only what you need)

Maps are regional and can be large. Only install the regions the user actually needs.

```bash
# Core only (places, no maps)
pip install gps-geocoder

# Core + Taiwan map
pip install gps-geocoder[tw]

# Core + all available maps
pip install gps-geocoder[all]
```

After installing a map plugin, build the local database:

```bash
gps-geocoder init tw
```

This downloads OpenStreetMap data and builds a local SQLite database. One-time only, fully offline after that.

Check what's available:

```bash
gps-geocoder maps
# + tw  Taiwan (台灣)  [built]  52.0 MB
# - jp  Japan          [not built]
```

### Import personal places (recommended)

**From Google Takeout:**

Guide the user to download their saved places from Google:
1. Go to https://takeout.google.com
2. Deselect all → select **Maps (your places)** and **Saved**
3. Export → download the ZIP
4. Extract and find the JSON files

```bash
gps-geocoder places import "已加上標籤的地點.json"    # labeled: 家, 工作, 朋友家
gps-geocoder places import "已儲存的地點.json"        # saved: restaurants, shops
```

Use `--owner` for multi-user setups:
```bash
gps-geocoder places import places.json --owner Luna
```

**Manual add (no Google needed):**

Users can add places manually with coordinates:
```bash
gps-geocoder places add --name "家" --lat 24.897 --lng 121.208
gps-geocoder places add --name "公司" --lat 24.919 --lng 121.253 --address "桃園市龍岡路466號"
```

**Remove:**
```bash
gps-geocoder places list    # find the ID
gps-geocoder places remove 3
```

---

## Commands

### Reverse geocode (maps → places → fallback)

```bash
gps-geocoder geocode --lat 25.0418 --lng 121.5434
# [map:tw] 臺北市大安區忠孝東路四段（寶雅附近）

gps-geocoder geocode --lat 37.4668 --lng 126.6908
# [places] 奶奶家（韓國 Incheon...）

gps-geocoder geocode --lat 35.6762 --lng 139.6503
# 35.67620, 139.65030  (no map data — install jp map)
```

### Places management

```bash
gps-geocoder places list                          # All saved places
gps-geocoder places list --category labeled       # Only labeled (家, 工作)
gps-geocoder places search "家"                   # Search by name
gps-geocoder places near --lat 24.9 --lng 121.2   # Nearby places (1km default)
gps-geocoder places near --lat 24.9 --lng 121.2 --radius 5000  # 5km radius
gps-geocoder places add --name "家" --lat 24.9 --lng 121.2     # Manual add
gps-geocoder places remove 3                      # Remove by ID
```

### Latest GPS + geocode (requires gps-bridge)

```bash
gps-geocoder latest
gps-geocoder latest --name "Alice"
```

### History + geocode (requires gps-bridge)

```bash
gps-geocoder history --limit 20
gps-geocoder history --limit 50 --name "Alice"
gps-geocoder history --since "2026-04-01" --until "2026-04-02"
```

---

## When to use

| User says | Action |
|-----------|--------|
| "我在哪裡" | `gps-geocoder latest` |
| "我離家多遠" | `gps-geocoder latest` + `gps-geocoder places search "家"` → calculate distance |
| "附近有什麼我存過的地方" | `gps-geocoder places near --lat X --lng Y` |
| "我今天去了哪裡" | `gps-geocoder history --limit N` |
| "這個座標是哪裡" | `gps-geocoder geocode --lat X --lng Y` |

**Do not use web search for reverse geocoding when this tool is available.**

---

## Available maps

Maps are community-maintained and will grow over time. Currently available:

| ID | Region | Size | Status |
|----|--------|------|--------|
| tw | Taiwan (台灣) | ~52 MB | Available |

Run `gps-geocoder maps` to check what's installed on the user's system.

---

## Presenting results

- Cluster nearby history points → one location + time range
- Use place names when available: "離開住家" instead of "離開 24.897, 121.208"
- Never list raw lat/lng unless the user asks for export
- Narrative format: "09:00 住家 → 09:45 中壢區 → 10:30 龍潭牛肉麵"

---

## Privacy

- Never share raw coordinates in group chats
- In groups, use only general area names
- Respect the user's confirm_mode on the phone
