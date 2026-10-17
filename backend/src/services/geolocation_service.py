"""Geolocation Service querying OpenStreetMap Overpass API with resilient fallback."""

import json
import logging
import math
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List

logger = logging.getLogger("dermassist.geolocation")


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two GPS coordinates using the Haversine formula."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


class GeolocationService:
    """Fetches verified dermatology clinics via OpenStreetMap Overpass API (single request)."""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def search_clinics(
        self,
        lat: float,
        lon: float,
        radius_km: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Query Overpass API for dermatologists, skin clinics, and hospitals in one request.
        Uses a radius-based around() filter — no rate-limit risk (single call).
        """
        radius_m = int(max(1.0, float(radius_km)) * 1000)

        # Single Overpass QL query covering all relevant amenity/healthcare tags
        overpass_query = f"""
[out:json][timeout:10];
(
  node["healthcare"="dermatology"](around:{radius_m},{lat},{lon});
  node["amenity"="doctors"]["healthcare:speciality"="dermatology"](around:{radius_m},{lat},{lon});
  node["amenity"="clinic"](around:{radius_m},{lat},{lon});
  node["amenity"="hospital"](around:{radius_m},{lat},{lon});
  way["amenity"="clinic"](around:{radius_m},{lat},{lon});
  way["amenity"="hospital"](around:{radius_m},{lat},{lon});
);
out center 12;
"""

        headers = {
            "User-Agent": "DermAssistAI/2.0 (open-source skin lesion triage tool)",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        clinics: List[Dict[str, Any]] = []
        seen_coords: set = set()

        try:
            post_data = urllib.parse.urlencode({"data": overpass_query}).encode("utf-8")
            req = urllib.request.Request(self.OVERPASS_URL, data=post_data, headers=headers)
            with urllib.request.urlopen(req, timeout=12.0) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode("utf-8"))
                    for item in result.get("elements", []):
                        # way elements have a center key; nodes have lat/lon directly
                        if item.get("type") == "way":
                            c_lat = float(item.get("center", {}).get("lat", 0.0))
                            c_lon = float(item.get("center", {}).get("lon", 0.0))
                        else:
                            c_lat = float(item.get("lat", 0.0))
                            c_lon = float(item.get("lon", 0.0))

                        if not c_lat and not c_lon:
                            continue

                        coord_key = (round(c_lat, 3), round(c_lon, 3))
                        if coord_key in seen_coords:
                            continue
                        seen_coords.add(coord_key)

                        tags = item.get("tags", {})
                        name = (
                            tags.get("name")
                            or tags.get("operator")
                            or tags.get("amenity", "Medical Center").replace("_", " ").title()
                        )
                        addr_parts = [
                            tags.get("addr:housenumber", ""),
                            tags.get("addr:street", ""),
                            tags.get("addr:city", ""),
                        ]
                        address_str = ", ".join(p for p in addr_parts if p) or "Address not listed"
                        dist_km = calculate_haversine_distance(lat, lon, c_lat, c_lon)

                        clinics.append({
                            "name": name,
                            "lat": c_lat,
                            "lon": c_lon,
                            "distance_km": dist_km,
                            "address": address_str,
                            "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={c_lat},{c_lon}",
                        })
        except Exception as exc:
            logger.warning(f"Overpass API query failed: {exc}")

        clinics.sort(key=lambda x: x["distance_km"])
        return clinics[:8]
