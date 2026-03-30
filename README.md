# gps-geocoder-tw

Offline reverse geocoder for Taiwan — converts GPS coordinates to street-level location names using [OpenStreetMap](https://www.openstreetmap.org/) data.

An extension for [gps-bridge](https://github.com/luna61ouo/gps-bridge). No API keys, no token cost, fully offline after setup.

---

## What it does

```
Input:  (25.0418, 121.5434)
Output: 臺北市大安區忠孝東路四段（寶雅附近）
```

Returns structured location data: city, district, street, and nearest POI.

---

## Requirements

- Python 3.10+
- [gps-bridge](https://github.com/luna61ouo/gps-bridge) (installed automatically as dependency)
- ~300 MB disk for map data download (one-time)
- ~50 MB disk for the built database

---

## Installation

```bash
pip install gps-geocoder-tw
```

Or from source:

```bash
git clone https://github.com/luna61ouo/gps-geocoder-tw.git
cd gps-geocoder-tw
pip install -e .
```

This will also install `gps-bridge` if not already present.

---

## Setup

After installation, build the local map database (one-time):

```bash
gps-geocoder init
```

This downloads Taiwan OpenStreetMap data (~300 MB) from [Geofabrik](https://download.geofabrik.de/asia/taiwan.html) and builds a local SQLite database (~50 MB). Everything runs offline after this step.

To update the map data later:

```bash
gps-geocoder init --force
```

---

## Usage

```bash
# Reverse geocode a coordinate
gps-geocoder geocode --lat 25.0418 --lng 121.5434
# → 臺北市大安區忠孝東路四段（寶雅附近）

# JSON output with full detail
gps-geocoder geocode --lat 25.0418 --lng 121.5434 --json

# Show latest GPS fix with location name (reads from gps-bridge)
gps-geocoder latest

# Show movement history with location names
gps-geocoder history --limit 20

# Filter by tracker name
gps-geocoder latest --name "Alice"
gps-geocoder history --limit 50 --name "Alice" --json
```

### Output example

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

---

## OpenClaw Skill

This package includes an OpenClaw skill. Copy it into your OpenClaw skills folder:

```bash
cp -r skills/gps-geocoder-tw /path/to/your/openclaw/skills/
```

Or if you installed via pip:

```bash
pip show gps-geocoder-tw | grep Location
# Then copy from: <location>/skills/gps-geocoder-tw/SKILL.md
```

The skill enables OpenClaw to automatically convert GPS coordinates to location names when answering questions like:

- "我在哪裡？"
- "我今天去了哪些地方？"
- "剛才經過哪裡？"

### How it works with gps-bridge

```
gps-bridge (raw coordinates)  →  gps-geocoder-tw (location names)

"我在哪裡？"
  1. gps-bridge latest        → lat=25.0418, lng=121.5434
  2. gps-geocoder geocode     → 臺北市大安區忠孝東路四段
  3. OpenClaw responds        → "你在臺北市大安區忠孝東路四段，寶雅附近"
```

---

## Data source

- Map data: [OpenStreetMap](https://www.openstreetmap.org/) Taiwan extract via [Geofabrik](https://download.geofabrik.de/asia/taiwan.html)
- Parsed with [osmiter](https://pypi.org/project/osmiter/) (pure Python, cross-platform)
- Stored locally at `~/.gps-geocoder-tw/taiwan_map.db`
- Coverage depends on OSM community contributions — urban areas have excellent detail, rural areas may be thinner

---

## License

MIT
