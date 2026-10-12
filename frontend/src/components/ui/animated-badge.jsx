import React from "react";
import { CheckCircle2, AlertTriangle, AlertOctagon } from "lucide-react";
import { cn } from "@/lib/utils";

export const AnimatedBadge = ({ level = "green", label, className }) => {
  const normalized = (level || "green").toLowerCase();

  const configs = {
    green: {
      bg: "bg-emerald-500/10 text-emerald-800 border-emerald-500/30",
      dot: "bg-emerald-500",
      icon: CheckCircle2,
      defaultLabel: "Benign / Low Risk",
    },
    yellow: {
      bg: "bg-amber-500/10 text-amber-900 border-amber-500/30",
      dot: "bg-amber-500",
      icon: AlertTriangle,
      defaultLabel: "Monitor / Moderate Risk",
    },
    red: {
      bg: "bg-red-500/10 text-red-900 border-red-500/30",
      dot: "bg-red-500",
      icon: AlertOctagon,
      defaultLabel: "Urgent Review Required",
    },
  };

  const current = configs[normalized] || configs.green;
  const Icon = current.icon;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-semibold shadow-xs select-none",
        current.bg,
        className
      )}
    >
      <span className={cn("w-2 h-2 rounded-full", current.dot, "animate-pulse")} />
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span>{label || current.defaultLabel}</span>
    </span>
  );
};
