import React, { useEffect } from "react";
import { motion, stagger, useAnimate } from "motion/react";
import { cn } from "@/lib/utils";

export const TextGenerateEffect = ({
  words = "",
  className,
  filter = true,
  duration = 0.4,
}) => {
  const [scope, animate] = useAnimate();
  const wordsArray = words.split(" ");

  useEffect(() => {
    if (words) {
      animate(
        "span",
        {
          opacity: 1,
          filter: filter ? "blur(0px)" : "none",
        },
        {
          duration: duration || 0.4,
          delay: stagger(0.04),
        }
      );
    }
  }, [words, duration, filter, animate]);

  return (
    <div className={cn("font-medium", className)}>
      <motion.div ref={scope} className="leading-relaxed">
        {wordsArray.map((word, idx) => (
          <motion.span
            key={word + idx}
            className="text-slate-800 opacity-0 inline-block mr-1"
            style={{
              filter: filter ? "blur(8px)" : "none",
            }}
          >
            {word}
          </motion.span>
        ))}
      </motion.div>
    </div>
  );
};
