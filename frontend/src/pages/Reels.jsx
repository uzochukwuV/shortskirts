const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Heart, MessageCircle, Share2, Music2, ArrowLeft, Play } from "lucide-react";

import { cn } from "@/lib/utils";

export default function Reels() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef(null);

  useEffect(() => {
    db.entities.Video.filter({ status: "ready" }, "-likes", 50)
      .then((data) => setVideos(data || []))
      .finally(() => setLoading(false));
  }, []);

  const toggleLike = (video) => {
    db.entities.Video.update(video.id, { is_liked: !video.is_liked, likes: (video.likes || 0) + (video.is_liked ? -1 : 1) });
    setVideos((prev) => prev.map((v) => (v.id === video.id ? { ...v, is_liked: !v.is_liked, likes: (v.likes || 0) + (v.is_liked ? -1 : 1) } : v)));
  };

  const onScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const idx = Math.round(el.scrollTop / el.clientHeight);
    setActiveIndex(idx);
  };

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-black">
        <Play className="h-8 w-8 animate-pulse text-white/40" />
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-black px-6 text-center">
        <p className="text-sm text-white/70">No reels yet.</p>
        <Link to="/studio" className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-black">Create a video</Link>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-black lg:pl-64">
      <button onClick={() => navigate(-1)} className="absolute left-4 top-4 z-30 flex h-9 w-9 items-center justify-center rounded-full bg-black/40 text-white backdrop-blur lg:left-[19rem]">
        <ArrowLeft className="h-4 w-4" />
      </button>

      {/* Mobile: vertical scroll feed; Desktop: centered player */}
      <div
        ref={containerRef}
        onScroll={onScroll}
        className="h-full snap-y snap-mandatory overflow-y-auto no-scrollbar lg:flex lg:items-center lg:justify-center lg:overflow-hidden"
      >
        {videos.map((video, i) => {
          const active = i === activeIndex;
          return (
            <div key={video.id} className="relative h-screen w-full snap-center lg:h-[86vh] lg:w-auto lg:aspect-[9/16]">
              <video
                src={video.video_url}
                poster={video.thumbnail_url}
                autoPlay={active}
                loop
                muted
                playsInline
                className="h-full w-full object-cover lg:rounded-3xl"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20 lg:rounded-3xl" />

              {/* Right action rail */}
              <div className="absolute bottom-24 right-3 flex flex-col items-center gap-5 lg:bottom-10">
                <button onClick={() => toggleLike(video)} className="flex flex-col items-center gap-1">
                  <span className={cn("flex h-11 w-11 items-center justify-center rounded-full bg-black/30 backdrop-blur", video.is_liked && "text-white")}>
                    <Heart className={cn("h-5 w-5", video.is_liked ? "fill-white text-white" : "text-white")} />
                  </span>
                  <span className="text-[11px] font-medium text-white">{video.likes || 0}</span>
                </button>
                <button className="flex flex-col items-center gap-1">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-black/30 backdrop-blur"><MessageCircle className="h-5 w-5 text-white" /></span>
                  <span className="text-[11px] font-medium text-white">Comment</span>
                </button>
                <button onClick={() => navigate(`/video/${video.id}/share`)} className="flex flex-col items-center gap-1">
                  <span className="flex h-11 w-11 items-center justify-center rounded-full bg-black/30 backdrop-blur"><Share2 className="h-5 w-5 text-white" /></span>
                  <span className="text-[11px] font-medium text-white">Share</span>
                </button>
              </div>

              {/* Bottom info */}
              <div className="absolute bottom-24 left-4 right-16 lg:bottom-10 lg:left-6 lg:right-20">
                <p className="text-sm font-semibold text-white">vivomatica</p>
                <p className="mt-1.5 line-clamp-2 text-sm text-white/90">{video.prompt}</p>
                <div className="mt-2 flex items-center gap-1.5 text-[11px] text-white/70">
                  <Music2 className="h-3 w-3" /> Original audio · {video.motion_style} · {video.duration}s
                </div>
                <Link to={`/video/${video.id}/edit`} className="mt-3 inline-flex items-center gap-1 rounded-full bg-white/90 px-3 py-1.5 text-xs font-semibold text-black">
                  Edit this video
                </Link>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}