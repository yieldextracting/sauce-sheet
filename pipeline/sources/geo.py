"""Venue coordinates and elevation, fetched (not typed) and cached in reference/venues.json.

- Geocoding: OpenStreetMap Nominatim (1 request/second policy, identifying UA).
- Elevation: Open-Meteo elevation API (Copernicus DEM).
Keyed by ESPN's venue city ("Denver, CO"), which is precise enough for travel distance.
"""

from __future__ import annotations

import math
import time

from ..et import now_utc, to_utc_iso
from ..io import read_json, write_json
from ..paths import VENUES
from .http import get_json

NOMINATIM = "https://nominatim.openstreetmap.org/search"
ELEVATION = "https://api.open-meteo.com/v1/elevation"


def load() -> dict[str, dict]:
    return read_json(VENUES, {})


def ensure(keys: set[str]) -> dict[str, dict]:
    """Make sure every venue key has coordinates + elevation. Fetches only missing ones."""
    venues = load()
    missing = sorted(k for k in keys if k and k not in venues)
    for k in missing:
        hits = get_json(NOMINATIM, {"q": k, "format": "json", "limit": 1}, source="nominatim")
        if not hits:
            raise RuntimeError(f"geocode failed for venue city {k!r}")
        lat, lon = float(hits[0]["lat"]), float(hits[0]["lon"])
        elev = get_json(ELEVATION, {"latitude": lat, "longitude": lon}, source="open-meteo")["elevation"][0]
        venues[k] = {"lat": round(lat, 4), "lon": round(lon, 4), "elevationM": float(elev),
                     "source": "OpenStreetMap Nominatim + Open-Meteo elevation",
                     "fetchedAt": to_utc_iso(now_utc())}
        write_json(VENUES, dict(sorted(venues.items())))
        time.sleep(1.1)  # Nominatim usage policy
    return venues


def haversine_km(a: dict, b: dict) -> float:
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = p2 - p1
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
