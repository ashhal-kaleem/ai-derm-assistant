import React, { useState, useEffect, useRef } from "react";
import {
  MapPin,
  Navigation,
  Phone,
  ExternalLink,
  Loader2,
  Building2,
  Compass,
  Star,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { PinContainer } from "@/components/ui/3d-pin";
import { searchClinics, googleMapsDermSearchUrl, googleMapsPlaceUrl } from "@/lib/clinicSearch";

export const ClinicFinderScreen = ({ onStartScan, addToast }) => {
  const [clinics, setClinics] = useState([]);
  const [radiusKm, setRadiusKm] = useState(10);
  const [userLocation, setUserLocation] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const hasSearched = useRef(false);

  // Fallback when location is unavailable or denied: Lahore city centre
  const defaultCoords = { lat: 31.5204, lon: 74.3587 };

  // Ask for the user's location once on first load
  useEffect(() => {
    handleUseMyLocation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-run the search when the radius changes (after the first location fix)
  useEffect(() => {
    if (!hasSearched.current) return;
    const loc = userLocation || defaultCoords;
    fetchClinics(loc.lat, loc.lon, radiusKm);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [radiusKm]);

  const GEO_ERROR_REASONS = {
    1: "location permission is blocked for this site",
    2: "your device's location service is off (check Windows/macOS location settings)",
    3: "location request timed out",
  };

  const getPosition = (options) =>
    new Promise((resolve, reject) => navigator.geolocation.getCurrentPosition(resolve, reject, options));

  // Approximate city-level location from the IP address (no permission needed)
  const getIpLocation = async () => {
    const res = await fetch("https://ipwho.is/");
    const data = await res.json();
    if (!data.success || typeof data.latitude !== "number") throw new Error("IP lookup failed");
    return { lat: data.latitude, lon: data.longitude, city: data.city };
  };

  const handleUseMyLocation = async () => {
    setIsLocating(true);
    let reason = "your browser doesn't support location";

    if (navigator.geolocation) {
      // Fast network-based fix first, then one high-accuracy retry (GPS/Wi-Fi)
      const attempts = [
        { enableHighAccuracy: false, timeout: 15000, maximumAge: 10 * 60 * 1000 },
        { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
      ];
      for (const opts of attempts) {
        try {
          const pos = await getPosition(opts);
          const loc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
          setIsLocating(false);
          setUserLocation(loc);
          fetchClinics(loc.lat, loc.lon, radiusKm);
          if (addToast) {
            addToast({ type: "success", title: "Location Acquired", message: "Showing clinics near you." });
          }
          return;
        } catch (err) {
          reason = GEO_ERROR_REASONS[err?.code] || reason;
          if (err?.code === 1) break; // permission denied: retrying won't help
        }
      }
    }

    try {
      const ipLoc = await getIpLocation();
      setIsLocating(false);
      setUserLocation({ lat: ipLoc.lat, lon: ipLoc.lon });
      fetchClinics(
        ipLoc.lat,
        ipLoc.lon,
        radiusKm,
        `Using your approximate location${ipLoc.city ? ` (${ipLoc.city})` : ""} because ${reason}.`
      );
    } catch {
      setIsLocating(false);
      setUserLocation(null);
      fetchClinics(defaultCoords.lat, defaultCoords.lon, radiusKm, `Showing clinics near Lahore because ${reason}.`);
    }
  };

  const fetchClinics = async (lat, lon, radius, notice = null) => {
    hasSearched.current = true;
    setIsLoading(true);
    setErrorMsg(notice);
    try {
      // Primary: query OpenStreetMap directly from the browser
      const list = await searchClinics(lat, lon, radius);
      setClinics(list);
    } catch (err) {
      console.error("Clinic search failed:", err);
      setErrorMsg("Map data service is busy right now. Please try again in a minute.");
      setClinics([]);
    } finally {
      setIsLoading(false);
    }
  };

  const inRadius = clinics.filter((c) => c.distance_km == null || c.distance_km <= radiusKm);
  const outsideDerm = clinics.filter((c) => c.is_dermatology && c.distance_km > radiusKm);

  const renderClinicCard = (clinic) => {
            const mapDirectionsUrl =
              googleMapsPlaceUrl(clinic);

            return (
              <div
                key={clinic.id || `${clinic.name}-${clinic.lat}-${clinic.lon}`}
                className="bg-white rounded-3xl p-6 border border-emerald-500/20 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center shrink-0">
                      <Building2 className="w-5 h-5" />
                    </div>
                    <span className="text-[11px] font-mono bg-emerald-100/70 text-emerald-800 font-bold px-2.5 py-0.5 rounded-full">
                      {clinic.distance_km ? `${clinic.distance_km.toFixed(1)} km` : "Nearby"}
                    </span>
                  </div>

                  <h4 className="font-heading font-bold text-base text-slate-900 mb-1">
                    {clinic.name}
                  </h4>
                  {clinic.category && (
                    <span
                      className={`inline-block text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full mb-2 ${
                        clinic.is_dermatology ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {clinic.is_dermatology ? "Dermatology" : clinic.category}
                    </span>
                  )}
                  <p className="text-xs text-slate-500 leading-relaxed mb-4">
                    {clinic.address}
                  </p>

                  {clinic.phone && (
                    <div className="flex items-center gap-2 text-xs font-mono text-slate-600 mb-2">
                      <Phone className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{clinic.phone}</span>
                    </div>
                  )}

                  {clinic.rating && (
                    <div className="flex items-center gap-1.5 text-xs text-amber-600 font-mono font-bold">
                      <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                      <span>{clinic.rating} / 5.0 Specialist Rating</span>
                    </div>
                  )}
                </div>

                <div className="pt-5 mt-4 border-t border-slate-100 flex items-center justify-between">
                  <a
                    href={mapDirectionsUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 hover:text-emerald-900 transition-colors"
                  >
                    <span>View on Google Maps</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>

                </div>
              </div>
            );
  };

  return (
    <div className="pt-32 pb-20 px-4 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-emerald-700 bg-emerald-100/60 px-2.5 py-0.5 rounded-full">
            Clinical Referral Network
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#064E3B] font-heading mt-1">
            Dermatology Clinic Finder
          </h2>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleUseMyLocation}
            disabled={isLocating}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-50"
          >
            {isLocating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Navigation className="w-3.5 h-3.5" />
            )}
            <span>Use Current Location</span>
          </button>

          {/* Radius Selector */}
          <div className="flex items-center gap-1 bg-white border border-slate-200 px-3 py-1.5 rounded-full text-xs font-mono">
            <span className="text-slate-500">Radius:</span>
            <select
              value={radiusKm}
              onChange={(e) => setRadiusKm(Number(e.target.value))}
              className="bg-transparent font-bold text-emerald-800 focus:outline-none cursor-pointer"
            >
              <option value={5}>5 km</option>
              <option value={10}>10 km</option>
              <option value={25}>25 km</option>
              <option value={50}>50 km</option>
            </select>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Clinics Display Grid */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-600 mb-3" />
          <p className="text-xs font-mono">Scanning geolocated dermatology centers...</p>
        </div>
      ) : (
        <div className="space-y-10">
          {inRadius.length === 0 ? (
            <div className="bg-white rounded-3xl p-8 text-center border border-slate-200 max-w-md mx-auto">
              <Compass className="w-10 h-10 text-slate-400 mx-auto mb-2" />
              <h4 className="font-heading font-bold text-sm text-slate-800">No clinics listed within {radiusKm} km</h4>
              <p className="text-xs text-slate-500 mt-1">Try a larger radius.</p>
            </div>
          ) : (
            <section>
              <h3 className="font-heading font-bold text-lg text-slate-900 mb-1">Within {radiusKm} km</h3>
              {!inRadius.some((c) => c.is_dermatology) && (
                <p className="text-xs text-slate-500 mb-4">
                  No dermatologist is listed within {radiusKm} km. These hospitals and clinics may have a skin OPD.
                </p>
              )}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
                {inRadius.map(renderClinicCard)}
              </div>
            </section>
          )}

          {outsideDerm.length > 0 && (
            <section>
              <h3 className="font-heading font-bold text-lg text-slate-900 mb-1">Nearest dermatologists</h3>
              <p className="text-xs text-slate-500 mb-4">Outside your {radiusKm} km radius.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
                {outsideDerm.map(renderClinicCard)}
              </div>
            </section>
          )}
        </div>
      )}

      {!isLoading && (
        <div className="text-center">
          <a
            href={googleMapsDermSearchUrl((userLocation || defaultCoords).lat, (userLocation || defaultCoords).lon)}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 hover:text-emerald-900"
          >
            <span>See more dermatologists near you on Google Maps</span>
            <ExternalLink className="w-4 h-4" />
          </a>
          <p className="text-[11px] text-slate-400 mt-1">Listings from OpenStreetMap, which may not include every clinic.</p>
        </div>
      )}
    </div>
  );
};

export default ClinicFinderScreen;
