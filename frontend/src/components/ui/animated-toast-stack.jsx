import React from "react";
import { motion, AnimatePresence } from "motion/react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export const ToastStack = ({ toasts = [], removeToast }) => {
  return (
    <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => {
          const isError = toast.type === "error";
          const isSuccess = toast.type === "success";

          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={cn(
                "pointer-events-auto flex items-start gap-3 rounded-2xl p-4 shadow-xl border backdrop-blur-md",
                isError
                  ? "bg-red-50/95 border-red-200 text-red-900"
                  : isSuccess
                  ? "bg-emerald-50/95 border-emerald-200 text-emerald-900"
                  : "bg-white/95 border-slate-200 text-slate-800"
              )}
            >
              {isError ? (
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
              ) : isSuccess ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              ) : (
                <Info className="w-5 h-5 text-slate-600 shrink-0 mt-0.5" />
              )}
              <div className="flex-1 text-xs">
                {toast.title && <h5 className="font-heading font-bold mb-0.5">{toast.title}</h5>}
                <p className="opacity-90 leading-relaxed font-sans">{toast.message}</p>
              </div>
              <button
                onClick={() => removeToast && removeToast(toast.id)}
                className="text-slate-400 hover:text-slate-700 p-0.5 rounded-lg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
};
