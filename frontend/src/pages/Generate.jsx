const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Check, MessageSquareText, Download, Share2, AlertTriangle, ArrowLeft } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import VideoThumb from "@/components/VideoThumb";

const PHASES = [
  { key: "queued", label: "Queued", desc: "Preparing your scene" },
  { key: "composing", label: "Composing", desc: "Building the visual frame" },
  { key: "rendering", label: "Rendering", desc: "Generating motion frames" },
  { key: "finalizing", label: "Finalizing", desc: "Polishing & encoding" },
];

export default function Generate() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [phase, setPhase] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    db.entities.Video.get(id).then((v) => { setVideo(v); setLoading(false); });
    const unsub = db.entities.Video.subscribe((event) => {
      if (event.data?.id === id) setVideo(event.data);
    });
    return unsub;
  }, [id]);

  // Animate phase progression while generating
  useEffect(() => {
    if (!video || video.status !== "generating") return;
    const t = setInterval(() => setPhase((p) => (p < PHASES.length - 1 ? p + 1 : p)), 3500);
    return () => clearInterval(t);
  }, [video?.status]);

  if (loading) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-xl">
          <div className="shimmer aspect-video rounded-2xl" />
        </div>
      </AppLayout>
    );
  }

  if (!video) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-xl py-20 text-center">
          <p className="text-sm text-muted-foreground">Video not found.</p>
          <Link to="/" className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-ink">Back home</Link>
        </div>
      </AppLayout>
    );
  }

  const isReady = video.status === "ready";
  const isFailed = video.status === "failed";

  return (
    <AppLayout>
      <div className="mx-auto max-w-xl">
        <button onClick={() => navigate(-1)} className="mb-4 inline-flex items-center gap-1 text-sm font-medium text-muted-foreground hover:text-ink">
          <ArrowLeft className="h-4 w-4" /> Back
        </button>

        <AnimatePresence mode="wait">
          {!isReady && !isFailed && (
            <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
                <VideoThumb aspect_ratio={video.aspect_ratio}>
                  <div className="absolute inset-0 shimmer opacity-60" />
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                    <span className="relative flex h-16 w-16 items-center justify-center">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ink/10" />
                      <span className="relative flex h-16 w-16 items-center justify-center rounded-full bg-ink text-white">
                        <Sparkles className="h-6 w-6 animate-spin-slow" />
                      </span>
                    </span>
                    <p className="text-sm font-medium text-ink">Rendering your video…</p>
                  </div>
                </VideoThumb>
              </div>

              <div className="mt-6 space-y-3">
                {PHASES.map((p, i) => {
                  const done = i < phase;
                  const active = i === phase;
                  return (
                    <div key={p.key} className="flex items-center gap-3">
                      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs transition-colors ${done ? "bg-ink text-white" : active ? "bg-ink/10 text-ink ring-2 ring-ink" : "bg-secondary text-muted-foreground"}`}>
                        {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                      </span>
                      <div className="flex-1">
                        <p className={`text-sm font-medium ${active || done ? "text-ink" : "text-muted-foreground"}`}>{p.label}</p>
                        <p className="text-xs text-muted-foreground">{p.desc}</p>
                      </div>
                      {active && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-ink" />}
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {isFailed && (
            <motion.div key="failed" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-2xl border border-border bg-card p-8 text-center shadow-sm">
              <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive"><AlertTriangle className="h-5 w-5" /></span>
              <h2 className="mt-4 text-base font-semibold">Rendering failed</h2>
              <p className="mt-1 text-sm text-muted-foreground">Something went wrong. You can try again.</p>
              <Link to="/studio" className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">Try again</Link>
            </motion.div>
          )}

          {isReady && (
            <motion.div key="ready" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
              <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
                <video src={video.video_url} poster={video.thumbnail_url} controls autoPlay loop muted playsInline className={`w-full bg-black ${video.aspect_ratio === "9:16" ? "aspect-[9/16]" : video.aspect_ratio === "1:1" ? "aspect-square" : "aspect-video"}`} />
              </div>

              <div className="mt-4">
                <p className="text-sm text-ink">{video.prompt}</p>
                <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
                  <span className="capitalize">{video.category}</span>·
                  <span>{video.resolution}</span>·
                  <span>{video.duration}s</span>·
                  <span className="capitalize">{video.motion_style}</span>
                </div>
              </div>

              <div className="mt-6 grid grid-cols-3 gap-2">
                <Link to={`/video/${video.id}/edit`} className="flex flex-col items-center gap-1.5 rounded-xl border border-border bg-card py-3 text-xs font-medium hover:border-ink/40">
                  <MessageSquareText className="h-4 w-4" /> Refine
                </Link>
                <Link to={`/video/${video.id}/export`} className="flex flex-col items-center gap-1.5 rounded-xl border border-border bg-card py-3 text-xs font-medium hover:border-ink/40">
                  <Download className="h-4 w-4" /> Export
                </Link>
                <Link to={`/video/${video.id}/share`} className="flex flex-col items-center gap-1.5 rounded-xl border border-border bg-card py-3 text-xs font-medium hover:border-ink/40">
                  <Share2 className="h-4 w-4" /> Share
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AppLayout>
  );
}