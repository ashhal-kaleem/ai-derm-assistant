import React from "react";
import { cn } from "@/lib/utils";

const CLASS_CONFIG = {
  "Melanoma": { short: "MEL", color: "bg-red-500", text: "text-red-700", bg: "bg-red-50" },
  "Basal Cell Carcinoma": { short: "BCC", color: "bg-red-500", text: "text-red-700", bg: "bg-red-50" },
  "Actinic Keratosis": { short: "AKIEC", color: "bg-amber-500", text: "text-amber-700", bg: "bg-amber-50" },
  "Melanocytic Nevus": { short: "NV", color: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
  "Benign Keratosis": { short: "BKL", color: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
  "Dermatofibroma": { short: "DF", color: "bg-emerald-500", text: "text-emerald-700", bg: "bg-emerald-50" },
  "Vascular Lesion": { short: "VASC", color: "bg-blue-500", text: "text-blue-700", bg: "bg-blue-50" },
};

export const ProbabilityBarChart = ({ probabilities = {}, className }) => {
  const normalized = Object.entries(probabilities).map(([key, val]) => {
    const isObj = typeof val === "object" && val !== null;
    const name = isObj ? (val.name || key) : key;
    const prob = isObj ? Number(val.probability ?? 0) : Number(val ?? 0);
    return { key, name, prob };
  });
  const sorted = normalized.sort((a, b) => b.prob - a.prob);

  return (
    <div className={cn("w-full bg-white rounded-3xl p-6 border border-emerald-500/15 shadow-sm space-y-4", className)}>
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
            7-Class Probability Distribution
          </h4>
          <p className="text-[11px] text-slate-500">Calibrated Likelihood</p>
        </div>
      </div>

      <div className="space-y-3 pt-1">
        {sorted.map(({ name, prob }) => {
          const cfg = CLASS_CONFIG[name] || {
            color: "bg-emerald-500",
            text: "text-emerald-700",
            bg: "bg-emerald-50",
            short: name.slice(0, 3).toUpperCase(),
          };
          const percent = (prob * 100).toFixed(1);

          return (
            <div key={name} className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 font-medium text-slate-700">
                  <span className={cn("text-[10px] font-mono px-1.5 py-0.5 rounded font-bold", cfg.bg, cfg.text)}>
                    {cfg.short}
                  </span>
                  <span className="truncate max-w-[200px] sm:max-w-none">{name}</span>
                </div>
                <span className="font-mono font-bold text-slate-900 text-[11px]">{percent}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all duration-700 ease-out", cfg.color)}
                  style={{ width: `${Math.max(2, prob * 100)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
