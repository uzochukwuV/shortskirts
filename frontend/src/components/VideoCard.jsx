import React from "react";
import { Link } from "react-router-dom";
import { Play, Heart } from "lucide-react";
import VideoThumb from "@/components/VideoThumb";
import { cn } from "@/lib/utils";

export default function VideoCard({ video, className, showStatus = false }) {
  const ready = video.status === "ready";
  return (
    <Link
      to={ready ? `/video/${video.id}/edit` : `/generate/${video.id}`}
      className={cn("group block", className)}
    >
      <div className="relative">
        <VideoThumb aspect_ratio={video.aspect_ratio} src={video.thumbnail_url}>
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
          <div className="absolute inset-0 flex items-center justify-center opacity-0 transition-opacity group-hover:opacity-100">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/90 text-ink shadow-lg backdrop-blur">
              <Play className="h-4 w-4 fill-ink" />
            </span>
          </div>
          {showStatus && video.status !== "ready" && (
            <span className="absolute left-2 top-2 rounded-full bg-black/60 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur">
              {video.status}
            </span>
          )}
          <span className="absolute bottom-2 right-2 rounded-md bg-black/60 px-1.5 py-0.5 text-[10px] font-medium text-white backdrop-blur">
            {video.aspect_ratio}
          </span>
        </VideoThumb>
      </div>
      <div className="mt-2.5">
        <p className="line-clamp-1 text-[13px] font-medium text-ink">{video.prompt}</p>
        <div className="mt-1 flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="capitalize">{video.category}</span>
          <span className="flex items-center gap-1">
            <Heart className={cn("h-3 w-3", video.is_liked && "fill-ink text-ink")} />
            {video.likes || 0}
          </span>
        </div>
      </div>
    </Link>
  );
}