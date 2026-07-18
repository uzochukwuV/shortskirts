import { Play, SlidersHorizontal, Film } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Episode, Scene, Story } from "@/lib/api";
import { statusTone } from "./story-console-utils";

type Props = {
  story: Story;
  episodes: Episode[];
  scenes: Scene[];
  selectedScene: Scene | null;
  selectedEpisode: Episode | undefined;
  onSelectScene: (sceneId: string) => void;
  onOpenOutline: () => void;
  onOpenScript: () => void;
  onOpenHistory: () => void;
  onApproveScene: (sceneId: string) => void;
  onRejectScene: (sceneId: string) => void;
  onRegenerateScene: (sceneId: string) => void;
  onLockScene: (sceneId: string) => void;
  currentMedia?: string | null;
  currentKind?: "image" | "video";
  zoom: number;
  onZoomChange: (value: number[]) => void;
  latestStepLabel?: string | null;
};

function ScenePill({ scene, active, onClick }: { scene: Scene; active: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group min-w-[164px] overflow-hidden rounded-[14px] border text-left transition ${
        active ? "border-[#0c0a09] bg-white shadow-[0_0_0_2px_rgba(150,255,26,0.7)]" : "border-[#e6e6e7] bg-white hover:border-[#323232]"
      }`}
    >
      <div className="relative aspect-[16/9] bg-[#121212]">
        {scene.image_url || scene.media_url || scene.clip_url || scene.video_url ? (
          scene.image_url || scene.media_url ? (
            <img src={scene.image_url || scene.media_url} alt={scene.title || `Scene ${scene.scene_number}`} className="h-full w-full object-cover" />
          ) : (
            <video src={scene.clip_url || scene.video_url} className="h-full w-full object-cover" muted playsInline preload="metadata" />
          )
        ) : (
          <div className="flex h-full items-center justify-center text-white/35">
            <Film className="h-5 w-5" />
          </div>
        )}
        <div className="absolute left-2 top-2 rounded-[9999px] bg-black/70 px-2 py-0.5 text-[10px] font-bold text-white">S{scene.scene_number}</div>
      </div>
      <div className="p-2.5">
        <div className="truncate text-[12px] font-semibold text-[#0c0a09]">{scene.title || `Scene ${scene.scene_number}`}</div>
        <div className="mt-1 truncate text-[11px] text-[#71737a]">{scene.status}</div>
      </div>
    </button>
  );
}

export function ConsoleStage({
  story,
  episodes,
  scenes,
  selectedScene,
  selectedEpisode,
  onSelectScene,
  onOpenOutline,
  onOpenScript,
  onOpenHistory,
  onApproveScene,
  onRejectScene,
  onRegenerateScene,
  onLockScene,
  currentMedia,
  currentKind = "video",
  zoom,
  onZoomChange,
  latestStepLabel,
}: Props) {
  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[24px] border border-[#e6e6e7] bg-white">
      <div className="flex items-center gap-3 border-b border-[#e6e6e7] px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-[#71737a]">
            <span>{selectedEpisode ? `Episode ${selectedEpisode.episode_number}` : "Workspace"}</span>
            <span className="h-1 w-1 rounded-full bg-[#d4d4d8]" />
            <span>{story.workflow_type}</span>
          </div>
          <div className="mt-1 truncate text-lg font-extrabold text-[#0c0a09]">{selectedScene?.title || story.title}</div>
          <div className="mt-1 line-clamp-2 max-w-4xl text-sm leading-6 text-[#71737a]">
            {selectedScene?.description || story.prompt}
          </div>
        </div>
        <div className="hidden w-[250px] items-center gap-3 md:flex">
          <SlidersHorizontal className="h-4 w-4 text-[#71737a]" />
          <Slider value={[zoom]} onValueChange={onZoomChange} min={72} max={108} step={2} />
          <span className="w-9 text-right text-[11px] font-bold text-[#71737a]">{zoom}%</span>
        </div>
      </div>

      <div className="border-b border-[#e6e6e7] bg-[#f8f8f8] px-4 py-3">
        <ScrollArea className="w-full">
          <div className="flex gap-2 pb-1">
            {episodes.map((episode) => (
              <div key={episode.id} className="flex shrink-0 items-center gap-2 rounded-[9999px] border border-[#e6e6e7] bg-white px-3 py-1.5 text-[11px] text-[#323232]">
                <Badge className="border-[#e6e6e7] bg-[#f2f1f0] text-[#323232]">E{episode.episode_number}</Badge>
                <span className="max-w-[220px] truncate">{episode.title}</span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </div>

      <div className="min-h-0 flex-1 bg-[#ececec] p-5">
        <div className="flex h-full min-h-0 flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase text-[#71737a]">
              <Play className="h-3.5 w-3.5" />
              <span>{latestStepLabel || "Ready"}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" variant="outline" onClick={onOpenOutline}>Outline</Button>
              <Button size="sm" variant="outline" onClick={onOpenScript}>Story text</Button>
              <Button size="sm" variant="outline" onClick={onOpenHistory}>History</Button>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-hidden rounded-[24px] border border-[#d9d9d9] bg-white shadow-[0_20px_60px_rgba(0,0,0,0.12)]">
            {currentMedia ? (
              currentKind === "image" ? (
                <img src={currentMedia} alt={selectedScene?.title || "Selected scene"} className="h-full w-full object-contain bg-black" />
              ) : (
                <video src={currentMedia} className="h-full w-full object-contain bg-black" controls playsInline muted preload="metadata" />
              )
            ) : (
              <div className="flex h-full items-center justify-center text-center">
                <div className="max-w-sm">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#96ff1a] text-[#083300]">
                    <Play className="h-7 w-7" />
                  </div>
                  <div className="mt-5 text-2xl font-extrabold text-[#0c0a09]">No rendered scene yet</div>
                  <div className="mt-2 text-sm leading-6 text-[#71737a]">
                    Approve the outline and generate to populate the canvas.
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-[18px] border border-[#e6e6e7] bg-white p-3">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-[11px] font-bold uppercase text-[#71737a]">Scene strip</div>
              <div className="text-[11px] text-[#71737a]">{scenes.length} scenes</div>
            </div>
            <ScrollArea className="w-full">
              <div className="flex gap-3 pb-1">
                {scenes.map((scene) => (
                  <ScenePill
                    key={scene.id}
                    scene={scene}
                    active={selectedScene?.id === scene.id}
                    onClick={() => onSelectScene(scene.id)}
                  />
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </section>
  );
}
