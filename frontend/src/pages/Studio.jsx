import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, ChevronLeft, Wand2 } from "lucide-react";
import AppLayout from "@/components/AppLayout";
import Chip from "@/components/Chip";
import { ASPECT_RATIOS, RESOLUTIONS, DURATIONS, MOTION_STYLES, CAMERA_MODES, PROMPT_SUGGESTIONS, createVideo } from "@/lib/video";

function SettingRow({ label, children }) {
  return (
    <div className="py-3">
      <p className="mb-2 text-xs font-medium text-muted-foreground">{label}</p>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

export default function Studio() {
  const location = useLocation();
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState(location.state?.prompt || "");
  const [settings, setSettings] = useState({
    aspect_ratio: "16:9",
    resolution: "1080p",
    duration: 6,
    motion_style: "cinematic",
    camera_mode: "dolly",
    category: "cinematic",
  });
  const [busy, setBusy] = useState(false);

  const set = (key, value) => setSettings((s) => ({ ...s, [key]: value }));

  const handleGenerate = async () => {
    if (prompt.trim().length < 3 || busy) return;
    setBusy(true);
    try {
      const video = await createVideo({ prompt: prompt.trim(), ...settings });
      navigate(`/generate/${video.id}`);
    } catch (e) {
      setBusy(false);
    }
  };

  return (
    <AppLayout>
      <div className="mb-5 flex items-center gap-2">
        <button onClick={() => navigate(-1)} className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card text-muted-foreground hover:text-ink">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <h1 className="font-display text-xl font-bold tracking-tight sm:text-2xl">Studio</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left: prompt + settings */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
          <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
            <label className="mb-2 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Wand2 className="h-3.5 w-3.5" /> Your prompt
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={4}
              maxLength={600}
              placeholder="Describe the scene you want to create…"
              className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            <div className="mt-1 flex justify-between text-[11px] text-muted-foreground">
              <span>Be vivid — mood, light, motion.</span>
              <span>{prompt.length}/600</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {PROMPT_SUGGESTIONS.map((s) => (
              <button key={s} type="button" onClick={() => setPrompt(s)} className="rounded-full border border-border bg-card px-3 py-1 text-[11px] text-muted-foreground hover:border-ink/40 hover:text-ink">
                {s}
              </button>
            ))}
          </div>

          <div className="rounded-2xl border border-border bg-card px-4 py-1 shadow-sm">
            <SettingRow label="Aspect ratio">
              {ASPECT_RATIOS.map((a) => <Chip key={a} active={settings.aspect_ratio === a} onClick={() => set("aspect_ratio", a)}>{a}</Chip>)}
            </SettingRow>
            <div className="h-px bg-border" />
            <SettingRow label="Resolution">
              {RESOLUTIONS.map((r) => <Chip key={r} active={settings.resolution === r} onClick={() => set("resolution", r)}>{r}</Chip>)}
            </SettingRow>
            <div className="h-px bg-border" />
            <SettingRow label="Duration">
              {DURATIONS.map((d) => <Chip key={d} active={settings.duration === d} onClick={() => set("duration", d)}>{d}s</Chip>)}
            </SettingRow>
            <div className="h-px bg-border" />
            <SettingRow label="Motion style">
              {MOTION_STYLES.map((m) => <Chip key={m} active={settings.motion_style === m} onClick={() => set("motion_style", m)} className="capitalize">{m}</Chip>)}
            </SettingRow>
            <div className="h-px bg-border" />
            <SettingRow label="Camera mode">
              {CAMERA_MODES.map((c) => <Chip key={c} active={settings.camera_mode === c} onClick={() => set("camera_mode", c)} className="capitalize">{c}</Chip>)}
            </SettingRow>
          </div>
        </motion.div>

        {/* Right: live preview */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="lg:sticky lg:top-6 lg:self-start">
          <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
            <div className={`relative bg-secondary ${settings.aspect_ratio === "9:16" ? "aspect-[9/16]" : settings.aspect_ratio === "1:1" ? "aspect-square" : "aspect-video"}`}>
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-center">
                <span className="relative flex h-14 w-14 items-center justify-center">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-ink/10" />
                  <span className="relative flex h-14 w-14 items-center justify-center rounded-full bg-ink text-white"><Sparkles className="h-5 w-5" /></span>
                </span>
                <p className="px-6 text-xs text-muted-foreground">Live preview will appear here once generated</p>
              </div>
              <div className="absolute left-3 top-3 flex gap-1.5">
                <span className="rounded-md bg-black/50 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur">{settings.aspect_ratio}</span>
                <span className="rounded-md bg-black/50 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur">{settings.resolution}</span>
              </div>
            </div>
            <div className="p-4">
              <p className="line-clamp-2 text-sm text-ink">{prompt || "Your prompt will show here…"}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] text-muted-foreground">
                <span className="capitalize">{settings.motion_style}</span>·
                <span className="capitalize">{settings.camera_mode}</span>·
                <span>{settings.duration}s</span>
              </div>
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={prompt.trim().length < 3 || busy}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-ink py-3.5 text-sm font-semibold text-white shadow-lg shadow-ink/10 transition-transform hover:scale-[1.01] disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" /> {busy ? "Starting…" : "Generate video"}
          </button>
        </motion.div>
      </div>
    </AppLayout>
  );
}