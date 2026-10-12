import React from "react";
import { cn } from "@/lib/utils";

export const Progress = ({ value = 0, className, barClassName, ...props }) => {
  const percent = Math.min(100, Math.max(0, value));

  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      className={cn("relative h-3 w-full overflow-hidden rounded-full bg-slate-100", className)}
      {...props}
    >
      <div
        className={cn("h-full w-full flex-1 transition-all duration-700 ease-out rounded-full bg-emerald-600", barClassName)}
        style={{ transform: `translateX(-${100 - percent}%)` }}
      />
    </div>
  );
};
