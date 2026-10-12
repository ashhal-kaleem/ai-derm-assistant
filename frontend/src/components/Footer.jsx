import React from "react";
import { ShieldCheck, HeartPulse, Sparkles, Lock, Database, Info } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="w-full bg-white border-t border-emerald-900/10 mt-auto text-slate-600 font-sans">
      <div className="max-w-6xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
          {/* Brand & Mission */}
          <div className="md:col-span-2 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-sm">
                <HeartPulse className="w-5 h-5" />
              </div>
              <span className="font-heading font-extrabold text-lg text-[#064E3B] tracking-tight">
                DermAssist AI
              </span>
              <span className="text-[10px] font-mono font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                v1.0.0
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed max-w-md">
              AI-assisted clinical dermatology triage engine built for high-risk lesion screening. Calibrated on 10,015 dermoscopic lesion samples across 7 diagnostic archetypes.
            </p>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                <Database className="w-3 h-3 text-emerald-600" />
                HAM10000 Validated
              </span>
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-slate-600 bg-slate-50 px-2.5 py-1 rounded-full border border-slate-200">
                <Lock className="w-3 h-3 text-slate-500" />
                Client-Side Sovereignty
              </span>
              <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-amber-700 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-200">
                <Sparkles className="w-3 h-3 text-amber-500" />
                Calibrated ECE Optimized
              </span>
            </div>
          </div>

          {/* Clinical Core Invariants */}
          <div className="space-y-2">
            <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
              Diagnostic Standards
            </h5>
            <ul className="text-xs text-slate-500 space-y-1.5">
              <li className="hover:text-emerald-700 transition-colors">
                • 7-Class Skin Pathology Schema
              </li>
              <li className="hover:text-emerald-700 transition-colors">
                • Temperature Scaling (T* Calibrated)
              </li>
              <li className="hover:text-emerald-700 transition-colors">
                • Grad-CAM Saliency Localization
              </li>
              <li className="hover:text-emerald-700 transition-colors">
                • Zero-Leakage Grouped Stratification
              </li>
            </ul>
          </div>

          {/* Privacy & Protocol */}
          <div className="space-y-2">
            <h5 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-900">
              Data & Ethics
            </h5>
            <ul className="text-xs text-slate-500 space-y-1.5">
              <li className="hover:text-emerald-700 transition-colors">
                • Zero Ephemeral Image Retention
              </li>
              <li className="hover:text-emerald-700 transition-colors">
                • Patient-Controlled Cloud Sync
              </li>
              <li className="hover:text-emerald-700 transition-colors">
                • HIPAA/GDPR Compatible Design
              </li>
              <li className="hover:text-emerald-700 transition-colors">
                • ISO/IEEE AI Safety Governance
              </li>
            </ul>
          </div>
        </div>

        {/* Permanent Medical Governance Notice */}
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-950 flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5 sm:mt-0" />
          <p className="leading-relaxed text-[11.5px]">
            <strong>Clinical Education Notice:</strong> DermAssist AI outputs are statistical inference estimates intended for preliminary triage guidance and educational clinical support. This software does not establish a doctor-patient relationship nor constitute a formal biopsy diagnosis. Always consult a board-certified dermatologist for suspicious melanomas or rapid-growth lesions.
          </p>
        </div>

        {/* Bottom Bar */}
        <div className="mt-8 pt-6 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>&copy; {new Date().getFullYear()} DermAssist AI. All rights reserved.</span>
          </div>
          <div className="font-mono text-[11px] text-slate-500">
            Render LPU Inference &bull; ONNX Engine Runtime &bull; Vercel Client
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
