// Clinic search straight from OpenStreetMap Overpass (CORS-enabled), so results
// don't depend on the backend deploy. Dermatology first, then nearest.

const OVERPASS_URLS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
];
const DERM_KEYWORDS = ["derma", "skin", "cutaneous", "laser", "aesthetic", "cosmetic"];
const MAX_RESULTS = 12;

export function haversineKm(lat1, lon1, lat2, lon2) {
  const r = 6371;
  const toRad = (d) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return Math.round(r * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)) * 100) / 100;
}

function isDermatology(tags) {
  const spec = `${tags["healthcare:speciality"] || ""};${tags.healthcare || ""}`.toLowerCase();
  if (spec.includes("dermatolog")) return true;
  const name = `${tags.name || ""} ${tags["name:en"] || ""}`.toLowerCase();
  return DERM_KEYWORDS.some((k) => name.includes(k));
}

function formatAddress(tags) {
  if (tags["addr:full"]) return tags["addr:full"];
  const street = [tags["addr:housenumber"], tags["addr:street"]].filter(Boolean).join(" ");
  const parts = [street, tags["addr:suburb"] || tags["addr:neighbourhood"], tags["addr:city"]].filter(Boolean);
  return parts.join(", ") || "Address not listed";
}

function buildQuery(lat, lon, radiusM) {
  // Tag-indexed filters only (cheap); dermatology is classified client-side.
  const around = `(around:${radiusM},${lat},${lon})`;
  return `[out:json][timeout:25];
(
  nwr["healthcare"]${around};
  nwr["amenity"~"^(clinic|doctors|hospital)$"]${around};
);
out center tags;`;
}

async function queryOverpass(query) {
  let lastErr;
  for (const url of OVERPASS_URLS) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 30000);
      const res = await fetch(url, {
        method: "POST",
        body: new URLSearchParams({ data: query }),
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      lastErr = err;
    }
  }
  throw lastErr || new Error("Overpass unavailable");
}

export async function searchClinics(lat, lon, radiusKm = 10) {
  const radiusM = Math.round(Math.min(Math.max(1, Number(radiusKm)), 50) * 1000);
  const data = await queryOverpass(buildQuery(lat, lon, radiusM));
  const seen = new Set();
  const places = [];
  for (const el of data.elements || []) {
    const c = el.center || el;
    if (typeof c.lat !== "number" || typeof c.lon !== "number") continue;
    const tags = el.tags || {};
    const name = tags["name:en"] || tags.name;
    if (!name) continue;
    const key = `${name.trim().toLowerCase()}|${c.lat.toFixed(3)}|${c.lon.toFixed(3)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const derm = isDermatology(tags);
    const kind = (tags.amenity || tags.healthcare || "clinic").replace(/_/g, " ");
    places.push({
      id: `${el.type}/${el.id}`,
      name,
      lat: c.lat,
      lon: c.lon,
      distance_km: haversineKm(lat, lon, c.lat, c.lon),
      address: formatAddress(tags),
      phone: tags.phone || tags["contact:phone"] || null,
      category: derm ? "Dermatology" : kind.charAt(0).toUpperCase() + kind.slice(1),
      is_dermatology: derm,
      directions_url: `https://www.google.com/maps/dir/?api=1&destination=${c.lat},${c.lon}`,
    });
  }
  places.sort((a, b) => (a.is_dermatology === b.is_dermatology ? a.distance_km - b.distance_km : a.is_dermatology ? -1 : 1));
  return places.slice(0, MAX_RESULTS);
}
