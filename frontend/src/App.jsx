import React, { useState, useEffect } from "react";
import { Scan, MapPin, ShieldAlert, Activity } from "lucide-react";
import { ToastStack } from "@/components/ui/animated-toast-stack";
import ScanScreen from "@/components/ScanScreen";
import ResultScreen from "@/components/ResultScreen";
import ClinicFinderScreen from "@/components/ClinicFinderScreen";
import Footer from "@/components/Footer";
import { API_BASE_URL } from "@/config";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState("scan");
  const [serverOnline, setServerOnline] = useState(null);
  const [toasts, setToasts] = useState([]);
  const [prediction, setPrediction] = useState(null);
  const [originalImage, setOriginalImage] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => setServerOnline(res.ok))
      .catch(() => setServerOnline(false));
  }, []);

  const addToast = (toast) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const handleAnalysisComplete = (result, image) => {
    setPrediction(result);
    setOriginalImage(image);
    setCurrentScreen("result");
  };

  return (
    <div className="min-h-screen bg-[#ECFDF5] text-[#0F172A] flex flex-col font-sans selection:bg-emerald-200">
      {/* Unified Clinical Header (Sticky) */}
      <header className="sticky top-0 z-[5000] w-full bg-white/95 backdrop-blur-md border-b border-emerald-950/10 shadow-xs">
        {/* Permanent Medical Disclaimer Banner */}
        <div className="w-full bg-amber-500/10 border-b border-amber-500/20 px-4 py-2 text-xs text-amber-950">
          <div className="max-w-6xl mx-auto flex items-center justify-center gap-2 text-center font-medium">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>PERMANENT MEDICAL DISCLAIMER:</strong> DermAssist AI is an educational clinical triage assistance tool. It does not provide medical diagnosis. Any suspicious skin lesion requires physical evaluation by a certified dermatologist.
            </span>
          </div>
        </div>

        {/* Clean Clinical Navbar */}
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-xs">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <span className="font-heading font-extrabold text-base tracking-tight text-[#064E3B]">
                DermAssist AI
              </span>
              <span className="hidden sm:inline-block ml-2 text-[10px] font-mono font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                HAM10000 Triage
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center gap-1.5">
            <button
              onClick={() => setCurrentScreen("scan")}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                currentScreen === "scan"
                  ? "bg-emerald-600 text-white shadow-xs"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Scan className="w-4 h-4" />
              <span>Scan & Analyze</span>
            </button>
            <button
              onClick={() => setCurrentScreen("clinics")}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold transition-all ${
                currentScreen === "clinics"
                  ? "bg-emerald-600 text-white shadow-xs"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <MapPin className="w-4 h-4" />
              <span>Clinic Finder</span>
            </button>
          </nav>

          {/* Live Engine Status */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 text-xs font-mono text-slate-600">
            <span
              className={`w-2 h-2 rounded-full ${
                serverOnline === true
                  ? "bg-emerald-500 animate-pulse"
                  : serverOnline === false
                  ? "bg-rose-500"
                  : "bg-amber-400"
              }`}
            />
            <span className="text-[11px] font-semibold hidden sm:inline">
              {serverOnline === true ? "ONNX Engine Online" : serverOnline === false ? "Offline" : "Connecting"}
            </span>
          </div>
        </div>
      </header>
      {/* Screen Router */}
      <main className="flex-1 w-full">
        {currentScreen === "scan" && (
          <ScanScreen
            onAnalysisComplete={handleAnalysisComplete}
            addToast={addToast}
          />
        )}

        {currentScreen === "result" && (
          <ResultScreen
            prediction={prediction}
            originalImage={originalImage}
            onReset={() => setCurrentScreen("scan")}
            onFindDoctors={() => setCurrentScreen("clinics")}
            addToast={addToast}
          />
        )}


        {currentScreen === "clinics" && (
          <ClinicFinderScreen
            onStartScan={() => setCurrentScreen("scan")}
            addToast={addToast}
          />
        )}
      </main>
      <Footer />

      {/* Animated Toast Stack (beUI) */}
      <ToastStack toasts={toasts} removeToast={removeToast} />
    </div>
  );
}
