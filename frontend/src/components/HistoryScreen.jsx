import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  History,
  RefreshCw,
  ChevronDown,
  Trash2,
  Scan,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus,
  Search,
  CalendarClock,
  Layers,
  ShieldAlert,
} from "lucide-react";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { AnimatedBadge } from "@/components/ui/animated-badge";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Compare } from "@/components/ui/compare";
import { CountUp } from "@/components/ui/count-up";
import { API_BASE_URL } from "@/config";
import { loadTracked, removeTracked } from "@/lib/historyStore";

/* ---------- helpers ---------- */

const RISK_RANK = { green: 0, yellow: 1, red: 2 };
const rank = (level) => RISK_RANK[String(level || "green").toLowerCase()] ?? 0;
const levelOf = (v) => String(v?.risk_level || "green").toLowerCase();

const ACCENT = { green: "bg-emerald-500", yellow: "bg-amber-500", red: "bg-red-500" };
const DOT = { green: "#10B981", yellow: "#F59E0B", red: "#DC2626" };

const fmtDate = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ""
    : d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};

const daysSince = (iso) => {
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? null : Math.max(0, Math.floor((Date.now() - t) / 86400000));
};

const ago = (iso) => {
  const d = daysSince(iso);
  if (d === null) return "";
  if (d === 0) return "today";
  if (d === 1) return "yesterday";
  if (d < 14) return `${d} days ago`;
  if (d < 60) return `${Math.floor(d / 7)} weeks ago`;
  return `${Math.floor(d / 30)} months ago`;
};

// Compares the two most recent visits.
function getTrend(visits) {
  if (visits.length < 2)
    return { label: "First scan", Icon: Minus, tone: "bg-slate-50 text-slate-600 border-slate-200" };
  const diff = rank(visits[0].risk_level) - rank(visits[1].risk_level);
  if (diff > 0)
    return { label: "Risk went up", Icon: TrendingUp, tone: "bg-red-50 text-red-700 border-red-200" };
  if (diff < 0)
    return { label: "Risk went down", Icon: TrendingDown, tone: "bg-emerald-50 text-emerald-700 border-emerald-200" };
  return { label: "No change", Icon: Minus, tone: "bg-slate-50 text-slate-600 border-slate-200" };
}

async function fetchTimeline(lesion) {
  const res = await fetch(`${API_BASE_URL}/history/${encodeURIComponent(lesion.lesion_id)}`);
  if (!res.ok) throw new Error("not ok");
  const data = await res.json();
  const visits = [...(data.visits || [])].sort((a, b) => new Date(b.date) - new Date(a.date));
  return { ...lesion, lesion_name: data.lesion_name || lesion.lesion_name, visits, failed: false };
}

/* ---------- small pieces ---------- */

function RiskChart({ visits }) {
  // visits arrive newest-first; the chart reads left (oldest) to right (newest)
  const pts = [...visits].reverse();
  const W = 300, H = 84, padL = 34, padR = 12;
  const x = (i) => (pts.length === 1 ? (W + padL) / 2 : padL + (i * (W - padL - padR)) / (pts.length - 1));
  const y = (r) => 66 - r * 27;
  const line = pts.map((v, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(rank(v.risk_level))}`).join(" ");

  return (
    <div>
      <p className="text-xs font-semibold text-slate-800 mb-1">Risk level over time</p>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
        aria-label={`Risk level across ${pts.length} scans`}>
        {[["High", 2], ["Mid", 1], ["Low", 0]].map(([label, r]) => (
          <g key={label}>
            <line x1={padL} x2={W - padR} y1={y(r)} y2={y(r)} stroke="#D1FAE5" strokeWidth="1" strokeDasharray="3 3" />
            <text x={0} y={y(r) + 3} fontSize="9" fill="#64748B">{label}</text>
          </g>
        ))}
        <path d={line} fill="none" stroke="#059669" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {pts.map((v, i) => (
          <g key={v.visit_id}>
            <circle cx={x(i)} cy={y(rank(v.risk_level))} r="5" fill={DOT[levelOf(v)] || "#94A3B8"} stroke="#fff" strokeWidth="2" />
            <text x={x(i)} y={H - 2} fontSize="8" fill="#64748B" textAnchor="middle">
              {new Date(v.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, tone }) {
  return (
    <SpotlightCard className="p-4">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${tone}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-heading font-extrabold text-slate-900 leading-none">
            <CountUp value={value} decimals={0} suffix="" duration={700} />
          </p>
          <p className="text-[11px] text-slate-500 mt-1">{label}</p>
        </div>
      </div>
    </SpotlightCard>
  );
}

function SkeletonCard() {
  return (
    <div className="rounded-3xl border border-emerald-500/15 bg-white p-4 animate-pulse">
      <div className="flex gap-3">
        <div className="w-14 h-14 rounded-xl bg-emerald-100" />
        <div className="flex-1 space-y-2 pt-1">
          <div className="h-4 w-1/3 rounded bg-slate-200" />
          <div className="h-3 w-1/2 rounded bg-slate-100" />
          <div className="h-6 w-2/5 rounded-full bg-slate-100" />
        </div>
      </div>
    </div>
  );
}

/* ---------- screen ---------- */

export default function HistoryScreen({ onStartScan, addToast }) {
  const [lesions, setLesions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState(null);
  const [confirmId, setConfirmId] = useState(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("recent");

  const load = useCallback(async () => {
    setLoading(true);
    const tracked = loadTracked();
    if (tracked.length === 0) {
      setLesions([]);
      setLoading(false);
      return;
    }
    const results = await Promise.allSettled(tracked.map(fetchTimeline));
    setLesions(
      results.map((r, i) =>
        r.status === "fulfilled" ? r.value : { ...tracked[i], visits: [], failed: true }
      )
    );
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRemove = (lesion) => {
    removeTracked(lesion.lesion_id);
    setLesions((prev) => prev.filter((l) => l.lesion_id !== lesion.lesion_id));
    setConfirmId(null);
    addToast?.({ type: "success", title: "Removed", message: `“${lesion.lesion_name}” was removed from this device.` });
  };

  const stats = useMemo(() => {
    const ok = lesions.filter((l) => !l.failed && l.visits.length);
    return {
      spots: lesions.length,
      scans: ok.reduce((n, l) => n + l.visits.length, 0),
      attention: ok.filter((l) => rank(l.visits[0].risk_level) >= 1).length,
    };
  }, [lesions]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    const latestRank = (l) => (l.visits[0] ? rank(l.visits[0].risk_level) : 0);
    const latestTime = (l) => (l.visits[0] ? new Date(l.visits[0].date).getTime() : 0);
    return lesions
      .filter((l) => (q ? l.lesion_name.toLowerCase().includes(q) : true))
      .filter((l) =>
        filter === "attention" ? latestRank(l) >= 1 : filter === "low" ? latestRank(l) === 0 : true
      )
      .sort((a, b) => {
        if (sort === "name") return a.lesion_name.localeCompare(b.lesion_name);
        if (sort === "risk") return latestRank(b) - latestRank(a) || latestTime(b) - latestTime(a);
        return latestTime(b) - latestTime(a);
      });
  }, [lesions, query, filter, sort]);

  const FILTERS = [
    { id: "all", label: "All" },
    { id: "attention", label: "Needs attention" },
    { id: "low", label: "Low risk" },
  ];

  return (
    <div className="pt-28 pb-16 px-4 max-w-3xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="font-heading font-extrabold text-2xl sm:text-3xl text-slate-900 flex items-center gap-2">
            <History className="w-6 h-6 text-emerald-600" /> My History
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Track how each spot changes over time. Scan it again and save it under the same name.
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-emerald-300 text-emerald-900 text-xs font-semibold hover:bg-emerald-50 transition-colors disabled:opacity-50 shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {/* Stats */}
      {!loading && lesions.length > 0 && (
        <div className="grid grid-cols-3 gap-3">
          <StatCard icon={Layers} label="Tracked spots" value={stats.spots} tone="bg-emerald-100 text-emerald-700" />
          <StatCard icon={Scan} label="Total scans" value={stats.scans} tone="bg-sky-100 text-sky-700" />
          <StatCard
            icon={ShieldAlert}
            label="Need attention"
            value={stats.attention}
            tone={stats.attention ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500"}
          />
        </div>
      )}

      {/* Toolbar */}
      {!loading && lesions.length > 0 && (
        <div className="space-y-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search your spots…"
              aria-label="Search your spots"
              className="w-full rounded-full border border-emerald-200 bg-white pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              {FILTERS.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setFilter(f.id)}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    filter === f.id
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : "bg-white text-slate-600 border-emerald-200 hover:bg-emerald-50"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              aria-label="Sort spots"
              className="rounded-full border border-emerald-200 bg-white px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="recent">Most recent</option>
              <option value="risk">Highest risk first</option>
              <option value="name">Name (A–Z)</option>
            </select>
          </div>
        </div>
      )}

      {/* Loading skeletons */}
      {loading && (
        <div className="space-y-3" aria-busy="true">
          <SkeletonCard />
          <SkeletonCard />
          <p className="text-xs text-slate-400 text-center">The server can take a few seconds to wake up.</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && lesions.length === 0 && (
        <SpotlightCard className="p-10 text-center">
          <div className="w-14 h-14 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mx-auto mb-4">
            <History className="w-7 h-7" />
          </div>
          <h2 className="font-heading font-bold text-lg text-slate-900 mb-1">No saved spots yet</h2>
          <p className="text-sm text-slate-500 mb-5 max-w-sm mx-auto">
            After a scan, choose “Save to my history” and give the spot a name. It will show up here
            with a timeline.
          </p>
          <button
            onClick={onStartScan}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors"
          >
            <Scan className="w-4 h-4" /> Start a scan
          </button>
        </SpotlightCard>
      )}

      {/* No match */}
      {!loading && lesions.length > 0 && shown.length === 0 && (
        <SpotlightCard className="p-8 text-center">
          <p className="text-sm text-slate-500">No spots match your search or filter.</p>
          <button
            onClick={() => { setQuery(""); setFilter("all"); }}
            className="mt-3 text-xs font-semibold text-emerald-700 hover:underline"
          >
            Clear filters
          </button>
        </SpotlightCard>
      )}

      {/* Spot cards */}
      {!loading &&
        shown.map((lesion, idx) => {
          const latest = lesion.visits[0];
          const oldest = lesion.visits[lesion.visits.length - 1];
          const trend = getTrend(lesion.visits);
          const TrendIcon = trend.Icon;
          const isOpen = openId === lesion.lesion_id;
          const thumb = latest ? lesion.thumbs?.[latest.visit_id] : Object.values(lesion.thumbs || {})[0];
          const beforeImg = oldest && lesion.thumbs?.[oldest.visit_id];
          const afterImg = latest && lesion.thumbs?.[latest.visit_id];
          const canCompare = lesion.visits.length >= 2 && beforeImg && afterImg;
          const due = latest && (daysSince(latest.date) ?? 0) >= 28;

          return (
            <motion.div
              key={lesion.lesion_id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: Math.min(idx, 6) * 0.05 }}
            >
              <SpotlightCard className="p-0">
                {latest && <span className={`absolute left-0 top-0 bottom-0 w-1.5 ${ACCENT[levelOf(latest)] || "bg-slate-300"}`} />}
                <div className="flex items-center gap-3 p-4 pl-5">
                  <button
                    onClick={() => setOpenId(isOpen ? null : lesion.lesion_id)}
                    className="flex flex-1 items-center gap-3 text-left min-w-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 rounded-xl"
                    aria-expanded={isOpen}
                  >
                    {thumb ? (
                      <img src={thumb} alt="" className="w-14 h-14 rounded-xl object-cover border border-emerald-200 shrink-0" />
                    ) : (
                      <div className="w-14 h-14 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center shrink-0">
                        <Scan className="w-5 h-5 text-emerald-400" />
                      </div>
                    )}
                    <div className="min-w-0">
                      <p className="font-heading font-bold text-slate-900 truncate">{lesion.lesion_name}</p>
                      {lesion.failed ? (
                        <p className="text-xs text-red-600">Could not load. Press Refresh to retry.</p>
                      ) : (
                        <p className="text-xs text-slate-500">
                          {lesion.visits.length} {lesion.visits.length === 1 ? "scan" : "scans"} · last scan {ago(latest?.date)}
                        </p>
                      )}
                      {!lesion.failed && latest && (
                        <div className="flex flex-wrap items-center gap-2 mt-2">
                          <AnimatedBadge level={latest.risk_level} label={latest.risk_label} />
                          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-medium ${trend.tone}`}>
                            <TrendIcon className="w-3 h-3" /> {trend.label}
                          </span>
                          {due && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-medium bg-amber-50 text-amber-800 border-amber-200">
                              <CalendarClock className="w-3 h-3" /> Time to re-scan
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <ChevronDown className={`w-5 h-5 text-slate-400 ml-auto shrink-0 transition-transform ${isOpen ? "rotate-180" : ""}`} />
                  </button>
                </div>

                <AnimatePresence initial={false}>
                  {isOpen && !lesion.failed && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.22 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 pt-4 border-t border-emerald-500/10 space-y-5">
                        {canCompare && (
                          <div>
                            <div className="flex justify-between text-[11px] font-mono text-slate-500 mb-2">
                              <span>First scan · {fmtDate(oldest.date)}</span>
                              <span>Latest · {fmtDate(latest.date)}</span>
                            </div>
                            <Compare firstImage={beforeImg} secondImage={afterImg} className="w-full" />
                            <p className="text-[11px] text-slate-400 mt-1">Drag the handle to compare.</p>
                          </div>
                        )}

                        {lesion.visits.length >= 2 && <RiskChart visits={lesion.visits} />}

                        <div>
                          <p className="text-xs font-semibold text-slate-800 mb-3">Scan timeline</p>
                          <ol>
                            {lesion.visits.map((v, i) => (
                              <li key={v.visit_id} className="relative pl-6 pb-5 last:pb-0">
                                {i < lesion.visits.length - 1 && (
                                  <span className="absolute left-[5px] top-4 bottom-0 w-px bg-emerald-200" />
                                )}
                                <span
                                  className="absolute left-0 top-1.5 w-[11px] h-[11px] rounded-full"
                                  style={{ background: DOT[levelOf(v)] || "#94A3B8" }}
                                />
                                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                                  <span className="text-xs font-semibold text-slate-900">{fmtDate(v.date)}</span>
                                  <span className="text-xs text-slate-600">{v.class_name}</span>
                                  <span className="text-xs font-mono text-slate-500">
                                    {Math.round((Number(v.confidence) || 0) * 100)}% confidence
                                  </span>
                                </div>
                                {v.notes && <p className="text-xs text-slate-600 mt-1 italic">“{v.notes}”</p>}
                                {v.llm_explanation && (
                                  <p className="text-xs text-slate-500 mt-1 line-clamp-3">{v.llm_explanation}</p>
                                )}
                              </li>
                            ))}
                          </ol>
                        </div>

                        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                          <button
                            onClick={onStartScan}
                            className="flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors"
                          >
                            <Scan className="w-4 h-4" /> Scan again
                          </button>

                          {confirmId === lesion.lesion_id ? (
                            <div className="flex items-center gap-2 text-xs">
                              <span className="text-slate-600">Remove from this device?</span>
                              <button
                                onClick={() => handleRemove(lesion)}
                                className="px-3 py-1.5 rounded-full bg-red-600 hover:bg-red-700 text-white font-semibold"
                              >
                                Yes, remove
                              </button>
                              <button
                                onClick={() => setConfirmId(null)}
                                className="px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50"
                              >
                                Cancel
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setConfirmId(lesion.lesion_id)}
                              className="flex items-center gap-1.5 px-3 py-2 rounded-full text-xs text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                            >
                              <Trash2 className="w-4 h-4" /> Remove
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </SpotlightCard>
            </motion.div>
          );
        })}

      <Alert variant="warning">
        <AlertTriangle className="w-4 h-4" />
        <AlertTitle>Please note</AlertTitle>
        <AlertDescription>
          If a spot grows, changes colour or shape, bleeds or itches, see a doctor, even when the
          latest result says low risk. This history is a diary, not a diagnosis.
        </AlertDescription>
      </Alert>
    </div>
  );
}
