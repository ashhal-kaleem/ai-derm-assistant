import React, { useState, useEffect } from "react";
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
import { API_BASE_URL } from "@/config";

export const ClinicFinderScreen = ({ onStartScan, addToast }) => {
  const [clinics, setClinics] = useState([]);
  const [radiusKm, setRadiusKm] = useState(10);
  const [userLocation, setUserLocation] = useState(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Default coordinate if geolocation not active: 28.6139, 77.2090 (Delhi)
  const defaultCoords = { lat: 28.6139, lon: 77.2090 };

  useEffect(() => {
    fetchClinics(defaultCoords.lat, defaultCoords.lon, radiusKm);
  }, [radiusKm]);

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      if (addToast) {
        addToast({
          type: "error",
          title: "Geolocation Unsupported",
          message: "Your browser does not support automatic location discovery.",
        });
      }
      return;
    }

    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocating(false);
        const loc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setUserLocation(loc);
        fetchClinics(loc.lat, loc.lon, radiusKm);
        if (addToast) {
          addToast({
            type: "success",
            title: "Location Acquired",
            message: `Coordinates locked: ${loc.lat.toFixed(2)}, ${loc.lon.toFixed(2)}`,
          });
        }
      },
      (err) => {
        setIsLocating(false);
        setErrorMsg("Location access denied. Displaying reference clinics.");
        fetchClinics(defaultCoords.lat, defaultCoords.lon, radiusKm);
      },
      { timeout: 10000 }
    );
  };

  const fetchClinics = async (lat, lon, radius) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE_URL}/clinics?lat=${lat}&lon=${lon}&radius_km=${radius}`);
      if (res.ok) {
        const data = await res.json();
        const list = Array.isArray(data) ? data : data.clinics || [];
        setClinics(list);
      } else {
        throw new Error("Unable to retrieve nearby clinics.");
      }
    } catch {
      // Offline fallback dummy dermatologists
      setClinics([
        {
          id: 1,
          name: "Apollo Dermatology Center",
          address: "Sarita Vihar, Mathura Road, New Delhi",
          distance_km: 3.2,
          phone: "+91 11 2692 5858",
          rating: 4.8,
          lat: 28.5355,
          lon: 77.2882,
        },
        {
          id: 2,
          name: "Max Super Speciality Skin Clinic",
          address: "1, 2 Press Enclave Marg, Saket",
          distance_km: 5.7,
          phone: "+91 11 2651 5050",
          rating: 4.9,
          lat: 28.5273,
          lon: 77.2145,
        },
        {
          id: 3,
          name: "Fortis Skin & Laser Institute",
          address: "Sector B, Pocket 1, Aruna Asaf Ali Marg, Vasant Kunj",
          distance_km: 8.4,
          phone: "+91 11 4277 6222",
          rating: 4.7,
          lat: 28.5284,
          lon: 77.1611,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
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
      ) : clinics.length === 0 ? (
        <div className="bg-white rounded-3xl p-10 text-center border border-slate-200 max-w-md mx-auto">
          <Compass className="w-10 h-10 text-slate-400 mx-auto mb-2" />
          <h4 className="font-heading font-bold text-sm text-slate-800">
            No clinics found within {radiusKm} km
          </h4>
          <p className="text-xs text-slate-500 mt-1">Try increasing the radius to 25 km or 50 km.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pt-2">
          {clinics.map((clinic) => {
            const mapDirectionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
              clinic.name + " " + clinic.address
            )}`;

            return (
              <div
                key={clinic.id || clinic.name}
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
          })}
        </div>
      )}
    </div>
  );
};

export default ClinicFinderScreen;
