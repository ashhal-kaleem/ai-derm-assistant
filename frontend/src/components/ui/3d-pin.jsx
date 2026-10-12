import React, { useState } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export const PinContainer = ({
  children,
  title,
  href,
  className,
  containerClassName,
}) => {
  const [transform, setTransform] = useState("translate(-50%,-50%) rotateX(0deg)");

  const onMouseEnter = () => {
    setTransform("translate(-50%,-50%) rotateX(40deg) scale(0.85)");
  };
  const onMouseLeave = () => {
    setTransform("translate(-50%,-50%) rotateX(0deg) scale(1)");
  };

  return (
    <div
      className={cn("relative group/pin z-30 cursor-pointer block", containerClassName)}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div
        style={{
          perspective: "1000px",
          transform: "rotateX(70deg) translateZ(0deg)",
        }}
        className="absolute left-1/2 top-1/2 ml-[0.09375rem] mt-4 -translate-x-1/2 -translate-y-1/2"
      >
        <div
          style={{ transform }}
          className="absolute left-1/2 p-5 top-1/2 flex justify-start items-start rounded-3xl shadow-xl bg-white border border-emerald-500/20 group-hover/pin:border-emerald-500/40 transition duration-500 overflow-hidden"
        >
          <div className={cn("relative z-50", className)}>{children}</div>
        </div>
      </div>
      <PinPerspective title={title} href={href} />
    </div>
  );
};

export const PinPerspective = ({ title, href }) => {
  return (
    <motion.div className="pointer-events-none w-80 h-64 flex items-center justify-center opacity-0 group-hover/pin:opacity-100 z-[60] transition duration-500">
      <div className="w-full h-full -mt-7 flex-none inset-0">
        <div className="absolute top-0 inset-x-0 flex justify-center">
          <a
            href={href || "#"}
            target="_blank"
            rel="noreferrer"
            className="pointer-events-auto relative flex space-x-2 items-center z-10 rounded-full bg-emerald-950 py-1 px-4 ring-1 ring-emerald-500/30 shadow-lg"
          >
            <span className="relative z-20 text-white text-xs font-bold font-mono inline-block">
              {title}
            </span>
          </a>
        </div>

        <div
          style={{
            perspective: "1000px",
            transform: "rotateX(70deg) translateZ(0)",
          }}
          className="absolute left-1/2 top-1/2 ml-[0.09375rem] mt-4 -translate-x-1/2 -translate-y-1/2"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0, x: "-50%", y: "-50%" }}
            animate={{ opacity: [0, 1, 0.5, 0], scale: 1 }}
            transition={{ duration: 4, repeat: Infinity, delay: 0 }}
            className="absolute left-1/2 top-1/2 h-[9rem] w-[9rem] rounded-full bg-emerald-500/[0.12] shadow-[0_8px_16px_rgb(5_150_105/0.2)]"
          />
        </div>

        <motion.div className="absolute right-1/2 bottom-1/2 bg-gradient-to-b from-transparent to-emerald-500 translate-y-[14px] w-px h-16 group-hover/pin:h-28 blur-[1px]" />
        <motion.div className="absolute right-1/2 bottom-1/2 bg-gradient-to-b from-transparent to-emerald-500 translate-y-[14px] w-px h-16 group-hover/pin:h-28" />
        <motion.div className="absolute right-1/2 translate-x-[1.5px] bottom-1/2 bg-emerald-600 translate-y-[14px] w-[4px] h-[4px] rounded-full z-40" />
      </div>
    </motion.div>
  );
};
