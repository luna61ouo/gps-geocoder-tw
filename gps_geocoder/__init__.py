"""gps-geocoder — Offline map system with personal place markers and pluggable regional maps."""

__version__ = "0.2.0"

# Data directory for all geocoder data (places, maps, config)
from pathlib import Path

GEOCODER_DIR = Path.home() / ".gps-geocoder"
