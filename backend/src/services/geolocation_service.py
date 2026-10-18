"""Geolocation service: nearby dermatologists and medical centres from OpenStreetMap Overpass."""

import json
import logging
import math
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("dermassist.geolocation")

MAX_RESULTS = 12
DERM_KEYWORDS = ("derma", "skin", "cutaneous", "laser", "aesthetic", "cosmetic")


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


def is_dermatology(tags: Dict[str, str]) -> bool:
    """True when OSM tags or the name mark the place as a dermatology / skin provider."""
    speciality = (tags.get("healthcare:speciality", "") + ";" + tags.get("healthcare", "")).lower()
    if "dermatolog" in speciality:
        return True
    name = (tags.get("name", "") + " " + tags.get("name:en", "")).lower()
    return any(k in name for k in DERM_KEYWORDS)


def format_address(tags: Dict[str, str]) -> str:
    if tags.get("addr:full"):
        return tags["addr:full"]
    parts = [
        " ".join(p for p in (tags.get("addr:housenumber", ""), tags.get("addr:street", "")) if p),
        tags.get("addr:suburb", "") or tags.get("addr:neighbourhood", ""),
        tags.get("addr:city", ""),
    ]
    return ", ".join(p for p in parts if p) or "Address not listed"


class ClinicSearchError(RuntimeError):
    """Raised when every Overpass mirror failed."""


class GeolocationService:
    """Fetches dermatologists first, then other clinics and hospitals, nearest first."""

    OVERPASS_URLS = (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    )

    def _build_query(self, lat: float, lon: float, radius_m: int) -> str:
        around = f"(around:{radius_m},{lat},{lon})"
        return f"""
[out:json][timeout:20];
(
  nwr["healthcare"="dermatology"]{around};
  nwr["healthcare:speciality"~"dermatolog",i]{around};
  nwr["name"~"derma|skin",i]["amenity"~"clinic|doctors|hospital"]{around};
  nwr["name"~"derma|skin",i]["healthcare"]{around};
  nwr["amenity"~"^(clinic|doctors|hospital)$"]["name"]{around};
);
out center tags;
"""

    def _query(self, query: str) -> Dict[str, Any]:
        headers = {
            "User-Agent": "DermAssistAI/2.0 (open-source skin lesion triage tool)",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        last_exc: Exception = ClinicSearchError("no mirrors configured")
        for url in self.OVERPASS_URLS:
            try:
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=25.0) as response:
                    return json.loads(response.read().decode("utf-8"))
            except Exception as exc:  # try the next mirror
                logger.warning(f"Overpass mirror {url} failed: {exc}")
                last_exc = exc
        raise ClinicSearchError(str(last_exc))

    def search_clinics(self, lat: float, lon: float, radius_km: float = 10.0) -> List[Dict[str, Any]]:
        """
        Return up to MAX_RESULTS places: dermatology providers first, each group nearest first.
        Raises ClinicSearchError when the map data source can't be reached.
        """
        radius_m = int(min(max(1.0, float(radius_km)), 50.0) * 1000)
        result = self._query(self._build_query(lat, lon, radius_m))

        seen: set = set()
        places: List[Tuple[bool, float, Dict[str, Any]]] = []
        for item in result.get("elements", []):
            centre = item.get("center") or item
            c_lat, c_lon = centre.get("lat"), centre.get("lon")
            if c_lat is None or c_lon is None:
                continue
            tags = item.get("tags", {})
            name = tags.get("name:en") or tags.get("name")
            if not name:
                continue
            key = (name.strip().lower(), round(float(c_lat), 3), round(float(c_lon), 3))
            if key in seen:
                continue
            seen.add(key)

            derm = is_dermatology(tags)
            dist = calculate_haversine_distance(lat, lon, float(c_lat), float(c_lon))
            kind = "Dermatology" if derm else tags.get("amenity", tags.get("healthcare", "clinic")).replace("_", " ").title()
            places.append((derm, dist, {
                "name": name,
                "lat": float(c_lat),
                "lon": float(c_lon),
                "distance_km": dist,
                "address": format_address(tags),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "category": kind,
                "is_dermatology": derm,
                "directions_url": f"https://www.google.com/maps/dir/?api=1&destination={c_lat},{c_lon}",
            }))

        places.sort(key=lambda p: (not p[0], p[1]))
        return [p[2] for p in places[:MAX_RESULTS]]
