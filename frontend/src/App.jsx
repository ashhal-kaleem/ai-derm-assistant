import React, { useState, useEffect } from "react";
import { Sparkles, MapPin, ShieldAlert } from "lucide-react";
import { FloatingNav } from "@/components/ui/floating-navbar";
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

  const navItems = [
    { id: "scan", name: "Scan & Analyze", icon: <Sparkles className="w-3.5 h-3.5" /> },
    { id: "clinics", name: "Clinic Finder", icon: <MapPin className="w-3.5 h-3.5" /> },
  ];

  return (
    <div className="min-h-screen bg-[#ECFDF5] text-[#0F172A] flex flex-col font-sans selection:bg-emerald-200">
      {/* Permanent Medical Disclaimer Banner */}
      <div className="w-full bg-amber-500/10 border-b border-amber-500/20 px-4 py-2.5 text-xs text-amber-900 sticky top-0 z-[6000] backdrop-blur-md">
        <div className="max-w-5xl mx-auto flex items-center justify-center gap-2 text-center font-medium">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            <strong>PERMANENT MEDICAL DISCLAIMER:</strong> DermAssist AI is an educational clinical triage assistance tool. It does not provide medical diagnosis. Any suspicious skin lesion requires physical evaluation by a certified dermatologist.
          </span>
        </div>
      </div>

      {/* Floating Navbar (Aceternity) */}
      <FloatingNav
        navItems={navItems}
        currentScreen={currentScreen}
        setScreen={setCurrentScreen}
        serverOnline={serverOnline}
      />

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
