import React, { useState } from "react";
import {
  FileDown,
  MapPin,
  RefreshCw,


  BrainCircuit,

  Loader2,
  CheckCircle2,
  AlertTriangle
} from "lucide-react";
import { Compare } from "@/components/ui/compare";
import { AnimatedBadge } from "@/components/ui/animated-badge";
import { Progress } from "@/components/ui/progress";
import { CountUp } from "@/components/ui/count-up";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";
import { ProbabilityBarChart } from "@/components/ui/probability-bar-chart";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { API_BASE_URL, STATIC_KNOWLEDGE_CARDS } from "@/config";
import SaveToHistory from "@/components/SaveToHistory";

export default function ResultScreen({
  prediction,
  originalImage,
  onReset,
  onFindDoctors,
  onViewHistory,
  addToast
}) {
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  if (!prediction) {
    return (
      <div className="pt-28 pb-16 px-4 text-center">
        <p className="text-slate-500 mb-4">No active analysis result found.</p>
        <button
          onClick={onReset}
          className="px-5 py-2.5 rounded-full bg-emerald-600 text-white font-medium text-xs"
        >
          Return to Scanner
        </button>
      </div>
    );
  }

  const confidencePercent = (prediction.confidence * 100);
  const CLASS_LABELS = [
    "Actinic Keratosis", "Basal Cell Carcinoma", "Benign Keratosis", "Dermatofibroma",
    "Melanoma", "Melanocytic Nevus (Mole)", "Vascular Lesion",
  ];
  const rankedAlternatives = Array.isArray(prediction.all_probs)
    ? prediction.all_probs
        .map((p, i) => ({ name: CLASS_LABELS[i], p: Number(p) || 0 }))
        .sort((a, b) => b.p - a.p)
        .slice(1, 3)
        .filter((a) => a.p >= 0.1)
    : [];
  const isLowConfidence =
    (prediction.confidence ?? 1) < 0.6 || String(prediction.uncertainty).toLowerCase() === "high";
  const uncertaintyLabel =
    confidencePercent >= 85 ? "Low Uncertainty" : confidencePercent >= 65 ? "Moderate Uncertainty" : "High Uncertainty";
  const uncertaintyColor =
    confidencePercent >= 85
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : confidencePercent >= 65
      ? "bg-amber-50 text-amber-700 border-amber-200"
      : "bg-red-50 text-red-700 border-red-200";

  const aiExplanation =
    prediction.llm_explanation ||
    STATIC_KNOWLEDGE_CARDS[prediction.class_name] ||
    "Clinical correlation and physical examination by a certified dermatologist recommended.";

  // Handle PDF report download from POST /report
  const handleDownloadPdf = async () => {
    setIsDownloadingPdf(true);
    try {
      const res = await fetch(`${API_BASE_URL}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prediction: {
            predicted_class: prediction.predicted_class || prediction.top_class || "nv",
            class_name: prediction.class_name || prediction.top_name || "Melanocytic Nevi",
            confidence: prediction.confidence || prediction.calibrated_confidence || 0.9,
            risk_level: prediction.risk_level || "green",
            risk_label: prediction.risk_label || "Benign",
            llm_explanation: aiExplanation,
            heatmap_b64: prediction.heatmap_b64,
            image_b64: originalImage
          },
          history: []
        })
      });

      if (!res.ok) throw new Error("PDF report generation failed.");
      const data = await res.json();
      const byteCharacters = atob(data.pdf_b64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dermassist_report_${prediction.class_name.toLowerCase().replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();

      if (addToast) {
        addToast({
          type: "success",
          title: "Report Downloaded",
          message: "Clinical PDF summary saved successfully."
        });
      }
    } catch (err) {
      if (addToast) {
        addToast({
          type: "error",
          title: "Download Failed",
          message: err.message
        });
      }
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  return (
    <div className="pt-32 pb-20 px-4 max-w-5xl mx-auto space-y-8">
      {/* Top Controls Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#064E3B] font-heading mt-1">
            Diagnostic & Triage Report
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full border border-slate-200 bg-white text-slate-700 text-xs font-semibold hover:bg-slate-50 transition-colors shadow-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Scan Another
          </button>
          <button
            onClick={onFindDoctors}
            className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 shadow-sm transition-colors"
          >
            <MapPin className="w-3.5 h-3.5" /> Find Clinics
          </button>
        </div>
      </div>

      {isLowConfidence && (
        <Alert variant="warning">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>Image unclear: the AI isn't confident about this result</AlertTitle>
          <AlertDescription>
            <p>
              Retake the photo close to the spot (about 10 cm away), in daylight, in focus, with only the lesion filling
              most of the frame.
              {rankedAlternatives.length > 0 && (
                <> It could also be {rankedAlternatives.map((a) => `${a.name} (${Math.round(a.p * 100)}%)`).join(" or ")}.</>
              )}{" "}
              Please show it to a dermatologist either way.
            </p>
          </AlertDescription>
        </Alert>
      )}

      {/* Main Grid: Visualizer & Result Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Compare Slider (6 cols) */}
        <div className="lg:col-span-6 flex flex-col gap-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-500 px-1">
            <span className="font-semibold text-slate-800">Visual Evidence Overlay</span>
            <span>Drag handle to compare</span>
          </div>

          <Compare
            firstImage={originalImage}
            secondImage={prediction.heatmap_b64 || originalImage}
            className="w-full"
          />

        </div>

        {/* Right Column: Diagnostic Cards & Badges (6 cols) */}
        <div className="lg:col-span-6 flex flex-col gap-5">
          {/* Diagnostic Result Card (Spotlight Card) */}
          <SpotlightCard className="p-6">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <p className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
                  Primary Classification
                </p>
                <h3 className="text-2xl sm:text-3xl font-bold font-heading text-slate-900 mt-0.5">
                  {prediction.class_name}
                </h3>
              </div>

              {/* 8. Animated Risk Badge */}
              <AnimatedBadge level={prediction.risk_level} label={prediction.risk_label} />
            </div>

            {/* Confidence Progress & CountUp */}
            <div className="space-y-2 mb-5">
              <div className="flex items-center justify-between text-xs font-medium">
                <span className="text-slate-600">Calibrated Confidence:</span>
                <span className="font-mono text-base font-bold text-slate-900">
                  <CountUp value={confidencePercent} />
                </span>
              </div>
              <Progress
                value={confidencePercent}
                barClassName={
                  prediction.risk_level === "red"
                    ? "bg-red-500"
                    : prediction.risk_level === "yellow"
                    ? "bg-amber-500"
                    : "bg-emerald-600"
                }
              />
            </div>

            {/* Chips: Uncertainty & Model info */}
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
              <span className={`text-[11px] font-mono px-2.5 py-1 rounded-full border font-semibold ${uncertaintyColor}`}>
                {uncertaintyLabel}
              </span>
            </div>
          </SpotlightCard>

          {/* AI Clinical Advisory Narrative Card */}
          <div className="bg-white rounded-3xl p-6 border border-emerald-500/20 shadow-sm space-y-3">
            <div className="flex items-center gap-2 text-xs font-bold font-heading text-emerald-800">
              <BrainCircuit className="w-4 h-4 text-emerald-600" />
              <span>Clinical Advisory Assessment</span>
            </div>

            {/* 12. Text Generate Effect for AI Explanation */}
            <div className="text-xs sm:text-sm text-slate-700 leading-relaxed font-sans bg-emerald-50/40 p-4 rounded-2xl border border-emerald-500/10">
              <TextGenerateEffect words={aiExplanation} />
            </div>
          </div>

          {/* Action Buttons: PDF Download & Track Lesion */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
            <button
              onClick={handleDownloadPdf}
              disabled={isDownloadingPdf}
              className="flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-[#064E3B] hover:bg-[#059669] text-white text-xs font-semibold shadow-md transition-colors disabled:opacity-50"
            >
              {isDownloadingPdf ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Preparing PDF...
                </>
              ) : (
                <>
                  <FileDown className="w-4 h-4" /> Download Clinical PDF
                </>
              )}
            </button>

            <button
              onClick={onFindDoctors}
              className="flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-white hover:bg-slate-50 border border-emerald-300 text-emerald-900 text-xs font-semibold shadow-xs transition-colors"
            >
              <MapPin className="w-4 h-4 text-emerald-700" /> Find Nearby Clinics
            </button>
          </div>
        </div>
      </div>
        <SaveToHistory
            prediction={prediction}
             originalImage={originalImage}
             addToast={addToast}
             onViewHistory={onViewHistory}
         />
      {/* 11. 7-Class Probability Bar Chart Section */}
      <div className="pt-4">
        <ProbabilityBarChart probabilities={prediction.probabilities || {}} />
      </div>

      {/* 14. Medical Disclaimer Warning */}
      <Alert variant="warning">
        <AlertTriangle className="w-4 h-4" />
        <AlertTitle>Mandatory Medical Protocol</AlertTitle>
        <AlertDescription>
          This automated classification is generated for clinical education and triage support. Never delay formal dermatological consultation based on automated screening results.
        </AlertDescription>
      </Alert>

    </div>
  );
}
