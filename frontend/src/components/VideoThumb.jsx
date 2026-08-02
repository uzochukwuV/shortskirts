import React from "react";
import { cn } from "@/lib/utils";

const ASPECT_CLASS = {
  "16:9": "aspect-video",
  "9:16": "aspect-[9/16]",
  "1:1": "aspect-square",
};

export default function VideoThumb({ aspect_ratio = "16:9", src, className, children }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl bg-secondary",
        ASPECT_CLASS[aspect_ratio] || "aspect-video",
        className
      )}
    >
      {src ? (
        <img src={src} alt="" className="h-full w-full object-cover" />
      ) : (
        <div className="h-full w-full bg-gradient-to-br from-secondary to-accent" />
      )}
      {children}
    </div>
  );
}