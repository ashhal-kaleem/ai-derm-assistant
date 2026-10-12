import React, { useState } from "react";
import { motion, AnimatePresence, useScroll, useMotionValueEvent } from "motion/react";
import { cn } from "@/lib/utils";
import { Activity } from "lucide-react";

export const FloatingNav = ({ navItems, className, currentScreen, setScreen, serverOnline }) => {
  const { scrollYProgress } = useScroll();
  const [visible, setVisible] = useState(true);

  useMotionValueEvent(scrollYProgress, "change", (current) => {
    if (typeof current === "number") {
      const prev = scrollYProgress.getPrevious() ?? 0;
      const direction = current - prev;
      if (scrollYProgress.get() < 0.05) {
        setVisible(true);
      } else {
        if (direction < 0) {
          setVisible(true);
        } else {
          setVisible(false);
        }
      }
    }
  });

  return (
    <AnimatePresence mode="wait">
      <motion.div
        initial={{ opacity: 1, y: -100 }}
        animate={{ y: visible ? 0 : -100, opacity: visible ? 1 : 0 }}
        transition={{ duration: 0.2 }}
        className={cn(
          "flex max-w-fit fixed top-5 inset-x-0 mx-auto z-[5000] items-center justify-center",
          className
        )}
      >
        <div className="flex items-center justify-center gap-2 rounded-full border border-emerald-500/20 bg-white/90 px-3 py-1.5 shadow-xl shadow-emerald-950/10 backdrop-blur-md">
          {/* Brand Logo */}
          <button
            onClick={() => setScreen && setScreen("scan")}
            className="flex items-center gap-2 pl-2 pr-1 py-1 focus:outline-none"
          >
            <div className="w-7 h-7 rounded-full bg-emerald-600 text-white flex items-center justify-center shadow-sm">
              <Activity className="w-4 h-4" />
            </div>
            <span className="font-heading font-bold text-sm tracking-tight text-slate-900 hidden sm:inline">
              DermAssist<span className="text-emerald-600">.ai</span>
            </span>
          </button>

          {/* Divider */}
          <div className="h-4 w-px bg-slate-200" />

          {/* Nav items container */}
          <div className="flex items-center gap-1">
            {navItems.map((navItem, idx) => {
              const active = currentScreen === navItem.id;
              return (
                <button
                  key={`link-${idx}`}
                  onClick={() => setScreen && setScreen(navItem.id)}
                  className={cn(
                    "relative flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                    active
                      ? "bg-emerald-600 text-white font-semibold shadow-xs"
                      : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                  )}> 
                  <span className="text-xs">{navItem.icon}</span>
                  <span className="hidden sm:inline">{navItem.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
