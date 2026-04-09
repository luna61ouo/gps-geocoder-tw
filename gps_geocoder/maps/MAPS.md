# Available Maps

gps-geocoder uses a pluggable map system. Each regional map is an optional module that can be installed independently.

## Currently available

| ID | Region | Data source | Approx. size |
|----|--------|-------------|-------------|
| `tw` | Taiwan (台灣) | OpenStreetMap / Geofabrik | ~52 MB |
| `jp` | Japan (日本) | OpenStreetMap / Geofabrik | ~400 MB |
| `kr` | South Korea (한국) | OpenStreetMap / Geofabrik | ~100 MB |

## Planned

Regional maps will be added over time based on community demand:

- `us` — United States (by state, due to data size)

## Install and build

```bash
# Install map support (covers all regions)
pip install gps-geocoder[maps]

# Build only the regions you need
gps-geocoder init tw    # Taiwan
gps-geocoder init jp    # Japan
gps-geocoder init kr    # South Korea
```

Maps auto-build on first query if not initialized.

## Without any maps

Even without installing any maps, you can still:
- Import personal places from Google Takeout
- Search and query your saved places
- Get raw coordinates from gps-bridge

Maps add street-level address resolution for their region.
