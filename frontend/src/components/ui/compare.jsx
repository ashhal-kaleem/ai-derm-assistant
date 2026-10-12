import React, { useState, useEffect, useRef, useCallback } from "react";
import { AnimatePresence, motion } from "motion/react";
import { cn } from "@/lib/utils";
import { GripVertical } from "lucide-react";

export const Compare = ({
  firstImage = "",
  secondImage = "",
  className,
  firstImageClassName,
  secondImageClassname,
  initialSliderPercentage = 50,
  slideMode = "drag",
  showHandlebar = true,
  autoplay = false,
  autoplayDuration = 5000,
}) => {
  const [sliderXPercent, setSliderXPercent] = useState(initialSliderPercentage);
  const [isDragging, setIsDragging] = useState(false);
  const sliderRef = useRef(null);

  const startAutoplay = useCallback(() => {
    if (!autoplay) return;
    const startTime = Date.now();
    const animate = () => {
      const elapsedTime = Date.now() - startTime;
      const progress = (elapsedTime % (autoplayDuration * 2)) / autoplayDuration;
      const percentage = progress <= 1 ? progress * 100 : (2 - progress) * 100;
      setSliderXPercent(percentage);
    };
    const timer = setInterval(animate, 16);
    return () => clearInterval(timer);
  }, [autoplay, autoplayDuration]);

  useEffect(() => {
    const cleanup = startAutoplay();
    return () => cleanup && cleanup();
  }, [startAutoplay]);

  const handleStart = useCallback(() => {
    if (slideMode === "drag") setIsDragging(true);
  }, [slideMode]);

  const handleEnd = useCallback(() => {
    if (slideMode === "drag") setIsDragging(false);
  }, [slideMode]);

  const handleMove = useCallback(
    (clientX) => {
      if (!sliderRef.current) return;
      if (slideMode === "hover" || (slideMode === "drag" && isDragging)) {
        const rect = sliderRef.current.getBoundingClientRect();
        const x = clientX - rect.left;
        const percent = (x / rect.width) * 100;
        requestAnimationFrame(() => {
          setSliderXPercent(Math.max(0, Math.min(100, percent)));
        });
      }
    },
    [slideMode, isDragging]
  );

  return (
    <div
      ref={sliderRef}
      className={cn("w-full aspect-square max-h-[460px] overflow-hidden rounded-3xl relative select-none border border-emerald-500/20 bg-slate-950 shadow-xl", className)}
      style={{ cursor: slideMode === "drag" ? (isDragging ? "grabbing" : "grab") : "col-resize" }}
      onMouseMove={(e) => handleMove(e.clientX)}
      onMouseDown={handleStart}
      onMouseUp={handleEnd}
      onMouseLeave={handleEnd}
      onTouchStart={(e) => e.touches[0] && handleStart()}
      onTouchMove={(e) => e.touches[0] && handleMove(e.touches[0].clientX)}
      onTouchEnd={handleEnd}
    >
      {/* Divider and slider handle */}
      <AnimatePresence initial={false}>
        <motion.div
          className="h-full w-0.5 absolute top-0 z-30 bg-emerald-400 shadow-[0_0_12px_#10B981]"
          style={{ left: `${sliderXPercent}%`, top: "0" }}
          transition={{ duration: 0 }}
        >
          {showHandlebar && (
            <div className="h-9 w-9 rounded-full top-1/2 -translate-y-1/2 -translate-x-1/2 bg-white text-emerald-700 z-40 absolute flex items-center justify-center shadow-xl border-2 border-emerald-600 transition-transform hover:scale-110 active:scale-95">
              <GripVertical className="h-4 w-4" />
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      {/* First Image (Foreground, clipped) */}
      <div className="overflow-hidden w-full h-full relative z-20 pointer-events-none">
        <AnimatePresence initial={false}>
          {firstImage && (
            <motion.div
              className={cn("absolute inset-0 z-20 w-full h-full select-none overflow-hidden", firstImageClassName)}
              style={{ clipPath: `inset(0 ${100 - sliderXPercent}% 0 0)` }}
              transition={{ duration: 0 }}
            >
              <img
                alt="Original Skin Lesion"
                src={firstImage}
                className={cn("absolute inset-0 w-full h-full object-cover select-none", firstImageClassName)}
                draggable={false}
              />
              <span className="absolute top-4 left-4 z-30 bg-slate-900/80 backdrop-blur-md text-white font-mono text-[11px] px-3 py-1 rounded-full font-bold shadow-md">
                Original Capture
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Second Image (Background Grad-CAM Heatmap) */}
      <AnimatePresence initial={false}>
        {secondImage && (
          <motion.div className="absolute inset-0 z-10 w-full h-full select-none">
            <img
              className={cn("w-full h-full object-cover select-none", secondImageClassname)}
              alt="Grad-CAM Saliency Heatmap"
              src={secondImage}
              draggable={false}
            />
            <span className="absolute top-4 right-4 z-30 bg-red-600/85 backdrop-blur-md text-white font-mono text-[11px] px-3 py-1 rounded-full font-bold shadow-md">
              Grad-CAM Explainability
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
