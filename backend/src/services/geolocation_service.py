"""Geolocation Service querying OpenStreetMap Nominatim API with resilient fallback."""

import json
import logging
import math
import urllib.parse
import urllib.request
from typing import Any, Dict, List

logger = logging.getLogger("dermassist.geolocation")


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers between two GPS coordinates using the Haversine formula."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


class GeolocationService:
    """Fetches verified dermatology clinics and medical centers via OpenStreetMap Nominatim."""

    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

    def search_clinics(
        self,
        lat: float,
        lon: float,
        radius_km: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Query real-time OpenStreetMap Nominatim API for dermatologists, skin clinics, and hospitals.
        Uses geographic bounding box calculated from user coordinates and search radius.
        """
        safe_radius = max(1.0, float(radius_km))
        d_lat = safe_radius / 111.0
        cos_lat = math.cos(math.radians(lat))
        d_lon = safe_radius / (111.0 * cos_lat) if abs(cos_lat) > 1e-4 else d_lat

        min_lat = round(lat - d_lat, 4)
        max_lat = round(lat + d_lat, 4)
        min_lon = round(lon - d_lon, 4)
        max_lon = round(lon + d_lon, 4)
        viewbox_str = f"{min_lon},{max_lat},{max_lon},{min_lat}"

        clinics: List[Dict[str, Any]] = []
        seen_coords = set()

        search_terms = ["dermatology", "skin clinic", "dermatologist", "clinic", "hospital"]
        headers = {
            "User-Agent": "DermAssistAI-Production/2.0 (Clinical Triage Research; contact@dermassist.ai)",
            "Accept": "application/json"
        }

        for term in search_terms:
            if len(clinics) >= 8:
                break
            try:
                params = urllib.parse.urlencode({
                    "format": "json",
                    "addressdetails": "1",
                    "q": term,
                    "viewbox": viewbox_str,
                    "bounded": "1",
                    "limit": "6"
                })
                req = urllib.request.Request(f"{self.NOMINATIM_URL}?{params}", headers=headers)
                with urllib.request.urlopen(req, timeout=4.0) as response:
                    if response.status == 200:
                        items = json.loads(response.read().decode("utf-8"))
                        for item in items:
                            c_lat = float(item.get("lat", 0.0))
                            c_lon = float(item.get("lon", 0.0))
                            coord_key = (round(c_lat, 3), round(c_lon, 3))
                            if coord_key in seen_coords:
                                continue
                            seen_coords.add(coord_key)

                            name = item.get("name") or item.get("display_name", "").split(",")[0].strip() or "Specialized Medical Center"
                            dist_km = calculate_haversine_distance(lat, lon, c_lat, c_lon)

                            addr_dict = item.get("address", {})
                            parts = [addr_dict.get(k) for k in ["road", "suburb", "city_district", "city"] if addr_dict.get(k)]
                            address_str = ", ".join(parts) if parts else item.get("display_name", "Medical District")

                            clinics.append({
                                "name": name,
                                "lat": c_lat,
                                "lon": c_lon,
                                "distance_km": dist_km,
                                "address": address_str,
                                "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={c_lat},{c_lon}"
                            })
            except Exception as exc:
                logger.warning(f"Nominatim query for term '{term}' failed: {exc}")
                continue

        # Sort ascending by distance
        clinics.sort(key=lambda x: x["distance_km"])
        return clinics
