import React, { useEffect, useRef, useState } from "react";
import { useScroll, useTransform, motion } from "motion/react";
import { cn } from "@/lib/utils";

export const Timeline = ({ data = [], title = "Longitudinal Lesion Timeline", subtitle = "Tracking changes and morphological evolution over time", className }) => {
  const ref = useRef(null);
  const containerRef = useRef(null);
  const [height, setHeight] = useState(0);

  useEffect(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      setHeight(rect.height);
    }
  }, [data]);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 10%", "end 50%"],
  });

  const heightTransform = useTransform(scrollYProgress, [0, 1], [0, height]);
  const opacityTransform = useTransform(scrollYProgress, [0, 0.1], [0, 1]);

  return (
    <div className={cn("w-full bg-white rounded-3xl p-6 sm:p-10 border border-emerald-500/15 shadow-sm font-sans", className)} ref={containerRef}>
      <div className="max-w-4xl mx-auto mb-8 border-b border-slate-100 pb-5">
        <h3 className="text-xl sm:text-2xl font-bold font-heading text-[#064E3B]">{title}</h3>
        <p className="text-xs sm:text-sm text-slate-500 mt-1 font-sans">{subtitle}</p>
      </div>

      <div ref={ref} className="relative max-w-4xl mx-auto pb-10">
        {data.map((item, index) => (
          <div key={index} className="flex justify-start pt-6 md:pt-10 gap-6 md:gap-10">
            <div className="sticky flex flex-col md:flex-row z-40 items-center top-32 self-start max-w-xs md:w-48">
              <div className="h-8 w-8 absolute left-0 md:left-0 rounded-full bg-white flex items-center justify-center border-2 border-emerald-500 shadow-md">
                <div className="h-2.5 w-2.5 rounded-full bg-emerald-600 animate-pulse" />
              </div>
              <h4 className="hidden md:block pl-12 text-sm font-bold font-mono text-slate-700">
                {item.title}
              </h4>
            </div>

            <div className="relative pl-10 md:pl-2 w-full">
              <h4 className="md:hidden block text-xs font-bold font-mono text-slate-700 mb-2">
                {item.title}
              </h4>
              <div>{item.content}</div>
            </div>
          </div>
        ))}

        {/* Scroll beam line */}
        <div
          style={{ height: height + "px" }}
          className="absolute left-4 top-0 overflow-hidden w-0.5 bg-slate-200"
        >
          <motion.div
            style={{
              height: heightTransform,
              opacity: opacityTransform,
            }}
            className="absolute inset-x-0 top-0 w-0.5 bg-gradient-to-b from-emerald-600 via-teal-400 to-emerald-200 rounded-full shadow-[0_0_8px_#059669]"
          />
        </div>
      </div>
    </div>
  );
};
