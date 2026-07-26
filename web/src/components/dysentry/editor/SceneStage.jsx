import React from "react";
import { RefreshCw, CheckCircle2, Eye, Film, Image as ImageIcon, Mic } from "lucide-react";
import Button from "../Button";

const typeTabs = [
  { id: "video", label: "Video", icon: Film },
  { id: "narrated_image", label: "Narrated image", icon: ImageIcon },
  { id: "voice", label: "Voice", icon: Mic },
];

export default function SceneStage({ scene, onChange, onRegenerate, onCheckpoint, regenerating }) {
  if (!scene) {
    return (
      <div className="flex h-full items-center justify-center text-[14px] text-steel">
        Select a scene to edit
      </div>
    );
  }
  return (
    <div className="flex flex-col lg:h-full">
      {/* Header */}
      <div className="flex flex-col gap-3 border-b border-mist px-8 py-5 sm:flex-row sm:items-center sm:justify-between">
        <input
          value={scene.title || ""}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="Untitled scene"
          className="font-display w-full bg-transparent text-[20px] font-medium tracking-tight-bold text-ink outline-none placeholder-steel"
        />
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="outline" onClick={onRegenerate} disabled={regenerating} className="px-4 py-2 text-[13px]">
            <RefreshCw className={`h-4 w-4 ${regenerating ? "animate-spin" : ""}`} />
            {regenerating ? "Regenerating" : "Regenerate"}
          </Button>
          {scene.status === "draft" && (
            <Button variant="outline" onClick={() => onCheckpoint("pending_review")} className="px-4 py-2 text-[13px]">
              <Eye className="h-4 w-4" /> Request review
            </Button>
          )}
          {scene.status === "pending_review" && (
            <Button onClick={() => onCheckpoint("approved")} className="px-4 py-2 text-[13px]">
              <CheckCircle2 className="h-4 w-4" /> Approve
            </Button>
          )}
          {scene.status === "approved" && (
            <span className="inline-flex items-center gap-1.5 text-[13px] text-ink">
              <CheckCircle2 className="h-4 w-4" /> Approved
            </span>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-8 py-8">
        <div className="mx-auto max-w-2xl space-y-8">
          {/* Type tabs */}
          <div className="flex items-center gap-6 border-b border-mist">
            {typeTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => onChange({ type: tab.id })}
                className={`flex items-center gap-2 border-b-2 pb-3 text-[14px] transition-colors ${scene.type === tab.id ? "border-ink font-medium text-ink" : "border-transparent text-steel hover:text-ink"}`}
              >
                <tab.icon className="h-4 w-4" /> {tab.label}
              </button>
            ))}
          </div>

          {/* Media preview */}
          <div className="flex aspect-video items-center justify-center rounded-2xl border border-fog bg-muted text-steel">
            {scene.media_url ? (
              <img src={scene.media_url} alt="" className="h-full w-full rounded-2xl object-cover" />
            ) : (
              <div className="text-center">
                <Film className="mx-auto h-8 w-8 text-ash" />
                <p className="mt-2 text-[13px]">No media attached</p>
              </div>
            )}
          </div>

          {/* Script */}
          <Field label="Script">
            <textarea
              value={scene.script || ""}
              onChange={(e) => onChange({ script: e.target.value })}
              placeholder="Describe the shot, action, and dialogue for this scene…"
              rows={6}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[16px] text-ink outline-none placeholder-steel focus:border-ash"
              style={{ lineHeight: 1.5 }}
            />
          </Field>

          {/* Narration */}
          <Field label="Narration / Voiceover">
            <textarea
              value={scene.narration || ""}
              onChange={(e) => onChange({ narration: e.target.value })}
              placeholder="Voiceover text for this scene…"
              rows={3}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[16px] text-ink outline-none placeholder-steel focus:border-ash"
              style={{ lineHeight: 1.5 }}
            />
          </Field>

          {/* Checkpoint notes */}
          <Field label="Checkpoint notes">
            <textarea
              value={scene.checkpoint_notes || ""}
              onChange={(e) => onChange({ checkpoint_notes: e.target.value })}
              placeholder="Reviewer feedback or production notes…"
              rows={2}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[14px] text-ink outline-none placeholder-steel focus:border-ash"
              style={{ lineHeight: 1.5 }}
            />
          </Field>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-2 block text-[11px] font-medium tracking-tight-bold text-steel uppercase">{label}</label>
      {children}
    </div>
  );
}