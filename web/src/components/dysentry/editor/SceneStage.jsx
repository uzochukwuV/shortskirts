import React from "react";
import {
  RefreshCw,
  CheckCircle2,
  Eye,
  Film,
  Image as ImageIcon,
  Mic,
  Lock,
  XCircle,
  Sparkles,
  Loader2,
} from "lucide-react";
import Button from "../Button";

const typeTabs = [
  { id: "video", label: "Video", icon: Film },
  { id: "narrated_image", label: "Narrated image", icon: ImageIcon },
  { id: "voice", label: "Voice", icon: Mic },
];

const workflowSteps = [
  { id: "draft", label: "Draft" },
  { id: "regenerating", label: "Generating" },
  { id: "ready", label: "Ready" },
  { id: "pending_review", label: "In review" },
  { id: "approved", label: "Approved" },
];

function stepIndex(status) {
  if (status === "rejected") return 0;
  const idx = workflowSteps.findIndex((s) => s.id === status);
  return idx >= 0 ? idx : 0;
}

function MediaPreview({ scene, regenerating, jobStep }) {
  const isVideo =
    scene.type === "video" ||
    (!!scene.clip_url && !scene.image_url) ||
    (scene.media_url && /\.(mp4|webm|mov)(\?|$)/i.test(scene.media_url));
  const mediaSrc = scene.clip_url || scene.media_url || scene.image_url;

  if (regenerating) {
    return (
      <div className="flex aspect-video flex-col items-center justify-center gap-3 rounded-2xl border border-fog bg-muted text-steel">
        <Loader2 className="h-8 w-8 animate-spin text-signal" />
        <div className="text-center">
          <p className="text-[14px] font-medium text-ink">Generating media…</p>
          <p className="mt-1 text-[12px] text-steel">
            {jobStep || "Queued — this can take a minute"}
          </p>
        </div>
      </div>
    );
  }

  if (!mediaSrc) {
    return (
      <div className="flex aspect-video flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-fog bg-muted text-steel">
        <Film className="h-8 w-8 text-ash" />
        <p className="text-[13px] font-medium text-ink">No media yet</p>
        <p className="max-w-xs text-center text-[12px] text-steel">
          Write a visual prompt, then generate media for this scene.
        </p>
      </div>
    );
  }

  if (isVideo) {
    return (
      <div className="overflow-hidden rounded-2xl border border-fog bg-black">
        <video
          key={mediaSrc}
          src={mediaSrc}
          controls
          className="aspect-video h-full w-full object-contain"
        />
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-fog bg-muted">
      <img
        src={mediaSrc}
        alt={scene.title || "Scene media"}
        className="aspect-video h-full w-full object-cover"
      />
    </div>
  );
}

function WorkflowPills({ status }) {
  const current = stepIndex(status);
  const isRejected = status === "rejected";

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {isRejected && (
        <span className="rounded-full bg-red-50 px-2.5 py-1 text-[11px] font-medium text-red-600">
          Needs changes
        </span>
      )}
      {workflowSteps.map((step, i) => {
        const active = !isRejected && i === current;
        const done = !isRejected && i < current;
        return (
          <span
            key={step.id}
            className={`rounded-full px-2.5 py-1 text-[11px] transition-colors ${
              active
                ? "bg-ink text-white"
                : done
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-muted text-steel"
            }`}
          >
            {step.label}
          </span>
        );
      })}
    </div>
  );
}

export default function SceneStage({
  scene,
  onChange,
  onSave,
  onRegenerate,
  onCheckpoint,
  onReject,
  regenerating,
  saving,
  dirty,
  jobStep,
}) {
  if (!scene) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
        <Film className="h-10 w-10 text-ash" />
        <p className="text-[15px] font-medium text-ink">Select a scene to edit</p>
        <p className="max-w-sm text-[13px] text-steel">
          Pick a scene from the left, or add one to start drafting.
        </p>
      </div>
    );
  }

  const locked = !!scene.locked;
  const status = scene.status || "draft";
  const hasMedia = !!(scene.media_url || scene.clip_url || scene.image_url);
  const canApprove = !locked && (status === "ready" || status === "pending_review");
  const canRequestReview = !locked && (status === "draft" || status === "ready" || status === "rejected");
  const canReject = !locked && (status === "approved" || status === "pending_review" || status === "ready");
  const generateLabel = hasMedia ? "Regenerate" : "Generate media";

  return (
    <div className="flex flex-col lg:h-full">
      {/* Header */}
      <div className="flex flex-col gap-3 border-b border-mist px-6 py-4 sm:px-8 sm:py-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-[11px] uppercase tracking-tight-bold text-steel">
                Scene {String(scene.order || scene.scene_number || "").padStart(2, "0")}
              </span>
              {dirty && (
                <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                  Unsaved
                </span>
              )}
              {locked && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                  <Lock className="h-3 w-3" /> Locked
                </span>
              )}
              {scene.regeneration_count > 0 && (
                <span className="text-[11px] text-steel">
                  {scene.regeneration_count} regen{scene.regeneration_count === 1 ? "" : "s"}
                </span>
              )}
            </div>
            <input
              value={scene.title || ""}
              onChange={(e) => onChange({ title: e.target.value })}
              disabled={locked}
              placeholder="Untitled scene"
              className="font-display w-full bg-transparent text-[20px] font-medium tracking-tight-bold text-ink outline-none placeholder-steel disabled:opacity-60"
            />
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {onSave && (
              <Button
                variant="outline"
                onClick={onSave}
                disabled={saving || locked || !dirty}
                className="px-4 py-2 text-[13px]"
              >
                {saving ? "Saving…" : "Save"}
              </Button>
            )}
            <Button
              variant={hasMedia ? "outline" : "primary"}
              onClick={onRegenerate}
              disabled={regenerating || locked}
              className="px-4 py-2 text-[13px]"
              title={locked ? "Unlock scene to regenerate" : undefined}
            >
              <RefreshCw className={`h-4 w-4 ${regenerating ? "animate-spin" : ""}`} />
              {regenerating ? "Generating…" : generateLabel}
            </Button>
            {canRequestReview && (
              <Button
                variant="outline"
                onClick={() => onCheckpoint("pending_review")}
                className="px-4 py-2 text-[13px]"
              >
                <Eye className="h-4 w-4" /> Send for review
              </Button>
            )}
            {canApprove && (
              <Button onClick={() => onCheckpoint("approved")} className="px-4 py-2 text-[13px]">
                <CheckCircle2 className="h-4 w-4" /> Approve
              </Button>
            )}
            {status === "approved" && (
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-3 py-2 text-[13px] text-emerald-700">
                <CheckCircle2 className="h-4 w-4" /> Approved
              </span>
            )}
            {canReject && onReject && (
              <Button
                variant="outline"
                onClick={onReject}
                className="px-4 py-2 text-[13px] text-red-600 hover:border-red-200"
              >
                <XCircle className="h-4 w-4" /> Reject
              </Button>
            )}
          </div>
        </div>

        <WorkflowPills status={status} />
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-6 sm:px-8 sm:py-8">
        <div className="mx-auto max-w-2xl space-y-7">
          {/* Type tabs */}
          <div className="flex items-center gap-6 border-b border-mist">
            {typeTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => !locked && onChange({ type: tab.id })}
                disabled={locked}
                className={`flex items-center gap-2 border-b-2 pb-3 text-[14px] transition-colors disabled:cursor-not-allowed ${
                  scene.type === tab.id
                    ? "border-ink font-medium text-ink"
                    : "border-transparent text-steel hover:text-ink"
                }`}
              >
                <tab.icon className="h-4 w-4" /> {tab.label}
              </button>
            ))}
          </div>

          <MediaPreview scene={scene} regenerating={regenerating} jobStep={jobStep} />

          {!hasMedia && !regenerating && (
            <div className="flex items-start gap-3 rounded-xl border border-signal/20 bg-signal/5 px-4 py-3">
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
              <div className="text-[13px] text-ink" style={{ lineHeight: 1.5 }}>
                <p className="font-medium">Ready to generate?</p>
                <p className="mt-0.5 text-steel">
                  Fill in the visual prompt below, then click <span className="font-medium text-ink">Generate media</span>.
                  Edits are saved automatically before generation starts.
                </p>
              </div>
            </div>
          )}

          <Field
            label="Visual prompt"
            hint="What the model should render — composition, lighting, action"
          >
            <textarea
              value={scene.visual_prompt || ""}
              onChange={(e) => onChange({ visual_prompt: e.target.value, prompt: e.target.value })}
              disabled={locked}
              placeholder="Wide shot of a neon-lit alley at night, rain on the pavement, protagonist walking toward camera…"
              rows={4}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[15px] text-ink outline-none placeholder-steel focus:border-ash disabled:opacity-60"
              style={{ lineHeight: 1.5 }}
            />
          </Field>

          <Field label="Script" hint="Action, dialogue, and beat notes for this scene">
            <textarea
              value={scene.script || ""}
              onChange={(e) => onChange({ script: e.target.value })}
              disabled={locked}
              placeholder="Describe the shot, action, and dialogue for this scene…"
              rows={5}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[16px] text-ink outline-none placeholder-steel focus:border-ash disabled:opacity-60"
              style={{ lineHeight: 1.5 }}
            />
          </Field>

          <Field label="Narration / Voiceover">
            <textarea
              value={scene.narration || ""}
              onChange={(e) => onChange({ narration: e.target.value })}
              disabled={locked}
              placeholder="Voiceover text for this scene…"
              rows={3}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[16px] text-ink outline-none placeholder-steel focus:border-ash disabled:opacity-60"
              style={{ lineHeight: 1.5 }}
            />
          </Field>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Mood">
              <input
                value={scene.mood || ""}
                onChange={(e) => onChange({ mood: e.target.value })}
                disabled={locked}
                placeholder="Tense, hopeful, quiet…"
                className="w-full rounded-lg border border-fog bg-white px-4 py-2.5 text-[14px] text-ink outline-none placeholder-steel focus:border-ash disabled:opacity-60"
              />
            </Field>
            <Field label="Location">
              <input
                value={scene.location || ""}
                onChange={(e) => onChange({ location: e.target.value })}
                disabled={locked}
                placeholder="City rooftop, forest path…"
                className="w-full rounded-lg border border-fog bg-white px-4 py-2.5 text-[14px] text-ink outline-none placeholder-steel focus:border-ash disabled:opacity-60"
              />
            </Field>
          </div>

          <Field label="Reviewer notes" hint="Feedback when rejecting or requesting changes">
            <textarea
              value={scene.checkpoint_notes || ""}
              onChange={(e) => onChange({ checkpoint_notes: e.target.value })}
              disabled={locked}
              placeholder="What should change on the next pass…"
              rows={2}
              className="w-full resize-none rounded-lg border border-fog bg-white px-4 py-3 text-[14px] text-ink outline-none placeholder-steel focus:border-ash disabled:opacity-60"
              style={{ lineHeight: 1.5 }}
            />
          </Field>
        </div>
      </div>
    </div>
  );
}

function Field({ label, hint, children }) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <label className="block text-[11px] font-medium uppercase tracking-tight-bold text-steel">
          {label}
        </label>
        {hint && <span className="text-[11px] text-ash">{hint}</span>}
      </div>
      {children}
    </div>
  );
}
