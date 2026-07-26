import React from "react";
import { cn } from "@/lib/utils";

export default function Button({ variant = "primary", className, children, ...props }) {
  const variants = {
    primary: "bg-signal text-white hover:bg-[#1557b8] shadow-subtle",
    secondary: "bg-transparent text-ink hover:text-steel",
    outline: "bg-white text-ink border border-fog hover:border-ash",
    ghost: "bg-transparent text-steel hover:text-ink",
    dark: "bg-ink text-white hover:bg-[#2a313a]",
  };
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg px-6 py-3 text-[16px] font-normal transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}