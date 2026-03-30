---
name: gps-geocoder-tw
description: Convert GPS coordinates to Taiwan location names (offline). Use when you already have coordinates from gps-bridge and need to know the place name — district, street, nearby POI. Triggers on location-related questions like "我在哪", "經過哪裡", "這是什麼地方", or when presenting GPS history to the user as readable locations.
---

# GPS Geocoder Taiwan

Offline reverse geocoder — converts raw GPS coordinates into human-readable Taiwan location names.

No API keys, no token cost, no network required. All queries run against a local SQLite database built from OpenStreetMap data.

**Requires:** `gps-bridge` (provides raw coordinates) + `gps-geocoder-tw` (provides location names).

---

## First-time setup

Before using any command, the local map database must be initialized:

```bash
gps-geocoder init
```

This downloads Taiwan OpenStreetMap data (~300 MB) and builds `~/.gps-geocoder-tw/taiwan_map.db` (~50 MB). One-time only, fully offline after that.

If the user runs any geocoder command and gets "database not found", guide them to run `gps-geocoder init`.

To update map data:

```bash
gps-geocoder init --force
```

---

## Commands

### Reverse geocode a coordinate (standalone, no bridge needed)

```bash
gps-geocoder geocode --lat 25.0418 --lng 121.5434
# Output: 臺北市大安區忠孝東路四段（寶雅附近）

gps-geocoder geocode --lat 25.0418 --lng 121.5434 --json
```

### Latest GPS fix with location name (reads from bridge)

```bash
gps-geocoder latest
gps-geocoder latest --name "Alice"
gps-geocoder latest --json
```

### Movement history with location names (reads from bridge)

```bash
gps-geocoder history --limit 20
gps-geocoder history --limit 50 --name "Alice"
gps-geocoder history --limit 20 --json

# Time range query
gps-geocoder history --limit 100 --since "2026-03-27T14:00:00" --until "2026-03-27T18:00:00"
```

---

## Output format

**Plain text:**
```
臺北市大安區忠孝東路四段（寶雅附近）
```

**JSON (--json):**
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

**history --json** (each record includes bridge fields + location):
```json
{
  "id": 42,
  "name": "default",
  "lat": 25.0418,
  "lng": 121.5434,
  "timestamp": "2026-03-28T08:30:00",
  "received_at": "2026-03-28T08:30:01+00:00",
  "location": "臺北市大安區忠孝東路四段（寶雅附近）",
  "city": "臺北市",
  "district": "大安區",
  "street": "忠孝東路四段",
  "poi": "寶雅"
}
```

---

## When to use this skill

| User says | Action |
|-----------|--------|
| "我在哪裡" / "我現在的位置" | `gps-geocoder latest` |
| "我今天去了哪裡" / "經過哪些地方" | `gps-geocoder history --limit N` |
| "這個座標是哪裡" / gives lat/lng | `gps-geocoder geocode --lat X --lng Y` |
| Reviewing movement trail | `gps-geocoder history --limit N --json` then summarise |
| "Alice 在哪" (multi-tracker) | `gps-geocoder latest --name "Alice"` |

**Do not use web search for reverse geocoding when this tool is available.**

---

## Workflow: answering "我在哪裡？"

Preferred (one step):
```bash
gps-geocoder latest
```

Or manually:
```bash
gps-bridge latest                              # → lat, lng
gps-geocoder geocode --lat <lat> --lng <lng>   # → location name
```

---

## Workflow: reviewing movement history

### Step 1: Check tracker settings

```bash
gps-bridge status
```

If `歷史刻度` is `不儲存`, history is disabled — use `gps-geocoder latest` only.

### Step 2: Estimate and fetch

| Time range | Granularity | Estimated records | Strategy |
|------------|-------------|-------------------|----------|
| Last 3 hours | 10 min | ~18 | Fetch all |
| Yesterday | 30 min | ~48 | Fetch all |
| Last week | 1 hour | ~168 | Summarise by day |
| Last week | 10 min | ~1,008 | Query one day at a time |

```bash
gps-geocoder history --limit 50 --json
```

### Step 3: Present as narrative, not raw data

Convert the results into a readable summary:

> 08:00 臺北市大安區（家附近）→ 09:15 臺北市中正區忠孝西路（台北車站）→ 12:00 臺北市信義區松智路（玉山銀行附近）

Rules:
- Cluster nearby points → one location name + time range
- Never list raw lat/lng unless the user explicitly asks for export
- Keep to ~100 records max per LLM response

---

## Multi-tracker support

`gps-bridge` can track multiple devices. Use `--name` to query a specific tracker:

```bash
gps-geocoder latest --name "Alice"
gps-geocoder history --limit 20 --name "Bob"
```

Without `--name`, returns data across all trackers.

---

## Freshness check

When using `gps-geocoder latest`, check the `received_at` timestamp. If older than **10 minutes**, warn the user that the location may be stale (phone off or out of range).

---

## Limitations

- **Coverage:** Taiwan only (OpenStreetMap data)
- **POI detail:** Depends on OSM community contributions — some shop branch names may be incomplete
- **Coordinates outside Taiwan** will return partial or no results
- **Database required:** If not initialized, commands will fail — guide user to run `gps-geocoder init`

---

## Privacy

GPS data is sensitive.
- Never share raw coordinates in group chats or public channels.
- In groups, use only the general area name (e.g. "在桃園", not exact lat/lng).
- Respect the user's `confirm_mode` setting on the phone — if set to "拒絕", no data is being sent.
