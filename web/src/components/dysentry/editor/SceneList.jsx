import React from "react";
import { Plus, GripVertical, Lock, Film, Image as ImageIcon, Mic } from "lucide-react";
import SceneActionsDropdown from "./SceneActionsDropdown";

const statusStyles = {
  draft: "bg-muted text-steel",
  regenerating: "bg-signal/10 text-signal",
  ready: "bg-sky-50 text-sky-700",
  pending_review: "bg-amber-50 text-amber-700",
  approved: "bg-emerald-50 text-emerald-700",
  rejected: "bg-red-50 text-red-600",
};

const statusLabel = {
  draft: "Draft",
  regenerating: "Generating",
  ready: "Ready",
  pending_review: "In review",
  approved: "Approved",
  rejected: "Needs changes",
};

const typeIcon = {
  video: Film,
  narrated_image: ImageIcon,
  voice: Mic,
};

export default function SceneList({
  scenes,
  selectedId,
  onSelect,
  onAdd,
  adding,
  onDelete,
  onLock,
  onUnlock,
}) {
  const approved = scenes.filter((s) => s.status === "approved" || s.approval_status === "approved").length;
  const total = scenes.length;
  const progress = total ? Math.round((approved / total) * 100) : 0;

  return (
    <div className="flex flex-col lg:h-full">
      <div className="border-b border-mist px-5 py-4">
        <div className="flex items-center justify-between">
          <h3 className="text-[14px] font-medium tracking-tight-bold text-ink">Scenes</h3>
          <button
            onClick={onAdd}
            disabled={adding}
            className="inline-flex items-center gap-1 text-[13px] text-signal transition-colors hover:text-[#1557b8] disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" /> Add
          </button>
        </div>
        {total > 0 && (
          <div className="mt-3">
            <div className="mb-1.5 flex items-center justify-between text-[11px] text-steel">
              <span>
                {approved}/{total} approved
              </span>
              <span>{progress}%</span>
            </div>
            <div className="h-1 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {scenes.length === 0 && (
          <div className="px-5 py-10 text-center">
            <Film className="mx-auto h-7 w-7 text-ash" />
            <p className="mt-3 text-[13px] text-steel">No scenes yet.</p>
            <button
              onClick={onAdd}
              disabled={adding}
              className="mt-3 text-[13px] text-signal hover:text-[#1557b8]"
            >
              Add your first scene
            </button>
          </div>
        )}

        {scenes.map((scene, i) => {
          const selected = selectedId === scene.id;
          const TypeIcon = typeIcon[scene.type] || Film;
          const thumb = scene.image_url || (scene.type !== "video" ? scene.media_url : null);
          const badge = scene.locked
            ? { label: "Locked", className: "bg-amber-50 text-amber-700" }
            : {
                label: statusLabel[scene.status] || "Draft",
                className: statusStyles[scene.status] || statusStyles.draft,
              };

          return (
            <div
              key={scene.id}
              className={`group flex items-start gap-2 border-b border-mist px-3 py-3 transition-colors ${
                selected ? "bg-muted" : "hover:bg-muted/50"
              }`}
            >
              <button
                onClick={() => onSelect(scene.id)}
                className="flex min-w-0 flex-1 items-start gap-2.5 text-left"
              >
                <GripVertical className="mt-2 h-4 w-4 shrink-0 text-ash opacity-0 transition-opacity group-hover:opacity-100" />

                <div className="relative mt-0.5 h-11 w-14 shrink-0 overflow-hidden rounded-md border border-fog bg-muted">
                  {thumb ? (
                    <img src={thumb} alt="" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center">
                      <TypeIcon className="h-3.5 w-3.5 text-ash" />
                    </div>
                  )}
                  {scene.status === "regenerating" && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/70">
                      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-mist border-t-signal" />
                    </div>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-steel">{String(i + 1).padStart(2, "0")}</span>
                    <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${badge.className}`}>
                      {badge.label}
                    </span>
                    {scene.locked && <Lock className="h-3 w-3 text-amber-600" />}
                  </div>
                  <p className="mt-0.5 truncate text-[13px] text-ink">{scene.title || "Untitled scene"}</p>
                  <p className="mt-0.5 truncate text-[11px] text-steel">
                    {scene.visual_prompt || scene.script || scene.type?.replace("_", " ")}
                  </p>
                </div>
              </button>

              {onDelete && (
                <SceneActionsDropdown
                  scene={scene}
                  onDelete={() => onDelete(scene.id)}
                  onLock={scene.locked ? null : () => onLock?.(scene.id)}
                  onUnlock={scene.locked ? () => onUnlock?.(scene.id) : null}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
