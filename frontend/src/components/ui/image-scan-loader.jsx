import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Brain, Cpu, Layers, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";

const SCAN_STAGES = [
  { id: 1, text: "Normalizing Image Matrix (380x380)", icon: Cpu },
  { id: 2, text: "Analyzing Cellular Structure and Borders", icon: Brain },
  { id: 3, text: "Calibrating Probabilities", icon: ShieldCheck },
  { id: 4, text: "Extracting Visual Saliency Map", icon: Layers },
  { id: 5, text: "Generating Clinical Triage Narrative", icon: CheckCircle2 },
];

export const ImageScanLoader = ({ active = false, imagePreview = null }) => {
  const [currentStage, setCurrentStage] = useState(0);

  useEffect(() => {
    if (!active) {
      setCurrentStage(0);
      return;
    }
    const interval = setInterval(() => {
      setCurrentStage((prev) => (prev < SCAN_STAGES.length - 1 ? prev + 1 : prev));
    }, 650);
    return () => clearInterval(interval);
  }, [active]);

  if (!active) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[6000] flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-md"
      >
        <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-emerald-500/30 bg-white p-6 shadow-2xl text-center">
          {/* Laser Scanner Viewport if image is present */}
          <div className="relative mx-auto mb-6 h-48 w-48 overflow-hidden rounded-2xl border-2 border-emerald-500/40 bg-slate-900 shadow-inner">
            {imagePreview ? (
              <img src={imagePreview} alt="Scanning Lesion" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full items-center justify-center text-slate-500 font-mono text-xs">
                Processing image...
              </div>
            )}
            {/* Glowing Laser Scan Bar */}
            <motion.div
              animate={{ y: [0, 192, 0] }}
              transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
              className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-emerald-400 to-transparent shadow-[0_0_15px_#10B981]"
            />
            <div className="absolute inset-0 bg-emerald-500/10 mix-blend-overlay" />
          </div>

          <h3 className="font-heading text-lg font-bold text-slate-900">
            DermAssist Engine Analyzing
          </h3>
          <p className="mt-1 text-xs text-slate-500 font-mono">
            Deep learning skin lesion triage pipeline
          </p>

          {/* Stepped progress indicators */}
          <div className="mt-5 space-y-2 text-left">
            {SCAN_STAGES.map((stage, idx) => {
              const Icon = stage.icon;
              const isDone = idx < currentStage;
              const isCurrent = idx === currentStage;

              return (
                <div
                  key={stage.id}
                  className={cn(
                    "flex items-center gap-2.5 rounded-xl p-2 text-xs transition-all duration-300",
                    isCurrent
                      ? "bg-emerald-50 font-semibold text-emerald-900 border border-emerald-200"
                      : isDone
                      ? "text-slate-400 opacity-70"
                      : "text-slate-300 opacity-40"
                  )}
                >
                  <div
                    className={cn(
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-lg text-xs",
                      isCurrent
                        ? "bg-emerald-600 text-white animate-pulse"
                        : isDone
                        ? "bg-emerald-200 text-emerald-800"
                        : "bg-slate-100 text-slate-400"
                    )}
                  >
                    {isCurrent ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Icon className="h-3.5 w-3.5" />}
                  </div>
                  <span className="truncate">{stage.text}</span>
                </div>
              );
            })}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
