import React, { useState, useEffect } from "react";
import {
  Calendar,
  History,
  TrendingUp,
  TrendingDown,
  Minus,
  Sparkles,
  ArrowRight,
  Loader2,
  Clock,
  Layers,
  Image as ImageIcon
} from "lucide-react";
import { Timeline } from "@/components/ui/timeline";
import { AnimatedBadge } from "@/components/ui/animated-badge";
import { API_BASE_URL } from "@/config";

export const HistoryScreen = ({ onStartNewScan, onSelectScan }) => {
  const [historyList, setHistoryList] = useState([]);
  const [selectedLesionId, setSelectedLesionId] = useState(null);
  const [timelineEntries, setTimelineEntries] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterQuery, setFilterQuery] = useState("");

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/history`);
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data) ? data : data.scans || [];
        setHistoryList(items);
        if (items.length > 0 && !selectedLesionId) {
          // Default select the first lesion
          handleSelectLesion(items[0].lesion_id || items[0].id, items);
        }
      }
    } catch (err) {
      console.warn("Could not fetch remote history, using fallback cache", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectLesion = async (lesionId, allItems = historyList) => {
    setSelectedLesionId(lesionId);
    try {
      const res = await fetch(`${API_BASE_URL}/history/${lesionId}`);
      if (res.ok) {
        const data = await res.json();
        const records = Array.isArray(data) ? data : data.records || [];
        buildTimeline(records);
        return;
      }
    } catch {
      // Fallback: filter locally from historyList
    }

    const matching = allItems.filter(
      (item) => (item.lesion_id || item.id) === lesionId
    );
    buildTimeline(matching);
  };

  const buildTimeline = (records) => {
    if (!records || !records.length) {
      setTimelineEntries([]);
      return;
    }

    // Sort chronologically
    const sorted = [...records].sort(
      (a, b) => new Date(a.created_at || Date.now()) - new Date(b.created_at || Date.now())
    );

    const entries = sorted.map((scan, idx) => {
      const dateStr = scan.created_at
        ? new Date(scan.created_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        : `Visit ${idx + 1}`;

      // Check risk trend against previous visit
      let TrendIcon = Minus;
      let trendText = "Baseline";
      let trendColor = "text-slate-500";

      if (idx > 0) {
        const prev = sorted[idx - 1];
        const riskRank = { green: 1, yellow: 2, red: 3 };
        const currRank = riskRank[scan.risk_level] || 1;
        const prevRank = riskRank[prev.risk_level] || 1;

        if (currRank > prevRank) {
          TrendIcon = TrendingUp;
          trendText = "Risk Escalated";
          trendColor = "text-red-600 font-bold";
        } else if (currRank < prevRank) {
          TrendIcon = TrendingDown;
          trendText = "Risk Decreased";
          trendColor = "text-emerald-600 font-bold";
        } else {
          trendText = "Morphology Stable";
          trendColor = "text-slate-600";
        }
      }

      return {
        title: dateStr,
        content: (
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="font-heading font-bold text-base text-slate-900">
                  {scan.class_name || scan.diagnosis || "Skin Lesion"}
                </span>
                <AnimatedBadge level={scan.risk_level} label={scan.risk_label} />
              </div>

              <div className={`flex items-center gap-1 text-xs font-mono ${trendColor}`}>
                <TrendIcon className="w-3.5 h-3.5" />
                <span>{trendText}</span>
              </div>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed font-sans">
              {scan.notes || "Clinical capture logged with automated temperature-scaled inference."}
            </p>

            <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px] font-mono text-slate-400">
              <span>Confidence: {((scan.confidence || 0.9) * 100).toFixed(1)}%</span>
              <span>ID: {scan.lesion_id || "LESION-DEFAULT"}</span>
            </div>
          </div>
        ),
      };
    });

    setTimelineEntries(entries);
  };

  const filtered = historyList.filter((item) =>
    (item.class_name || "").toLowerCase().includes(filterQuery.toLowerCase()) ||
    (item.lesion_id || "").toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <div className="pt-24 pb-20 px-4 max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-emerald-700 bg-emerald-100/60 px-2.5 py-0.5 rounded-full">
            Longitudinal Memory
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#064E3B] font-heading mt-1">
            Lesion History & Evolution
          </h2>
        </div>

        <button
          onClick={onStartNewScan}
          className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-700 transition-colors shadow-sm"
        >
          <Sparkles className="w-3.5 h-3.5" /> New Skin Scan
        </button>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 text-slate-500">
          <Loader2 className="w-8 h-8 animate-spin text-emerald-600 mb-3" />
          <p className="text-xs font-mono">Fetching recorded scans from database...</p>
        </div>
      ) : historyList.length === 0 ? (
        /* Empty State */
        <div className="bg-white rounded-3xl p-12 text-center max-w-lg mx-auto border border-dashed border-emerald-300 shadow-sm">
          <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-4">
            <History className="w-8 h-8" />
          </div>
          <h3 className="font-heading font-bold text-lg text-slate-900 mb-1">
            Abhi koi scan nahi hai
          </h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mb-6">
            Pehle ek skin lesion image scan karein aur "Track This Lesion" par click karke timeline mein save karein.
          </p>
          <button
            onClick={onStartNewScan}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-emerald-600 text-white font-semibold text-xs shadow-md shadow-emerald-700/20 hover:bg-emerald-700 transition-all"
          >
            <Sparkles className="w-4 h-4" /> Start First Scan
          </button>
        </div>
      ) : (
        /* History Grid: Lesion list & Longitudinal Timeline */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Lesion Cards List (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-800">
                Tracked Scans ({historyList.length})
              </h4>
            </div>

            <div className="space-y-3">
              {filtered.map((item, idx) => {
                const isSelected = (item.lesion_id || item.id) === selectedLesionId;
                const lesionKey = item.lesion_id || item.id || `lesion_${idx}`;

                return (
                  <div
                    key={lesionKey}
                    onClick={() => handleSelectLesion(lesionKey)}
                    className={`cursor-pointer rounded-2xl p-4 transition-all border ${
                      isSelected
                        ? "bg-emerald-50/80 border-emerald-500 shadow-sm"
                        : "bg-white border-slate-200 hover:border-slate-300 shadow-xs"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <div>
                        <h5 className="font-heading font-bold text-sm text-slate-900">
                          {item.class_name || "Skin Lesion"}
                        </h5>
                        <span className="text-[10px] font-mono text-slate-400">
                          ID: {item.lesion_id || "UNTAGGED"}
                        </span>
                      </div>
                      <AnimatedBadge level={item.risk_level} label={item.risk_label} />
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100">
                      <span className="flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3 text-slate-400" />
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : "Recent"}
                      </span>
                      <span className="font-mono font-bold text-emerald-800">
                        {((item.confidence || 0.9) * 100).toFixed(0)}% Conf
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Longitudinal Timeline (#22 Aceternity Timeline) (7 cols) */}
          <div className="lg:col-span-7">
            {timelineEntries.length > 0 ? (
              <Timeline
                data={timelineEntries}
                title={`Timeline: ${selectedLesionId || "Selected Lesion"}`}
                subtitle="Longitudinal progression & risk trend across visits"
              />
            ) : (
              <div className="bg-white rounded-3xl p-8 text-center border border-slate-200 text-slate-500 text-xs font-mono">
                Select a lesion from the left to view its chronological progression.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default HistoryScreen;
