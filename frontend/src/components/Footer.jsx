import React from "react";
import { Activity } from "lucide-react";

export const Footer = () => {
  return (
    <footer className="w-full bg-white border-t border-slate-200 mt-auto text-slate-500 font-sans text-xs">
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center">
              <Activity className="w-3.5 h-3.5" />
            </div>
            <span className="font-heading font-bold text-slate-800 text-sm">
              DermAssist AI
            </span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-500">Skin Lesion Triage Assistant</span>
          </div>

          <p className="text-slate-400 text-center sm:text-right">
            &copy; {new Date().getFullYear()} DermAssist AI. All rights reserved.
          </p>
        </div>

        {/* Minimal Clinical Disclaimer */}
        <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 text-center leading-relaxed">
          <strong>Medical Notice:</strong> DermAssist AI is intended for educational and preliminary screening assistance only. It does not provide medical diagnosis. Any suspicious or changing skin lesion must be examined in person by a certified dermatologist.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
