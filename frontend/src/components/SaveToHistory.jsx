import React, { useState } from "react";
import { Bookmark, Loader2, CheckCircle2, History } from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { API_BASE_URL } from "@/config";
import { makeThumb, trackVisit } from "@/lib/historyStore";

export default function SaveToHistory({ prediction, originalImage, addToast, onViewHistory }) {
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  if (!prediction) return null;

  const handleSave = async () => {
    const lesionName = name.trim();
    if (!lesionName) {
      addToast?.({
        type: "error",
        title: "Name needed",
        message: "Give this spot a name, e.g. “Left forearm mole”, so you can track it later.",
      });
      return;
    }

    setSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/history`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lesion_name: lesionName,
          notes: notes.trim() || null,
          prediction: {
            predicted_class: prediction.predicted_class || prediction.top_class || "",
            class_name: prediction.class_name || prediction.top_name || "",
            confidence: prediction.confidence ?? prediction.calibrated_confidence ?? 0,
            risk_level: prediction.risk_level || "green",
            risk_label: prediction.risk_label || "Benign",
            llm_explanation: prediction.llm_explanation || null,
          },
        }),
      });
      if (!res.ok) throw new Error("Save failed");
      const data = await res.json(); // { visit_id, lesion_id }

      const thumb = await makeThumb(originalImage);
      trackVisit({
        lesion_id: data.lesion_id,
        lesion_name: lesionName,
        visit_id: data.visit_id,
        thumb,
      });

      setSaved(true);
      addToast?.({
        type: "success",
        title: "Saved to history",
        message: `“${lesionName}” was added. Scan it again later to see how it changes.`,
      });
    } catch {
      addToast?.({
        type: "error",
        title: "Could not save",
        message: "The server did not respond. Please try again in a moment.",
      });
    } finally {
      setSaving(false);
    }
  };

  if (saved) {
    return (
      <SpotlightCard className="p-5">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-emerald-800 text-sm font-semibold">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            Saved as “{name.trim()}”
          </div>
          <button
            onClick={onViewHistory}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors"
          >
            <History className="w-4 h-4" /> View history
          </button>
        </div>
      </SpotlightCard>
    );
  }

  return (
    <SpotlightCard className="p-5">
      <div className="flex items-center gap-2 mb-1">
        <Bookmark className="w-4 h-4 text-emerald-700" />
        <h3 className="font-heading font-bold text-sm text-slate-900">Track this spot over time</h3>
      </div>
      <p className="text-xs text-slate-500 mb-4">
        Save this result under a name. When you scan the same spot again with the same name, the
        results are compared in your History.
      </p>

      <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="lesion-name">
        Spot name
      </label>
      <input
        id="lesion-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={60}
        placeholder="e.g. Left forearm mole"
        className="w-full mb-3 rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />

      <label className="block text-xs font-medium text-slate-700 mb-1" htmlFor="lesion-notes">
        Notes (optional)
      </label>
      <textarea
        id="lesion-notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        maxLength={300}
        rows={2}
        placeholder="e.g. Looks slightly bigger than last month"
        className="w-full mb-4 rounded-xl border border-emerald-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
      />

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-md transition-colors disabled:opacity-50"
      >
        {saving ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Saving…
          </>
        ) : (
          <>
            <Bookmark className="w-4 h-4" /> Save to my history
          </>
        )}
      </button>
    </SpotlightCard>
  );
}
