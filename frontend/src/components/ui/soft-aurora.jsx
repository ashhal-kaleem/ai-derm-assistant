import React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export const SoftAurora = ({ className, children }) => {
  return (
    <div className={cn("relative overflow-hidden w-full", className)}>
      <motion.div
        animate={{
          scale: [1, 1.15, 1],
          rotate: [0, 8, 0],
          x: [0, 20, 0],
          y: [0, -15, 0],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="pointer-events-none absolute -top-40 -left-20 h-96 w-96 rounded-full bg-emerald-400/20 blur-[120px]"
      />
      <motion.div
        animate={{
          scale: [1, 1.25, 1],
          rotate: [0, -10, 0],
          x: [0, -25, 0],
          y: [0, 20, 0],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="pointer-events-none absolute top-10 right-0 h-96 w-96 rounded-full bg-teal-400/20 blur-[130px]"
      />
      <motion.div
        animate={{
          scale: [1, 1.2, 1],
          x: [0, 15, 0],
        }}
        transition={{
          duration: 18,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        className="pointer-events-none absolute bottom-0 left-1/3 h-80 w-80 rounded-full bg-emerald-600/10 blur-[140px]"
      />
      <div className="relative z-10">{children}</div>
    </div>
  );
};
