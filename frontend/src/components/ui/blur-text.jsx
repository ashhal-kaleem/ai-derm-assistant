import React from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

export const BlurText = ({
  text = "",
  delay = 0.05,
  className = "",
  animateBy = "words", // 'words' | 'letters'
}) => {
  const elements = animateBy === "words" ? text.split(" ") : text.split("");

  return (
    <h1 className={cn("inline-flex flex-wrap items-center justify-center gap-x-2", className)}>
      {elements.map((segment, index) => (
        <motion.span
          key={index}
          initial={{ filter: "blur(10px)", opacity: 0, y: 10 }}
          animate={{ filter: "blur(0px)", opacity: 1, y: 0 }}
          transition={{
            duration: 0.5,
            delay: index * delay,
            ease: [0.25, 0.4, 0.25, 1],
          }}
          className="inline-block"
        >
          {segment}
        </motion.span>
      ))}
    </h1>
  );
};
