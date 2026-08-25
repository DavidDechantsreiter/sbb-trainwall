#!/usr/bin/env python3
"""
Quick experiment script for the transport.opendata.ch stationboard API.
No hardware needed — run this on your laptop to see what the data looks like.

Usage:
    python3 sbb_api_test.py "Zürich HB"
    python3 sbb_api_test.py "Lausanne" --limit 5
"""

import sys
import argparse
import requests

API_URL = "https://transport.opendata.ch/v1/stationboard"

def get_departures():
    params = {
        "station": "Renens",
        "limit": 6,
    }
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def main():

    data = get_departures()

    resolved_name = data.get("station", {}).get("name", "Renens")
    print(f"\nDepartures for: {resolved_name}\n" + "-" * 40)

    for entry in data.get("stationboard", []):
        stop = entry.get("stop", {})
        departure_time = stop.get("departure", "")[11:16]  # HH:MM slice from ISO timestamp
        delay = stop.get("delay")
        platform = stop.get("platform", "?")
        category = entry.get("category", "")
        number = entry.get("number", "")
        to = entry.get("to", "")

        delay_str = f" (+{delay})" if delay else ""
        print(f"{departure_time}{delay_str}  {category}{number:<6} → {to:<25} Platform {platform}")

    print()
    print("Raw JSON keys available per entry:", list(data["stationboard"][0].keys()) if data.get("stationboard") else "none")


if __name__ == "__main__":
    main()