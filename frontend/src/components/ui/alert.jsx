import React from "react";
import { cn } from "@/lib/utils";

export const Alert = ({ className, variant = "default", children, ...props }) => {
  return (
    <div
      role="alert"
      className={cn(
        "relative w-full rounded-2xl border p-4 text-xs [&>svg~*]:pl-7 [&>svg+div]:translate-y-[-3px] [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4",
        variant === "destructive" &&
          "border-red-500/30 bg-red-50/90 text-red-900 [&>svg]:text-red-600",
        variant === "warning" &&
          "border-amber-500/30 bg-amber-500/10 text-amber-900 [&>svg]:text-amber-600",
        variant === "default" &&
          "border-emerald-500/30 bg-emerald-500/10 text-emerald-900 [&>svg]:text-emerald-700",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
};

export const AlertTitle = ({ className, children, ...props }) => (
  <h5 className={cn("mb-1 font-heading font-bold leading-none tracking-tight", className)} {...props}>
    {children}
  </h5>
);

export const AlertDescription = ({ className, children, ...props }) => (
  <div className={cn("text-xs opacity-90 leading-relaxed font-sans", className)} {...props}>
    {children}
  </div>
);
