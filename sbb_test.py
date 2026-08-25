#!/usr/bin/env python3
"""
Filters stationboard departures by whether they're likely visible from a
given point (e.g. your apartment), based on compass bearing geometry.

How it works:
  1. Get the station's coordinates (from the stationboard response).
  2. Compute the bearing from the station -> your apartment. That's
     "the direction I need to look."
  3. For each departure, resolve the destination station's coordinates
     (via /v1/locations) and compute the bearing station -> destination.
     That's roughly "the direction this train is heading."
  4. If the two bearings are within MARGIN_DEGREES of each other, mark
     the train as visible.

This is an approximation — it doesn't know about the station building,
platform layout, or track curvature near the station. Use it as a
starting filter, then tune MARGIN_DEGREES once you've checked it
against what you can actually see out the window.

Usage:
    python3 sbb_visibility.py
    python3 sbb_visibility.py --visible-only

Edit the constants below to match your setup — no flags needed for
day-to-day runs.
"""

import argparse
import math
import requests

API_BASE = "https://transport.opendata.ch/v1"

# --- Edit these to match your setup ---
STATION = "Renens VD"
APARTMENT_LAT = 46.53420
APARTMENT_LON = 6.59021
LIMIT = 10
MARGIN_DEGREES = 60.0
# ---------------------------------------


def bearing(lat1, lon1, lat2, lon2):
    """Compass bearing in degrees (0-360, 0=N, 90=E) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)
    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def angle_diff(a, b):
    """Smallest difference between two bearings, 0-180 degrees."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


def get_departures(station, limit=10):
    resp = requests.get(f"{API_BASE}/stationboard", params={"station": station, "limit": limit}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def geocode(name, cache):
    """Look up coordinates for a station name, with caching to limit API calls."""
    if name in cache:
        return cache[name]
    resp = requests.get(f"{API_BASE}/locations", params={"query": name, "type": "station"}, timeout=10)
    resp.raise_for_status()
    stations = resp.json().get("stations", [])
    coords = None
    if stations:
        c = stations[0].get("coordinate", {})
        if c.get("x") and c.get("y"):
            coords = (float(c["x"]), float(c["y"]))  # x=lat, y=lon per API docs
    cache[name] = coords
    return coords


def main():
    parser = argparse.ArgumentParser(description="Filter departures by visibility from a point")
    parser.add_argument("--visible-only", action="store_true", help="Only print departures classified as visible")
    args = parser.parse_args()

    data = get_departures(STATION, LIMIT)
    station = data.get("station")
    if not station or not station.get("coordinate"):
        print(f"Could not resolve station '{STATION}'. Try a more exact name.")
        return

    station_lat = float(station["coordinate"]["x"])
    station_lon = float(station["coordinate"]["y"])
    apartment_bearing = bearing(station_lat, station_lon, APARTMENT_LAT, APARTMENT_LON)

    print(f"\nStation: {station['name']}  ({station_lat:.5f}, {station_lon:.5f})")
    print(f"Bearing to your location: {apartment_bearing:.1f}°   Margin: ±{MARGIN_DEGREES}°\n")
    print("-" * 70)

    geocode_cache = {}
    for entry in data.get("stationboard", []):
        stop = entry.get("stop", {})
        dep_time = (stop.get("departure") or "")[11:16]
        category = entry.get("category", "")
        number = entry.get("number", "")
        to = entry.get("to", "")
        platform = stop.get("platform", "?")

        dest_coords = geocode(to, geocode_cache)
        if dest_coords is None:
            visible = None  # couldn't resolve, unknown
            note = "? (couldn't geocode destination)"
        else:
            train_bearing = bearing(station_lat, station_lon, dest_coords[0], dest_coords[1])
            diff = angle_diff(train_bearing, apartment_bearing)
            visible = diff <= MARGIN_DEGREES
            note = f"train bearing {train_bearing:.0f}°, diff {diff:.0f}°"

        if args.visible_only and not visible:
            continue

        tag = "VISIBLE " if visible else ("VISIBLE?" if visible is None else "        ")
        print(f"{dep_time}  {category}{number:<6} -> {to:<25} Platform {platform:<4} [{tag}] {note}")

    print()


if __name__ == "__main__":
    main()