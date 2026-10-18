// Clinic search straight from OpenStreetMap Overpass (CORS-enabled), so results
// don't depend on the backend deploy. Dermatology first, then nearest.

const OVERPASS_URLS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
];
const DERM_STRONG = ["derma", "skin", "cutaneous", "cosmetolog"];
const DERM_WEAK = ["laser", "aesthetic", "cosmetic"];
const NOT_DERM = /\b(dental|dentist|dento|ent|eye|hearing|vision|kidney|gynae)\b/i;
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
  if (DERM_STRONG.some((k) => name.includes(k))) return true;
  return DERM_WEAK.some((k) => name.includes(k)) && !NOT_DERM.test(name);
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

const PHOTON_URL = "https://photon.komoot.io/api/";
const PHOTON_TERMS = ["skin", "derma", "dermatology", "dermatologist", "laser", "cosmetic", "aesthetic", "hospital", "clinic", "medical"];
const PHOTON_TAGS = ["amenity:hospital", "amenity:clinic", "amenity:doctors", "healthcare"];
const EXCLUDED_VALUES = new Set(["dentist", "veterinary", "pharmacy", "parking", "optometrist", "physiotherapist"]);

function bboxAround(lat, lon, radiusKm) {
  const dLat = radiusKm / 111;
  const dLon = radiusKm / (111 * Math.cos((lat * Math.PI) / 180));
  return [lon - dLon, lat - dLat, lon + dLon, lat + dLat].map((v) => v.toFixed(4)).join(",");
}

async function photonQuery(term, lat, lon, bbox) {
  const params = new URLSearchParams({ q: term, lat: String(lat), lon: String(lon), bbox, limit: "40" });
  PHOTON_TAGS.forEach((t) => params.append("osm_tag", t));
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const res = await fetch(`${PHOTON_URL}?${params}`, { signal: controller.signal });
    if (!res.ok) throw new Error(`Photon HTTP ${res.status}`);
    return (await res.json()).features || [];
  } finally {
    clearTimeout(timer);
  }
}

async function searchPhoton(lat, lon, radiusKm) {
  const bbox = bboxAround(lat, lon, radiusKm);
  const results = await Promise.allSettled(PHOTON_TERMS.map((t) => photonQuery(t, lat, lon, bbox)));
  if (results.every((r) => r.status === "rejected")) throw new Error("Photon unavailable");
  const elements = [];
  for (const r of results) {
    if (r.status !== "fulfilled") continue;
    for (const f of r.value) {
      const p = f.properties || {};
      if (!p.name || EXCLUDED_VALUES.has(p.osm_value)) continue;
      const [fLon, fLat] = (f.geometry && f.geometry.coordinates) || [];
      const tags = {
        name: p.name,
        [p.osm_key]: p.osm_value,
        "addr:housenumber": p.housenumber,
        "addr:street": p.street,
        "addr:suburb": p.district || p.locality,
        "addr:city": p.city,
      };
      elements.push({ type: p.osm_type, id: p.osm_id, lat: fLat, lon: fLon, tags });
    }
  }
  return elements;
}

function toPlaces(elements, lat, lon, radiusKm) {
  const seen = new Set();
  const places = [];
  for (const el of elements) {
    const c = el.center || el;
    if (typeof c.lat !== "number" || typeof c.lon !== "number") continue;
    const tags = el.tags || {};
    const name = tags["name:en"] || tags.name;
    if (!name) continue;
    const key = `${name.trim().toLowerCase()}|${c.lat.toFixed(3)}|${c.lon.toFixed(3)}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const dist = haversineKm(lat, lon, c.lat, c.lon);
    if (dist > radiusKm) continue;
    const derm = isDermatology(tags);
    const kind = (tags.amenity || tags.healthcare || "clinic").replace(/_/g, " ");
    places.push({
      id: `${el.type}/${el.id}`,
      name,
      lat: c.lat,
      lon: c.lon,
      distance_km: dist,
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

// Photon (komoot) first: fast, CORS-enabled, no strict rate limit. Overpass as backup.
export async function searchClinics(lat, lon, radiusKm = 10) {
  const radius = Math.min(Math.max(1, Number(radiusKm)), 50);
  try {
    const places = toPlaces(await searchPhoton(lat, lon, radius), lat, lon, radius);
    if (places.length) return places;
  } catch (err) {
    console.warn("Photon search failed, trying Overpass:", err);
  }
  const data = await queryOverpass(buildQuery(lat, lon, Math.round(radius * 1000)));
  return toPlaces(data.elements || [], lat, lon, radius);
}
