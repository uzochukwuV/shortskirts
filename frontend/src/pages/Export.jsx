const db = globalThis.__B44_DB__ || { auth:{ isAuthenticated: async()=>false, me: async()=>null }, entities:new Proxy({}, { get:()=>({ filter:async()=>[], get:async()=>null, create:async()=>({}), update:async()=>({}), delete:async()=>({}) }) }), integrations:{ Core:{ UploadFile:async()=>({ file_url:'' }) } } };

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Download, Copy, Check, ExternalLink, ChevronRight } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import Chip from "@/components/Chip";

const STEPS = [
  { key: "save", label: "Save the video", desc: "Download to your device" },
  { key: "caption", label: "Copy the caption", desc: "We wrote one for you" },
  { key: "tiktok", label: "Open TikTok", desc: "Upload and paste" },
];

const CAPTION = "Made with Vivomatica AI ✨ #aivideo #cinematic #vivomatica";

export default function Export() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [video, setVideo] = useState(null);
  const [step, setStep] = useState(0);
  const [copied, setCopied] = useState(false);
  const [format, setFormat] = useState("mp4");
  const [resolution, setResolution] = useState("1080p");

  useEffect(() => {
    db.entities.Video.get(id).then(setVideo);
  }, [id]);

  const copyCaption = () => {
    navigator.clipboard?.writeText(CAPTION);
    setCopied(true);
    setStep(2);
    setTimeout(() => setCopied(false), 2000);
  };

  const download = () => {
    if (video?.video_url) {
      const a = document.createElement("a");
      a.href = video.video_url;
      a.download = `vivomatica-${id}.mp4`;
      a.click();
    }
    setStep(1);
  };

  const ready = video?.status === "ready" && video.video_url;

  return (
    <AppLayout>
      <div className="mb-4 flex items-center gap-2">
        <button onClick={() => navigate(-1)} className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-ink">
          <ArrowLeft className="h-4 w-4" />
        </button>
        <h1 className="font-display text-lg font-bold tracking-tight sm:text-xl">Export</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: preview + TikTok card */}
        <div className="space-y-4">
          <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
            {ready ? (
              <video src={video.video_url} poster={video.thumbnail_url} controls loop muted playsInline className={`w-full bg-black ${video.aspect_ratio === "9:16" ? "aspect-[9/16]" : video.aspect_ratio === "1:1" ? "aspect-square" : "aspect-video"}`} />
            ) : (
              <div className={`shimmer ${video?.aspect_ratio === "9:16" ? "aspect-[9/16]" : "aspect-video"}`} />
            )}
          </div>

          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-ink text-xs font-bold text-white">T</span>
              <div>
                <p className="text-sm font-semibold">Direct to TikTok</p>
                <p className="text-xs text-muted-foreground">Guided 3-step upload</p>
              </div>
            </div>

            <div className="mt-4 space-y-2.5">
              {STEPS.map((s, i) => {
                const done = i < step;
                const active = i === step;
                return (
                  <div key={s.key} className={`flex items-center gap-3 rounded-xl border p-2.5 transition-colors ${active ? "border-ink bg-ink/5" : "border-border"}`}>
                    <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs ${done ? "bg-ink text-white" : active ? "bg-ink/10 text-ink" : "bg-secondary text-muted-foreground"}`}>
                      {done ? <Check className="h-3.5 w-3.5" /> : i + 1}
                    </span>
                    <div className="flex-1">
                      <p className="text-xs font-medium">{s.label}</p>
                      <p className="text-[11px] text-muted-foreground">{s.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-4 flex gap-2">
              {step === 0 && <button onClick={download} disabled={!ready} className="flex-1 rounded-full bg-ink py-2.5 text-xs font-semibold text-white disabled:opacity-50">Save video</button>}
              {step === 1 && <button onClick={copyCaption} className="flex-1 rounded-full bg-ink py-2.5 text-xs font-semibold text-white">{copied ? "Copied!" : "Copy caption"}</button>}
              {step >= 2 && <a href="https://www.tiktok.com/upload" target="_blank" rel="noreferrer" className="flex flex-1 items-center justify-center gap-1.5 rounded-full bg-ink py-2.5 text-xs font-semibold text-white">Open TikTok <ExternalLink className="h-3.5 w-3.5" /></a>}
            </div>
          </div>
        </div>

        {/* Right: manual download */}
        <div className="space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <h3 className="text-sm font-semibold">Manual download</h3>
            <p className="mt-1 text-xs text-muted-foreground">Choose your format and resolution.</p>

            <div className="mt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Format</p>
              <div className="flex gap-2">
                {["mp4", "mov", "webm"].map((f) => <Chip key={f} active={format === f} onClick={() => setFormat(f)} className="uppercase">{f}</Chip>)}
              </div>
            </div>

            <div className="mt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Resolution</p>
              <div className="flex gap-2">
                {["720p", "1080p", "4K"].map((r) => <Chip key={r} active={resolution === r} onClick={() => setResolution(r)}>{r}</Chip>)}
              </div>
            </div>

            <button onClick={download} disabled={!ready} className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-ink py-3 text-sm font-semibold text-white disabled:opacity-50">
              <Download className="h-4 w-4" /> Download {resolution} {format.toUpperCase()}
            </button>
          </div>

          <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
            <p className="text-xs text-muted-foreground">Caption</p>
            <p className="mt-1.5 text-sm">{CAPTION}</p>
            <button onClick={copyCaption} className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-ink">
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />} {copied ? "Copied" : "Copy caption"}
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}