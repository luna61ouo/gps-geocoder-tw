# gps-geocoder

Offline map system with personal place markers and pluggable regional maps.

No API keys, no token cost, fully offline after setup. Works as a standalone tool or as an extension for [gps-bridge](https://github.com/luna61ouo/gps-bridge).

---

## Concept

Think of it as a blank globe:
- **Install a regional map** (e.g. Taiwan) → that region lights up with full address data
- **Import personal places** (from Google Takeout or manually) → pins appear everywhere, even without maps
- **Query a coordinate** → tries maps first, then personal places, then returns raw coordinates

---

## Requirements

- Python 3.10+
- Optional: [gps-bridge](https://github.com/luna61ouo/gps-bridge) (for `latest` and `history` commands)

---

## Installation

```bash
# Core only (places, geocode router — no maps)
pip install gps-geocoder

# Core + Taiwan map
pip install gps-geocoder[tw]

# Core + all available maps
pip install gps-geocoder[all]
```

Or from source:

```bash
git clone https://github.com/luna61ouo/gps-geocoder.git
cd gps-geocoder
pip install -e ".[tw]"
```

---

## Setup

### Build a regional map (optional)

```bash
gps-geocoder init tw
```

Downloads OpenStreetMap data and builds a local SQLite database. One-time only, fully offline after that.

Check installed maps:

```bash
gps-geocoder maps
# + tw  Taiwan (台灣)  [built]  52.0 MB
```

### Import personal places

**From Google Takeout:**

1. Go to https://takeout.google.com
2. Deselect all → select **Maps (your places)** and **Saved**
3. Export → download ZIP → extract

```bash
gps-geocoder places import "已加上標籤的地點.json"
gps-geocoder places import "已儲存的地點.json"
```

**Manual add:**

```bash
gps-geocoder places add --name "家" --lat 24.897 --lng 121.208
gps-geocoder places add --name "公司" --lat 24.919 --lng 121.253 --address "桃園市龍岡路466號"
```

---

## Usage

```bash
# Reverse geocode a coordinate (maps → places → fallback)
gps-geocoder geocode --lat 25.0418 --lng 121.5434
# [map:tw] 臺北市大安區忠孝東路四段（寶雅附近）

gps-geocoder geocode --lat 37.4668 --lng 126.6908
# [places] 奶奶家（韓國 Incheon...）

# Search places
gps-geocoder places search "家"
gps-geocoder places near --lat 24.9 --lng 121.2

# List all places
gps-geocoder places list

# Remove a place
gps-geocoder places remove 3

# With gps-bridge: latest GPS + geocode
gps-geocoder latest
gps-geocoder latest --name "Alice"

# With gps-bridge: movement history + geocode
gps-geocoder history --limit 20
```

---

## Available maps

Maps are regional plugins. Install only what you need:

| ID | Region | Size | Install |
|----|--------|------|---------|
| `tw` | Taiwan (台灣) | ~52 MB | `pip install gps-geocoder[tw]` |

More maps will be added over time. See [MAPS.md](gps_geocoder/maps/MAPS.md) for details.

---

## OpenClaw Skill

This package includes an OpenClaw skill. Copy it into your skills folder:

**From source:**

```bash
cp -r skills/gps-geocoder ~/.openclaw/workspace/skills/
```

**From pip install:**

```bash
GEO_DIR=$(python3 -c "import gps_geocoder; import os; print(os.path.dirname(gps_geocoder.__file__))")
cp -r "${GEO_DIR}/../skills/gps-geocoder" ~/.openclaw/workspace/skills/
```

**Restart OpenClaw after copying the skill.**

---

## Data storage

- Places: `~/.gps-geocoder/places.db`
- Maps: `~/.gps-geocoder/maps/<region>.db`
- All data stays on your own machine

---

## License

MIT
