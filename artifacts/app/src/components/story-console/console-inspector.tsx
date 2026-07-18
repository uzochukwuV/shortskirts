import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import type { Character, GenerationJob, HistoryEntry, Scene, Story } from "@/lib/api";
import { formatShortDate, InspectorMode, statusTone } from "./story-console-utils";
import { Eye, History, ImagePlus, Layers3, MoreHorizontal, Settings2, Upload, Trash2 } from "lucide-react";

type RefAsset = { url: string; name: string };

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[12px] border border-[#e6e6e7] bg-[#f8f8f8] p-3">
      <div className="text-[10px] font-bold uppercase text-[#71737a]">{label}</div>
      <div className="mt-1 truncate text-sm font-extrabold text-[#0c0a09]">{value}</div>
    </div>
  );
}

function ModeButton({ mode, active, onClick, icon: Icon, label }: { mode: InspectorMode; active: InspectorMode; onClick: (mode: InspectorMode) => void; icon: any; label: string }) {
  return (
    <button
      type="button"
      onClick={() => onClick(mode)}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-[12px] px-3 py-2 text-[11px] font-bold transition ${
        active === mode ? "bg-[#0c0a09] text-white" : "bg-[#f2f1f0] text-[#71737a] hover:text-[#0c0a09]"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function RefGrid({
  items,
  onUpload,
  onRemove,
  disabled,
}: {
  items: RefAsset[];
  onUpload: (files: FileList | null) => void;
  onRemove: (url: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="text-[11px] font-bold uppercase text-[#71737a]">References</div>
        <label htmlFor="scene-ref-upload">
          <Button asChild variant="outline" size="sm" className="h-8 cursor-pointer">
            <span>
              <Upload className="h-3.5 w-3.5" />
              Upload
            </span>
          </Button>
        </label>
        <input id="scene-ref-upload" type="file" accept="image/*" multiple className="hidden" disabled={disabled} onChange={(e) => onUpload(e.target.files)} />
      </div>
      <div className="grid grid-cols-3 gap-2">
        {items.map((item) => (
          <div key={item.url} className="group relative overflow-hidden rounded-[12px] border border-[#e6e6e7] bg-[#f8f8f8]">
            <img src={item.url} alt={item.name} className="h-20 w-full object-cover" />
            <button type="button" onClick={() => onRemove(item.url)} className="absolute right-1 top-1 rounded-full bg-black/70 p-1 text-white opacity-0 group-hover:opacity-100">
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        ))}
        {!items.length && <div className="col-span-3 rounded-[12px] border border-dashed border-[#e6e6e7] bg-white px-3 py-4 text-xs text-[#71737a]">No refs uploaded.</div>}
      </div>
    </div>
  );
}

export function ConsoleInspector({
  story,
  latestJob,
  scene,
  characters,
  storyHistory,
  sceneHistory,
  referenceUrls,
  onReferenceUpload,
  onReferenceRemove,
  onApproveOutline,
  onGenerate,
  onApproveScene,
  onRejectScene,
  onRegenerateScene,
  onLockScene,
  onOpenHistory,
  onSetMode,
  mode,
  progressValue,
  completedScenes,
  expectedScenes,
  approvedScenes,
  sceneRefUploading,
}: {
  story: Story;
  latestJob: GenerationJob | null;
  scene: Scene | null;
  characters: Character[];
  storyHistory: HistoryEntry[];
  sceneHistory: HistoryEntry[];
  referenceUrls: string[];
  onReferenceUpload: (files: FileList | null) => void;
  onReferenceRemove: (url: string) => void;
  onApproveOutline: () => void;
  onGenerate: () => void;
  onApproveScene: (sceneId: string) => void;
  onRejectScene: (sceneId: string) => void;
  onRegenerateScene: (sceneId: string) => void;
  onLockScene: (sceneId: string) => void;
  onOpenHistory: () => void;
  onSetMode: (mode: InspectorMode) => void;
  mode: InspectorMode;
  progressValue: number;
  completedScenes: number;
  expectedScenes: number;
  approvedScenes: number;
  sceneRefUploading: boolean;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const sceneStatus = scene?.approval_status || scene?.status || "-";

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden rounded-[24px] border border-[#e6e6e7] bg-white">
      <div className="flex items-center justify-between gap-3 border-b border-[#e6e6e7] px-4 py-3">
        <div>
          <div className="text-[11px] font-bold uppercase text-[#71737a]">Inspector</div>
          <div className="mt-1 text-sm font-extrabold text-[#0c0a09]">Production state</div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="h-8 px-2">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onClick={onApproveOutline}>Approve outline</DropdownMenuItem>
            <DropdownMenuItem onClick={onGenerate}>Generate video</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onSetMode("scene")}>Scene</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onSetMode("refs")}>Refs</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onSetMode("cast")}>Cast</DropdownMenuItem>
            <DropdownMenuItem onClick={() => onSetMode("history")}>History</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="border-b border-[#e6e6e7] p-4">
        <div className="rounded-[18px] border border-[#e6e6e7] bg-[#f8f8f8] p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="text-[11px] font-bold uppercase text-[#71737a]">Story</div>
              <div className="mt-1 line-clamp-2 text-base font-extrabold text-[#0c0a09]">{story.title}</div>
            </div>
            <Badge className={statusTone(story.status)}>{story.status}</Badge>
          </div>
          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between text-[11px] font-bold text-[#71737a]">
              <span>{latestJob ? "Job progress" : "Generation progress"}</span>
              <span>{progressValue}%</span>
            </div>
            <Progress value={progressValue} className="h-2 bg-[#e6e6e7] [&>div]:bg-[#96ff1a]" />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Metric label="Scenes" value={`${completedScenes}/${expectedScenes || "-"}`} />
            <Metric label="Approved" value={`${approvedScenes}`} />
          </div>
          <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="mt-4 w-full">
                <Eye className="h-4 w-4" />
                View details
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-3xl rounded-[18px] border-[#e6e6e7] bg-white">
              <DialogHeader>
                <DialogTitle className="text-2xl font-extrabold text-[#0c0a09]">{story.title}</DialogTitle>
                <DialogDescription>Story, workflow, and outline summary.</DialogDescription>
              </DialogHeader>
              <div className="grid gap-3 md:grid-cols-4">
                <Metric label="Status" value={story.status} />
                <Metric label="Approval" value={story.approval_status} />
                <Metric label="Workflow" value={story.workflow_type} />
                <Metric label="Version" value={story.generation_version || "v1"} />
              </div>
              <div className="max-h-[320px] overflow-y-auto rounded-[14px] border border-[#e6e6e7] bg-[#f8f8f8] p-4 text-sm leading-7 text-[#323232]">
                {story.episode_plan?.synopsis || story.prompt}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="border-b border-[#e6e6e7] p-4">
        <div className="mb-3 flex gap-2">
          <ModeButton mode="scene" active={mode} onClick={onSetMode} icon={Settings2} label="Scene" />
          <ModeButton mode="refs" active={mode} onClick={onSetMode} icon={ImagePlus} label="Refs" />
          <ModeButton mode="cast" active={mode} onClick={onSetMode} icon={Layers3} label="Cast" />
          <ModeButton mode="history" active={mode} onClick={onSetMode} icon={History} label="History" />
        </div>

        {mode === "scene" && (
          <div className="space-y-3">
            <div className="rounded-[18px] border border-[#e6e6e7] bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-[11px] font-bold uppercase text-[#71737a]">Selected scene</div>
                  <div className="mt-1 truncate text-base font-extrabold text-[#0c0a09]">{scene?.title || "No scene selected"}</div>
                </div>
                <Badge className={statusTone(sceneStatus)}>{sceneStatus}</Badge>
              </div>
              <p className="mt-3 line-clamp-4 text-sm leading-6 text-[#71737a]">{scene?.description || "Select a scene to inspect it."}</p>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <Metric label="Status" value={scene?.status || "-"} />
                <Metric label="Version" value={scene?.generation_version || story.generation_version || "v1"} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" variant="lime" disabled={!scene} onClick={() => scene && onApproveScene(scene.id)}>Approve</Button>
                <Button size="sm" variant="outline" disabled={!scene} onClick={() => scene && onRejectScene(scene.id)}>Reject</Button>
                <Button size="sm" variant="outline" disabled={!scene} onClick={() => scene && onRegenerateScene(scene.id)}>Regenerate</Button>
                <Button size="sm" variant="ghost" disabled={!scene} onClick={() => scene && onLockScene(scene.id)}>Lock</Button>
              </div>
            </div>
          </div>
        )}

        {mode === "refs" && (
          <RefGrid
            items={referenceUrls.map((url) => ({ url, name: "scene reference" }))}
            onUpload={onReferenceUpload}
            onRemove={onReferenceRemove}
            disabled={sceneRefUploading}
          />
        )}

        {mode === "cast" && (
          <div className="space-y-2">
            {characters.slice(0, 5).map((character) => (
              <div key={character.id} className="rounded-[12px] border border-[#e6e6e7] bg-[#f8f8f8] p-3">
                <div className="text-sm font-extrabold text-[#0c0a09]">{character.name}</div>
                <div className="mt-1 text-[11px] text-[#71737a]">{character.role} / {character.approval_status}</div>
              </div>
            ))}
            {!characters.length && <div className="rounded-[12px] border border-dashed border-[#e6e6e7] bg-white p-4 text-sm text-[#71737a]">No characters yet.</div>}
          </div>
        )}

        {mode === "history" && (
          <div className="space-y-2">
            {sceneHistory.slice(0, 4).map((entry) => (
              <div key={entry.id} className="rounded-[12px] border border-[#e6e6e7] bg-[#f8f8f8] p-3">
                <div className="truncate text-sm font-extrabold text-[#0c0a09]">{entry.event_type}</div>
                <div className="mt-1 text-[11px] text-[#71737a]">v{entry.revision} / {formatShortDate(entry.created_at)}</div>
              </div>
            ))}
            <Button variant="outline" size="sm" className="w-full" onClick={onOpenHistory}>Open full history</Button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {storyHistory.slice(0, 3).map((entry) => (
            <div key={entry.id} className="rounded-[12px] border border-[#e6e6e7] bg-white p-3">
              <div className="truncate text-sm font-extrabold text-[#0c0a09]">{entry.event_type}</div>
              <div className="mt-1 text-[11px] text-[#71737a]">v{entry.revision} / {formatShortDate(entry.created_at)}</div>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
