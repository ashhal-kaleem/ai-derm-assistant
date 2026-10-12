import React, { useState } from "react";
import { Camera, Cloud, Sun, Activity, AlertTriangle, ShieldCheck, HelpCircle } from "lucide-react";
import { SoftAurora } from "@/components/ui/soft-aurora";
import { BlurText } from "@/components/ui/blur-text";
import { Stepper } from "@/components/ui/stepper";
import { FileUpload } from "@/components/ui/file-upload";
import { Button } from "@/components/ui/stateful-button";
import { ImageScanLoader } from "@/components/ui/image-scan-loader";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { API_BASE_URL } from "@/config";

const WORKFLOW_STEPS = [
  { id: 1, title: "1. Capture" },
  { id: 2, title: "2. Standardize" },
  { id: 3, title: "3. ONNX Inference" },
  { id: 4, title: "4. Clinical Report" },
];

export default function ScanScreen({ onAnalysisComplete, addToast }) {
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [saveToCloud, setSaveToCloud] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleFilesChange = (files) => {
    setSelectedFiles(files);
    if (files && files[0]) {
      const reader = new FileReader();
      reader.onload = (e) => setPreviewUrl(e.target.result);
      reader.readAsDataURL(files[0]);
    } else {
      setPreviewUrl(null);
    }
  };

  const handleAnalyzeClick = async () => {
    if (!selectedFiles.length) {
      if (addToast) {
        addToast({
          type: "error",
          title: "Image Required",
          message: "Please upload or capture a skin lesion image before starting analysis.",
        });
      }
      return;
    }

    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append("file", selectedFiles[0]);
    formData.append("save_to_cloud", saveToCloud ? "true" : "false");

    try {
      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Analysis failed (HTTP ${response.status})`);
      }

      const data = await response.json();
      // Keep loader running briefly so animations finish smoothly
      setTimeout(() => {
        setIsAnalyzing(false);
        if (onAnalysisComplete) {
          onAnalysisComplete(data, previewUrl);
        }
        if (addToast) {
          addToast({
            type: "success",
            title: "Analysis Complete",
            message: `Identified ${data.class_name} with ${(data.confidence * 100).toFixed(1)}% confidence.`,
          });
        }
      }, 1800);
    } catch (err) {
      setIsAnalyzing(false);
      if (addToast) {
        addToast({
          type: "error",
          title: "Inference Error",
          message: err.message || "Failed to reach inference server.",
        });
      }
    }
  };

  return (
    <div className="relative w-full">
      {/* 5. Image Scan Loader Overlay */}
      <ImageScanLoader active={isAnalyzing} imagePreview={previewUrl} />

      {/* 8. Hero with Soft Aurora Background */}
      <SoftAurora className="pt-28 pb-14 px-4 text-center">
        <div className="max-w-4xl mx-auto flex flex-col items-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-100/80 border border-emerald-500/20 text-emerald-800 text-xs font-semibold mb-4 shadow-xs">
            <Activity className="w-3.5 h-3.5 text-emerald-600" />
            <span>HAM10000 Validated • 7-Class Clinical Triage</span>
          </div>

          {/* 10. Hero Heading with Blur Text */}
          <BlurText
            text="Clinical Triage & Skin Lesion Analysis"
            className="text-3xl sm:text-5xl font-extrabold tracking-tight text-[#064E3B] font-heading mb-4 text-center"
          />

          <p className="text-slate-600 text-sm sm:text-base max-w-xl mx-auto mb-6 leading-relaxed">
            Upload or photograph a skin lesion for preliminary screening and visual heatmap analysis.
          </p>

          {/* 12. Stepper Component */}
          <Stepper steps={WORKFLOW_STEPS} currentStep={previewUrl ? 2 : 1} className="mb-6" />
        </div>
      </SoftAurora>

      {/* Main Workspace Container */}
      <div className="max-w-4xl mx-auto px-4 pb-20 space-y-8">
        {/* 1. File Upload Box (Aceternity) */}
        <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-xl shadow-emerald-950/5 border border-emerald-500/20">
          <FileUpload onChange={handleFilesChange} />

          {/* Action Row: Camera trigger & Cloud Toggle */}
          <div className="mt-6 pt-5 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Camera Capture Input */}
            <label className="flex items-center gap-2 text-xs font-medium text-slate-600 hover:text-emerald-700 cursor-pointer p-2 rounded-xl hover:bg-emerald-50 transition-colors">
              <Camera className="w-4 h-4 text-emerald-600" />
              <span>Capture via Device Camera</span>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFilesChange(Array.from(e.target.files));
                  }
                }}
              />
            </label>

            {/* Cloud Storage Toggle */}
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer select-none">
                <Cloud className="w-4 h-4 text-emerald-600" />
                <span>Save scan to cloud archive</span>
                <input
                  type="checkbox"
                  checked={saveToCloud}
                  onChange={(e) => setSaveToCloud(e.target.checked)}
                  className="w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500"
                />
              </label>
            </div>
          </div>
        </div>

        {/* 3. Stateful Analyze Button (Aceternity) */}
        <div className="flex flex-col items-center justify-center gap-2">
          <Button
            onClick={handleAnalyzeClick}
            className="w-full sm:w-auto text-sm px-8 py-3.5 shadow-xl shadow-emerald-700/25"
          >
            Run Clinical Analysis
          </Button>
          <span className="text-[11px] font-mono text-slate-400">
            {selectedFiles.length > 0 ? "Ready for inference" : "Upload an image above to start"}
          </span>
        </div>

        {/* 11. Photo Tips Bento / Spotlight Cards (React Bits) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
          <SpotlightCard>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-3">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h4 className="font-heading font-bold text-sm text-slate-900 mb-1">
              Macro Focus (10-15 cm)
            </h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              Ensure lesion fills 50% of the viewport with sharp, discernible borders. Avoid shaky or motion-blurred shots.
            </p>
          </SpotlightCard>

          <SpotlightCard>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-3">
              <Sun className="w-5 h-5" />
            </div>
            <h4 className="font-heading font-bold text-sm text-slate-900 mb-1">
              Uniform Diffuse Light
            </h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              Use bright, natural daylight. Avoid harsh direct camera flash glare or heavy surrounding cast shadows.
            </p>
          </SpotlightCard>

          <SpotlightCard>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-3">
              <HelpCircle className="w-5 h-5" />
            </div>
            <h4 className="font-heading font-bold text-sm text-slate-900 mb-1">
              Clear Unobstructed Field
            </h4>
            <p className="text-xs text-slate-500 leading-relaxed">
              Gently part hair and remove bandages. Optional: place a 1-cent coin or metric ruler 1 cm alongside for scale.
            </p>
          </SpotlightCard>
        </div>

        {/* 14. Medical Disclaimer Alert (shadcn/ui Alert) */}
        <Alert variant="warning">
          <AlertTriangle className="w-4 h-4" />
          <AlertTitle>Clinical Disclaimer & Regulatory Scope</AlertTitle>
          <AlertDescription>
            DermAssist AI is an educational clinical triage assistance tool trained on the HAM10000 benchmark. It does not replace a physical dermoscopy consultation or histopathological biopsy.
          </AlertDescription>
        </Alert>
      </div>
    </div>
  );
}
