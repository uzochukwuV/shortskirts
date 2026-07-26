import React from "react";
import { Plus, GripVertical } from "lucide-react";
import SceneActionsDropdown from "./SceneActionsDropdown";

const statusStyles = {
  draft: "text-steel",
  pending_review: "text-ink font-medium",
  approved: "text-emerald-600",
  regenerating: "text-signal",
  locked: "text-amber-600",
};

const statusLabel = {
  draft: "Draft",
  pending_review: "In review",
  approved: "Approved",
  regenerating: "Regenerating",
  locked: "Locked",
};

export default function SceneList({ scenes, selectedId, onSelect, onAdd, adding, onDelete, onLock, onUnlock }) {
  return (
    <div className="flex flex-col lg:h-full">
      <div className="flex items-center justify-between border-b border-mist px-5 py-4">
        <h3 className="text-[14px] font-medium tracking-tight-bold text-ink">Scenes</h3>
        <button
          onClick={onAdd}
          disabled={adding}
          className="inline-flex items-center gap-1 text-[13px] text-signal transition-colors hover:text-[#1557b8] disabled:opacity-50"
        >
          <Plus className="h-3.5 w-3.5" /> Add
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {scenes.length === 0 && (
          <p className="px-5 py-8 text-[13px] text-steel">No scenes yet. Add your first scene to begin.</p>
        )}
        {scenes.map((scene, i) => (
          <div
            key={scene.id}
            className={`group flex items-start gap-2 border-b border-mist px-4 py-3 transition-colors ${selectedId === scene.id ? "bg-muted" : "hover:bg-muted/50"}`}
          >
            <button
              onClick={() => onSelect(scene.id)}
              className="flex min-w-0 flex-1 items-start gap-2 text-left"
            >
              <GripVertical className="mt-0.5 h-4 w-4 shrink-0 text-ash opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-steel">{String(i + 1).padStart(2, "0")}</span>
                  <span className={`text-[11px] ${statusStyles[scene.status] || statusStyles.draft}`}>
                    {scene.locked ? "Locked" : statusLabel[scene.status] || "Draft"}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-[13px] text-ink">{scene.title || "Untitled scene"}</p>
                <p className="mt-0.5 text-[10px] capitalize text-steel">{scene.type?.replace("_", " ")}</p>
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
        ))}
      </div>
    </div>
  );
}