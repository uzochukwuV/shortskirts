import React from "react";
import { cn } from "@/lib/utils";

export default function Chip({ active = false, onClick, children, className }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-xs font-medium transition-all active:scale-95",
        active
          ? "border-ink bg-ink text-white"
          : "border-border bg-card text-muted-foreground hover:border-ink/40 hover:text-ink",
        className
      )}
    >
      {children}
    </button>
  );
}