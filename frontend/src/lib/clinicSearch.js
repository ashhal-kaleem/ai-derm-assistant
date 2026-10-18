// Clinic search straight from OpenStreetMap Overpass (CORS-enabled), so results
// don't depend on the backend deploy. Dermatology first, then nearest.

const OVERPASS_URLS = [
  "https://overpass-api.de/api/interpreter",
  "https://overpass.kumi.systems/api/interpreter",
  "https://overpass.private.coffee/api/interpreter",
];
const DERM_STRONG = ["derma", "skin", "cutaneous", "cosmetolog"];
const DERM_WEAK = ["laser", "aesthetic", "cosmetic"];
const NOT_DERM = /\b(dental|dentist|dento|ent|eye|hearing|vision|kidney|gyn\w*|children|child|maternity|homeo\w*|herbal|vet\w*|psychiatr\w*|physio\w*)\b/i;
const DERM_SEARCH_MIN_KM = 25; // dermatologists are sparse: always look at least this far
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
const PHOTON_TERMS = ["skin", "derma", "dermatologist", "laser", "cosmetic", "hospital", "clinic"];
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
  // Retry any failed term once (Photon occasionally drops bursts)
  for (let i = 0; i < results.length; i++) {
    if (results[i].status === "rejected") {
      try {
        results[i] = { status: "fulfilled", value: await photonQuery(PHOTON_TERMS[i], lat, lon, bbox) };
      } catch {
        /* keep as rejected */
      }
    }
  }
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

function toPlaces(elements, lat, lon) {
  const places = [];
  for (const el of elements) {
    const c = el.center || el;
    if (typeof c.lat !== "number" || typeof c.lon !== "number") continue;
    const tags = el.tags || {};
    const name = tags["name:en"] || tags.name;
    if (!name) continue;
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
  return places;
}

// Same name within 1.5 km = same place (OSM often has a node and a building for one hospital)
function dedupe(places) {
  const kept = [];
  for (const p of places.sort((a, b) => a.distance_km - b.distance_km)) {
    const norm = p.name.trim().toLowerCase().replace(/\s+/g, " ");
    const dup = kept.some(
      (k) => k.name.trim().toLowerCase().replace(/\s+/g, " ") === norm && haversineKm(k.lat, k.lon, p.lat, p.lon) < 1.5
    );
    if (!dup) kept.push(p);
  }
  return kept;
}

function rank(places, radiusKm) {
  const unique = dedupe(places);
  // Dermatologists: nearest first, even beyond the chosen radius (they're rare in OSM)
  const derm = unique.filter((p) => p.is_dermatology && p.distance_km <= Math.max(radiusKm, DERM_SEARCH_MIN_KM)).slice(0, 6);
  // General hospitals/clinics inside the radius, skipping unrelated specialities
  const general = unique.filter((p) => !p.is_dermatology && p.distance_km <= radiusKm && !NOT_DERM.test(p.name));
  return [...derm, ...general].slice(0, MAX_RESULTS);
}

// Photon (komoot) first: fast, CORS-enabled, no strict rate limit. Overpass as backup.
export async function searchClinics(lat, lon, radiusKm = 10) {
  const radius = Math.min(Math.max(1, Number(radiusKm)), 50);
  const searchKm = Math.max(radius, DERM_SEARCH_MIN_KM);
  try {
    const places = rank(toPlaces(await searchPhoton(lat, lon, searchKm), lat, lon), radius);
    if (places.length) return places;
  } catch (err) {
    console.warn("Photon search failed, trying Overpass:", err);
  }
  const data = await queryOverpass(buildQuery(lat, lon, Math.round(radius * 1000)));
  return rank(toPlaces(data.elements || [], lat, lon), radius);
}

export function googleMapsDermSearchUrl(lat, lon) {
  return `https://www.google.com/maps/search/dermatologist/@${lat},${lon},13z`;
}
