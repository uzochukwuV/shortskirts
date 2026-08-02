import React from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/utils";

export default function Logo({ className, compact = false, to = "/" }) {
  return (
    <Link to={to} className={cn("inline-flex items-center gap-2.5 group", className)}>
      <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-xl bg-ink text-white shadow-sm transition-transform group-hover:scale-105">
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none">
          <path d="M9 7.5v9l7-4.5-7-4.5z" fill="currentColor" />
        </svg>
        <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-white ring-2 ring-ink" />
      </span>
      {!compact && (
        <span className="font-display text-[17px] font-extrabold tracking-tight text-ink">
          Vivomatica<span className="text-muted-foreground font-medium">AI</span>
        </span>
      )}
    </Link>
  );
}