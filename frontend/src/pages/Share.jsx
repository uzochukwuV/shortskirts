const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Copy, Check, Link2, Send } from "lucide-react";
import AppLayout from "@/components/AppLayout";

import { cn } from "@/lib/utils";

const PLATFORMS = [
  { id: "instagram", label: "Instagram", color: "#E1306C", handle: "@vivomatica" },
  { id: "tiktok", label: "TikTok", color: "#000000", handle: "@vivomatica" },
  { id: "youtube", label: "YouTube", color: "#FF0000", handle: "Vivomatica" },
  { id: "x", label: "X", color: "#000000", handle: "@vivomatica" },
  { id: "facebook", label: "Facebook", color: "#1877F2", handle: "Vivomatica" },
  { id: "reddit", label: "Reddit", color: "#FF4500", handle: "r/vivomatica" },
];

export default function Share() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [selected, setSelected] = useState(["instagram", "tiktok"]);
  const [caption, setCaption] = useState("Made with Vivomatica AI ✨ #aivideo #cinematic");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    db.entities.Video.get(id).then(setVideo);
  }, [id]);

  const toggle = (pid) => setSelected((s) => (s.includes(pid) ? s.filter((x) => x !== pid) : [...s, pid]));

  const copyLink = () => {
    navigator.clipboard?.writeText(video?.video_url || window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const ready = video?.status === "ready" && video.video_url;

  return (
    <AppLayout>
      <div className="mb-4 flex items-center gap-2">
        <button onClick={() => navigate(-1)} className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-ink">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="font-display text-lg font-bold tracking-tight sm:text-xl">Share</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: preview + caption */}
        <div className="space-y-4">
          <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
            {ready ? (
              <video src={video.video_url} poster={video.thumbnail_url} controls loop muted playsInline className={`w-full bg-black ${video.aspect_ratio === "9:16" ? "aspect-[9/16]" : video.aspect_ratio === "1:1" ? "aspect-square" : "aspect-video"}`} />
            ) : (
              <div className={`shimmer ${video?.aspect_ratio === "9:16" ? "aspect-[9/16]" : "aspect-video"}`} />
            )}
          </div>

          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground">Caption</p>
              <span className="text-[11px] text-muted-foreground">{caption.length}/500</span>
            </div>
            <textarea
              value={caption}
              onChange={(e) => setCaption(e.target.value.slice(0, 500))}
              rows={3}
              className="mt-2 w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
          </div>

          <button onClick={copyLink} className="flex w-full items-center justify-between rounded-2xl border border-border bg-card p-4 shadow-sm hover:border-ink/40">
            <div className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-ink"><Link2 className="h-4 w-4" /></span>
              <div className="text-left">
                <p className="text-sm font-medium">Copy link</p>
                <p className="text-[11px] text-muted-foreground">Anyone with the link can view</p>
              </div>
            </div>
            {copied ? <Check className="h-4 w-4 text-ink" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
          </button>
        </div>

        {/* Right: platforms */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold">Share to</h3>
            <p className="mt-1 text-xs text-muted-foreground">Select where to publish.</p>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {PLATFORMS.map((p) => {
                const active = selected.includes(p.id);
                return (
                  <button
                    key={p.id}
                    onClick={() => toggle(p.id)}
                    className={cn("flex items-center gap-2.5 rounded-xl border p-3 text-left transition-all", active ? "border-ink bg-ink/5" : "border-border hover:border-ink/30")}
                  >
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg text-white" style={{ backgroundColor: p.color }}>
                      <span className="text-xs font-bold">{p.label[0]}</span>
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium">{p.label}</p>
                      <p className="truncate text-[10px] text-muted-foreground">{p.handle}</p>
                    </div>
                    <span className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded-full border transition-colors", active ? "border-ink bg-ink text-white" : "border-border")}>
                      {active && <Check className="h-3 w-3" />}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          <button
            disabled={selected.length === 0}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-ink py-3.5 text-sm font-semibold text-white shadow-lg shadow-ink/10 transition-transform hover:scale-[1.01] disabled:opacity-50"
          >
            <Send className="h-4 w-4" /> Publish to {selected.length} {selected.length === 1 ? "platform" : "platforms"}
          </button>
          <p className="text-center text-[11px] text-muted-foreground">You'll be redirected to each platform to confirm.</p>
        </div>
      </div>
    </AppLayout>
  );
}