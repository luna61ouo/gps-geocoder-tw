# gps-geocoder

Offline map system with personal place markers and pluggable regional maps.

No API keys, no token cost, fully offline after setup. Works as a standalone tool or as an extension for [gps-bridge](https://github.com/luna61ouo/gps-bridge).

---

## Concept

Think of it as a blank globe:
- **Install a regional map** (e.g. Taiwan, Japan, Korea) — that region lights up with full address data
- **Import personal places** (from Google Takeout or manually) — pins appear everywhere, even without maps
- **Query a coordinate** — tries maps first, then personal places, then returns raw coordinates

---

## Requirements

- Python 3.10+
- Optional: [gps-bridge](https://github.com/luna61ouo/gps-bridge) (for `latest` and `history` commands)

---

## Installation

```bash
# Core only (places, no map support)
pip install gps-geocoder

# Core + map support (any region)
pip install gps-geocoder[maps]
```

Or from source:

```bash
git clone https://github.com/luna61ouo/gps-geocoder.git
cd gps-geocoder
pip install -e ".[maps]"
```

---

## Setup

### Build a regional map (optional)

```bash
gps-geocoder init tw    # Build Taiwan map
gps-geocoder init jp    # Build Japan map
gps-geocoder init kr    # Build South Korea map
```

Downloads OpenStreetMap data and builds a local SQLite database. One-time only, fully offline after that. Maps also auto-build on first use if not initialized.

Check installed maps:

```bash
gps-geocoder maps
# + tw  Taiwan       [built]      52.0 MB
# + jp  Japan        [built]     400.0 MB
# - kr  South Korea  [not built]
```

### Import personal places

**From Google Takeout:**

1. Go to https://takeout.google.com
2. Deselect all, then select **Maps (your places)** and **Saved**
3. Export, download the ZIP, and extract it
4. Import the JSON files:

```bash
gps-geocoder places import "Labeled places.json"
gps-geocoder places import "Saved places.json"
```

> File names depend on your Google account language. Look for JSON files inside the `Takeout/` folder.

**Manual add:**

```bash
gps-geocoder places add --name "Home" --lat 25.033 --lng 121.565
gps-geocoder places add --name "Office" --lat 25.042 --lng 121.543 --address "123 Main St."
```

---

## Usage

```bash
# Reverse geocode a coordinate (maps -> places -> fallback)
gps-geocoder geocode --lat 25.0418 --lng 121.5434
# [map:tw] Taipei, Da'an District, Zhongxiao E. Rd. Sec. 4

gps-geocoder geocode --lat 35.6762 --lng 139.6503
# [map:jp] Tokyo, Shibuya

gps-geocoder geocode --lat 37.4668 --lng 126.6908
# [places] Grandma's house (Incheon, South Korea)

# Search saved places
gps-geocoder places search "Home"
gps-geocoder places near --lat 25.0 --lng 121.5

# List all places
gps-geocoder places list

# Remove a place by ID
gps-geocoder places remove 3

# With gps-bridge: latest GPS fix + geocode
gps-geocoder latest
gps-geocoder latest --name "Alice"

# With gps-bridge: movement history + geocode
gps-geocoder history --limit 20
```

---

## Available maps

Maps are regional plugins. Install only what you need:

| ID | Region | Approx. DB size | Build command |
|----|--------|----------------|---------------|
| `tw` | Taiwan | ~52 MB | `gps-geocoder init tw` |
| `jp` | Japan | ~400 MB | `gps-geocoder init jp` |
| `kr` | South Korea | ~100 MB | `gps-geocoder init kr` |

All maps require `pip install gps-geocoder[maps]`. Maps also auto-build on first query if not initialized.

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
