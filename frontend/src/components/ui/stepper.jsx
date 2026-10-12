import React from "react";
import { motion } from "motion/react";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export const Stepper = ({ steps = [], currentStep = 1, className }) => {
  return (
    <div className={cn("w-full max-w-2xl mx-auto py-4", className)}>
      <div className="flex items-center justify-between relative">
        {/* Connecting Line Track */}
        <div className="absolute top-1/2 left-0 right-0 -translate-y-1/2 h-0.5 bg-slate-200 z-0" />
        {/* Connecting Active Progress Line */}
        <motion.div
          className="absolute top-1/2 left-0 -translate-y-1/2 h-0.5 bg-emerald-600 z-0"
          initial={{ width: "0%" }}
          animate={{
            width: `${((Math.max(1, currentStep) - 1) / Math.max(1, steps.length - 1)) * 100}%`,
          }}
          transition={{ duration: 0.4, ease: "easeInOut" }}
        />

        {steps.map((step, idx) => {
          const stepNum = idx + 1;
          const isDone = currentStep > stepNum;
          const isCurrent = currentStep === stepNum;

          return (
            <div key={step.id || idx} className="flex flex-col items-center relative z-10">
              <motion.div
                animate={{
                  scale: isCurrent ? 1.1 : 1,
                  backgroundColor: isDone || isCurrent ? "#059669" : "#FFFFFF",
                  borderColor: isDone || isCurrent ? "#059669" : "#CBD5E1",
                  color: isDone || isCurrent ? "#FFFFFF" : "#64748B",
                }}
                className={cn(
                  "w-8 h-8 rounded-full border-2 flex items-center justify-center font-mono text-xs font-bold shadow-sm transition-colors duration-200"
                )}
              >
                {isDone ? <Check className="w-4 h-4 stroke-[3]" /> : stepNum}
              </motion.div>
              <span
                className={cn(
                  "mt-2 text-[11px] font-medium tracking-tight text-center max-w-[80px]",
                  isCurrent ? "text-emerald-900 font-bold" : isDone ? "text-slate-700" : "text-slate-400"
                )}
              >
                {step.title}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
