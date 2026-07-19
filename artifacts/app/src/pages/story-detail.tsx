import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useLocation, useRoute } from "wouter";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  ChevronRight,
  Clapperboard,
  Clock3,
  Eye,
  FileText,
  Film,
  History,
  ImagePlus,
  Layers3,
  LayoutPanelLeft,
  Loader2,
  Lock,
  MessageSquareText,
  Mic2,
  MoreHorizontal,
  Play,
  RefreshCw,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trash2,
  Upload,
  Video,
  WandSparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { api, Character, Episode, GenerationJob, HistoryEntry, Scene, Story } from "@/lib/api";
import { ConsoleStage } from "@/components/story-console/console-stage";
import { ConsoleInspector } from "@/components/story-console/console-inspector";
import { ConsoleBottomTray } from "@/components/story-console/console-bottom-tray";
import { buildWorkspaceActivity } from "@/components/story-console/story-console-utils";

type ChatMessage = { role: "assistant" | "user"; text: string };
type RefAsset = { url: string; name: string };
type WorkspaceTab = "design" | "outline" | "script" | "history";
type InspectorMode = "scene" | "refs" | "cast" | "history";

function statusTone(status?: string) {
  if (status === "completed" || status === "ready" || status === "approved") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "draft" || status === "pending_approval") return "border-amber-200 bg-amber-50 text-amber-700";
  if (status === "generating" || status === "checkpoint_review") return "border-[#083300] bg-[#96ff1a] text-[#083300]";
  if (status === "failed" || status === "rejected") return "border-red-200 bg-red-50 text-red-700";
  return "border-[#e6e6e7] bg-white text-[#71737a]";
}

function formatShortDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function makeStoryText(story: Story) {
  const plan = story.episode_plan;
  if (!plan) return story.prompt;
  const lines: string[] = [];
  if (plan.synopsis) lines.push(plan.synopsis);
  for (const episode of plan.episodes || []) {
    lines.push("");
    lines.push(`Episode ${episode.episode_number}: ${episode.title}`);
    if (episode.summary) lines.push(episode.summary);
    for (const scene of episode.scenes || []) {
      lines.push("");
      lines.push(`Scene ${scene.scene_number}: ${scene.title}`);
      lines.push(scene.description || scene.action || "");
      if (scene.narration) lines.push(`Narration: ${scene.narration}`);
    }
  }
  return lines.filter(Boolean).join("\n");
}

function SceneTile({ scene, active, onClick }: { scene: Scene; active: boolean; onClick: () => void }) {
  const media = scene.image_url || scene.media_url || scene.clip_url || scene.video_url;
  const kind = scene.media_kind || (scene.image_url || scene.media_url ? "image" : "video");
  return (
    <button
      type="button"
      onClick={onClick}
      className={`group w-[156px] shrink-0 overflow-hidden rounded-[12px] border bg-white text-left transition ${
        active ? "border-[#0c0a09] shadow-[0_0_0_2px_rgba(150,255,26,0.8)]" : "border-[#e6e6e7] hover:border-[#323232]"
      }`}
    >
      <div className="relative aspect-video bg-[#121212]">
        {media ? (
          kind === "image" ? (
            <img src={media} alt={scene.title || `Scene ${scene.scene_number}`} className="h-full w-full object-cover" />
          ) : (
            <video src={media} className="h-full w-full object-cover" muted playsInline preload="metadata" />
          )
        ) : (
          <div className="flex h-full items-center justify-center text-white/35">
            <Video className="h-6 w-6" />
          </div>
        )}
        <div className="absolute left-2 top-2 rounded-[6px] bg-black/70 px-1.5 py-0.5 text-[10px] font-bold text-white">S{scene.scene_number}</div>
      </div>
      <div className="p-2">
        <div className="truncate text-[12px] font-semibold text-[#0c0a09]">{scene.title || `Scene ${scene.scene_number}`}</div>
        <div className="mt-1 truncate text-[11px] text-[#71737a]">{scene.status}</div>
      </div>
    </button>
  );
}

function SidebarButton({ icon: Icon, label, active, onClick }: { icon: any; label: string; active?: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full flex-col items-center gap-1 rounded-[10px] px-1 py-2 text-[10px] font-semibold transition ${
        active ? "bg-[#e6ffc8] text-[#083300]" : "text-[#71737a] hover:bg-[#f2f1f0] hover:text-[#0c0a09]"
      }`}
    >
      <Icon className="h-5 w-5" />
      <span>{label}</span>
    </button>
  );
}

function PanelSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-[#e6e6e7] p-4">
      <div className="mb-3 text-[11px] font-bold uppercase text-[#71737a]">{title}</div>
      {children}
    </section>
  );
}

function EmptyCanvas({ story }: { story: Story }) {
  return (
    <div className="flex h-full items-center justify-center text-center">
      <div className="max-w-sm">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#96ff1a] text-[#083300]">
          <Play className="h-7 w-7" />
        </div>
        <h2 className="mt-5 text-2xl font-extrabold text-[#0c0a09]">No rendered scene yet</h2>
        <p className="mt-2 text-sm leading-6 text-[#71737a]">
          {story.status === "draft" ? "Review the outline and approve it to begin video generation." : "Generated scene media will appear on the canvas."}
        </p>
      </div>
    </div>
  );
}

function OutlineView({ story }: { story: Story }) {
  const plan = story.episode_plan;
  if (!plan) return <EmptyCanvas story={story} />;
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-[980px] space-y-5">
        <section className="rounded-[16px] border border-[#e6e6e7] bg-white p-5">
          <div className="text-[11px] font-bold uppercase text-[#71737a]">Generated storyline</div>
          <h1 className="mt-2 text-3xl font-extrabold text-[#0c0a09]">{story.title}</h1>
          <p className="mt-3 text-sm leading-7 text-[#323232]">{plan.synopsis || story.prompt}</p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <Info label="Setting" value={plan.setting || "-"} />
            <Info label="Themes" value={(plan.themes || []).join(", ") || "-"} />
          </div>
        </section>

        {(plan.episodes || []).map((episode: any) => (
          <section key={episode.episode_number} className="overflow-hidden rounded-[16px] border border-[#e6e6e7] bg-white">
            <div className="border-b border-[#e6e6e7] p-5">
              <div className="text-[11px] font-bold uppercase text-[#71737a]">Episode {episode.episode_number}</div>
              <h2 className="mt-1 text-xl font-extrabold text-[#0c0a09]">{episode.title}</h2>
              <p className="mt-2 text-sm leading-6 text-[#71737a]">{episode.summary}</p>
            </div>
            <div className="divide-y divide-[#e6e6e7]">
              {(episode.scenes || []).map((scene: any) => (
                <div key={`${episode.episode_number}-${scene.scene_number}`} className="grid gap-4 p-5 md:grid-cols-[120px_1fr]">
                  <div>
                    <div className="text-[11px] font-bold uppercase text-[#083300]">Scene {scene.scene_number}</div>
                    <div className="mt-1 text-xs text-[#71737a]">{scene.duration_seconds || 6}s</div>
                  </div>
                  <div>
                    <div className="text-base font-extrabold text-[#0c0a09]">{scene.title}</div>
                    <p className="mt-1 text-sm leading-6 text-[#323232]">{scene.description}</p>
                    <div className="mt-3 grid gap-2 md:grid-cols-2">
                      <Info label="Location" value={scene.location || "-"} compact />
                      <Info label="Mood" value={scene.mood || "-"} compact />
                      <Info label="Cast" value={(scene.characters_present || []).join(", ") || "-"} compact />
                      <Info label="Narration" value={scene.narration || "-"} compact />
                    </div>
                    <div className="mt-3 rounded-[10px] bg-[#f2f1f0] p-3 text-xs leading-5 text-[#4d4d51]">{scene.visual_prompt || scene.action || scene.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function ScriptView({ story }: { story: Story }) {
  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-[860px] rounded-[16px] border border-[#e6e6e7] bg-white p-6">
        <div className="text-[11px] font-bold uppercase text-[#71737a]">Story text</div>
        <h1 className="mt-2 text-3xl font-extrabold text-[#0c0a09]">{story.title}</h1>
        <pre className="mt-5 whitespace-pre-wrap font-sans text-[15px] leading-8 text-[#323232]">{makeStoryText(story)}</pre>
      </div>
    </div>
  );
}

function HistoryView({ entries, selected, onSelect }: { entries: HistoryEntry[]; selected?: HistoryEntry | null; onSelect: (entry: HistoryEntry) => void }) {
  return (
    <div className="grid h-full grid-cols-[320px_1fr]">
      <div className="overflow-y-auto border-r border-[#e6e6e7] bg-white p-3">
        {entries.map((entry) => (
          <button
            key={entry.id}
            type="button"
            onClick={() => onSelect(entry)}
            className={`mb-2 w-full rounded-[12px] border p-3 text-left transition ${
              selected?.id === entry.id ? "border-[#0c0a09] bg-[#e6ffc8]" : "border-[#e6e6e7] bg-white hover:bg-[#f2f1f0]"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-sm font-extrabold text-[#0c0a09]">{entry.event_type}</span>
              <span className="text-[11px] text-[#71737a]">v{entry.revision}</span>
            </div>
            <div className="mt-1 text-xs text-[#71737a]">{formatShortDate(entry.created_at)}</div>
          </button>
        ))}
        {!entries.length && <div className="rounded-[12px] border border-dashed border-[#e6e6e7] p-4 text-sm text-[#71737a]">No history yet.</div>}
      </div>
      <div className="overflow-y-auto p-6">
        {selected ? (
          <div className="space-y-4">
            <section className="rounded-[16px] border border-[#e6e6e7] bg-white p-5">
              <div className="text-[11px] font-bold uppercase text-[#71737a]">Selected event</div>
              <h2 className="mt-1 text-2xl font-extrabold text-[#0c0a09]">{selected.event_type}</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge className="border-[#e6e6e7] bg-[#f2f1f0] text-[#323232]">revision {selected.revision}</Badge>
                <Badge className="border-[#e6e6e7] bg-[#f2f1f0] text-[#323232]">{selected.generation_version}</Badge>
                <Badge className="border-[#e6e6e7] bg-[#f2f1f0] text-[#323232]">{new Date(selected.created_at).toLocaleString()}</Badge>
              </div>
            </section>
            <JsonBlock title="Payload" value={selected.payload || {}} />
            <JsonBlock title="State snapshot" value={selected.state_snapshot || {}} />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-[#71737a]">Select a history item.</div>
        )}
      </div>
    </div>
  );
}

function Info({ label, value, compact }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={`rounded-[10px] border border-[#e6e6e7] bg-[#f8f8f8] ${compact ? "p-2" : "p-3"}`}>
      <div className="text-[10px] font-bold uppercase text-[#71737a]">{label}</div>
      <div className={`${compact ? "mt-1 text-xs" : "mt-2 text-sm"} leading-5 text-[#323232]`}>{value}</div>
    </div>
  );
}

function MetricPill({ label, value, tone = "light" }: { label: string; value: string; tone?: "light" | "dark" | "lime" }) {
  const toneClass =
    tone === "dark"
      ? "border-[#0c0a09] bg-[#0c0a09] text-white"
      : tone === "lime"
        ? "border-[#083300] bg-[#96ff1a] text-[#083300]"
        : "border-[#e6e6e7] bg-[#f8f8f8] text-[#323232]";
  return (
    <div className={`rounded-[12px] border px-3 py-2 ${toneClass}`}>
      <div className="text-[10px] font-bold uppercase opacity-65">{label}</div>
      <div className="mt-1 truncate text-sm font-extrabold">{value}</div>
    </div>
  );
}

function InspectorModeButton({ mode, active, icon: Icon, label, onClick }: { mode: InspectorMode; active: InspectorMode; icon: any; label: string; onClick: (mode: InspectorMode) => void }) {
  return (
    <button
      type="button"
      onClick={() => onClick(mode)}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-[10px] px-2 py-2 text-[11px] font-bold transition ${
        active === mode ? "bg-[#0c0a09] text-white" : "bg-[#f2f1f0] text-[#71737a] hover:text-[#0c0a09]"
      }`}
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </button>
  );
}

function JobActivity({ job }: { job?: GenerationJob | null }) {
  if (!job) {
    return (
      <div className="rounded-[12px] border border-dashed border-[#e6e6e7] bg-white p-3 text-sm text-[#71737a]">
        No active generation job yet.
      </div>
    );
  }
  const total = job.total_steps || 0;
  const value = total ? Math.min(100, Math.round((job.progress / total) * 100)) : job.status === "completed" ? 100 : 8;
  return (
    <div className="rounded-[12px] border border-[#e6e6e7] bg-white p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase text-[#71737a]">Live generation</div>
          <div className="mt-1 truncate text-sm font-extrabold text-[#0c0a09]">{job.current_step || job.status}</div>
        </div>
        <Badge className={statusTone(job.status)}>{job.status}</Badge>
      </div>
      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-[11px] font-bold text-[#71737a]">
          <span>{total ? `Step ${job.progress} of ${total}` : "Queued"}</span>
          <span>{value}%</span>
        </div>
        <Progress value={value} className="h-2 bg-[#e6e6e7] [&>div]:bg-[#96ff1a]" />
      </div>
      {job.error && <div className="mt-2 line-clamp-2 text-xs leading-5 text-red-600">{job.error}</div>}
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <section className="overflow-hidden rounded-[16px] border border-[#e6e6e7] bg-white">
      <div className="border-b border-[#e6e6e7] px-4 py-3 text-[11px] font-bold uppercase text-[#71737a]">{title}</div>
      <pre className="max-h-[360px] overflow-auto bg-[#f8f8f8] p-4 text-xs leading-5 text-[#323232]">{JSON.stringify(value, null, 2)}</pre>
    </section>
  );
}

function ReferencePanel({ items, onUpload, onRemove, disabled }: { items: RefAsset[]; onUpload: (files: FileList | null) => void; onRemove: (url: string) => void; disabled?: boolean }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-bold uppercase text-[#71737a]">Scene references</div>
        <label htmlFor="scene-ref-upload">
          <Button asChild variant="outline" size="sm" className="h-8 cursor-pointer">
            <span><Upload className="h-3.5 w-3.5" /> Upload</span>
          </Button>
        </label>
        <input id="scene-ref-upload" type="file" accept="image/*" multiple className="hidden" disabled={disabled} onChange={(e) => onUpload(e.target.files)} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {items.map((item) => (
          <div key={item.url} className="group relative overflow-hidden rounded-[10px] border border-[#e6e6e7] bg-[#f2f1f0]">
            <img src={item.url} alt={item.name} className="h-16 w-full object-cover" />
            <button type="button" onClick={() => onRemove(item.url)} className="absolute right-1 top-1 rounded bg-black/70 p-1 text-white opacity-0 group-hover:opacity-100">
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        ))}
        {!items.length && <div className="col-span-3 rounded-[10px] border border-dashed border-[#e6e6e7] p-3 text-xs text-[#71737a]">No refs uploaded.</div>}
      </div>
    </div>
  );
}

export default function StoryDetail() {
  const [, params] = useRoute("/stories/:id");
  const [, setLocation] = useLocation();
  const qc = useQueryClient();
  const id = params?.id || "";
  const [selectedSceneId, setSelectedSceneId] = useState("");
  const [tab, setTab] = useState<WorkspaceTab>("design");
  const [selectedHistoryId, setSelectedHistoryId] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [sceneRefUploading, setSceneRefUploading] = useState(false);
  const [inspectorMode, setInspectorMode] = useState<InspectorMode>("scene");
  const [canvasZoom, setCanvasZoom] = useState([92]);

  const { data: story, isLoading: storyLoading } = useQuery({
    queryKey: ["story", id],
    queryFn: () => api.getStory(id),
    enabled: !!id,
    refetchInterval: (query) => query.state.data?.status === "generating" || query.state.data?.status === "checkpoint_review" ? 5000 : false,
  });
  const { data: characters = [] } = useQuery({ queryKey: ["characters", id], queryFn: () => api.getCharacters(id), enabled: !!id });
  const { data: episodes = [] } = useQuery({
    queryKey: ["episodes", id],
    queryFn: () => api.getEpisodes(id),
    enabled: !!id,
    refetchInterval: story?.status === "generating" || story?.status === "checkpoint_review" ? 5000 : false,
  });
  const { data: storyHistory = [] } = useQuery({ queryKey: ["story-history", id], queryFn: () => api.getStoryHistory(id), enabled: !!id });
  const { data: storyJobs = [] } = useQuery({
    queryKey: ["story-jobs", id],
    queryFn: () => api.getEntityJobs("story", id),
    enabled: !!id,
    refetchInterval: story?.status === "generating" || story?.status === "checkpoint_review" ? 3000 : false,
  });
  const { data: checkpoints = [] } = useQuery({
    queryKey: ["checkpoints", id],
    queryFn: () => api.getStoryCheckpoints(id),
    enabled: !!id,
    refetchInterval: story?.status === "checkpoint_review" ? 5000 : false,
  });

  const allScenes = useMemo(() => episodes.flatMap((episode) => episode.scenes ?? []), [episodes]);
  const selectedScene = useMemo(() => allScenes.find((scene) => scene.id === selectedSceneId) ?? allScenes[0] ?? null, [allScenes, selectedSceneId]);
  const selectedEpisode = useMemo(() => episodes.find((episode) => episode.scenes?.some((scene) => scene.id === selectedScene?.id)) ?? episodes[0], [episodes, selectedScene]);
  const selectedHistory = useMemo(() => storyHistory.find((entry) => entry.id === selectedHistoryId) ?? storyHistory[0] ?? null, [storyHistory, selectedHistoryId]);
  const latestStoryJob = useMemo(() => storyJobs[0] ?? null, [storyJobs]);

  useEffect(() => {
    if (!selectedSceneId && allScenes.length > 0) setSelectedSceneId(allScenes[0].id);
  }, [allScenes, selectedSceneId]);

  useEffect(() => {
    if (!selectedHistoryId && storyHistory.length > 0) setSelectedHistoryId(storyHistory[0].id);
  }, [storyHistory, selectedHistoryId]);

  const { data: sceneHistory = [] } = useQuery({
    queryKey: ["scene-history", selectedScene?.id],
    queryFn: () => api.getSceneHistory(selectedScene!.id),
    enabled: !!selectedScene?.id,
  });

  const latestAudioCheckpoint = useMemo(
    () => [...checkpoints].filter((checkpoint) => checkpoint.narration_audio_url || checkpoint.audio_status === "completed").sort((a, b) => (a.batch_number || 0) - (b.batch_number || 0)).slice(-1)[0] ?? null,
    [checkpoints],
  );
  const activeCheckpoint = checkpoints.find((checkpoint) => checkpoint.status === "pending_review") ?? null;
  const checkpointAudioReady = !activeCheckpoint?.audio_status || activeCheckpoint.audio_status === "completed" || activeCheckpoint.audio_status === "failed";

  const approveOutline = useMutation({ mutationFn: () => api.approveOutline(id), onSuccess: () => qc.invalidateQueries({ queryKey: ["story", id] }) });
  const generateStory = useMutation({
    mutationFn: () => api.generateStory(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["episodes", id] });
    },
  });
  const approveCheckpoint = useMutation({
    mutationFn: (checkpointId: string) => api.approveCheckpoint(id, checkpointId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["story", id] });
      qc.invalidateQueries({ queryKey: ["checkpoints", id] });
    },
  });
  const approveScene = useMutation({ mutationFn: (sceneId: string) => api.approveScene(sceneId), onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }) });
  const rejectScene = useMutation({ mutationFn: (sceneId: string) => api.rejectScene(sceneId), onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }) });
  const lockScene = useMutation({ mutationFn: (sceneId: string) => api.lockScene(sceneId), onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }) });
  const regenerateScene = useMutation({ mutationFn: (sceneId: string) => api.regenerateScene(sceneId), onSuccess: () => qc.invalidateQueries({ queryKey: ["episodes", id] }) });

  const sceneReferenceUrls = useMemo(() => {
    const raw = selectedScene?.state_snapshot?.reference_image_urls;
    return Array.isArray(raw) ? raw.filter((item): item is string => typeof item === "string" && item.length > 0) : [];
  }, [selectedScene]);

  const uploadSceneRefs = async (files: FileList | null) => {
    if (!selectedScene || !files?.length) return;
    setSceneRefUploading(true);
    try {
      const uploads = await Promise.all(Array.from(files).map(async (file) => (await api.uploadImage(file)).url));
      await api.updateSceneReferences(selectedScene.id, [...sceneReferenceUrls, ...uploads]);
      qc.invalidateQueries({ queryKey: ["episodes", id] });
      qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
    } finally {
      setSceneRefUploading(false);
    }
  };

  useEffect(() => {
    if (!story || messages.length > 0) return;
    setMessages([{ role: "assistant", text: `Workspace loaded for ${story.title}. Review the outline, open story text, or select a scene.` }]);
  }, [story, messages.length]);

  const sendMessage = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    const lower = trimmed.toLowerCase();
    if (lower.includes("approve outline") && story?.status === "draft") {
      approveOutline.mutate();
      setMessages((prev) => [...prev, { role: "assistant", text: "Outline approval queued." }]);
    } else if (lower.includes("approve checkpoint") && activeCheckpoint?.id && checkpointAudioReady) {
      approveCheckpoint.mutate(activeCheckpoint.id);
      setMessages((prev) => [...prev, { role: "assistant", text: "Checkpoint approval queued." }]);
    } else if (lower.includes("generate")) {
      generateStory.mutate();
      setMessages((prev) => [...prev, { role: "assistant", text: "Generation queued." }]);
    } else if (lower.includes("approve scene") && selectedScene) {
      approveScene.mutate(selectedScene.id);
      setMessages((prev) => [...prev, { role: "assistant", text: `Scene ${selectedScene.scene_number} approval queued.` }]);
    } else if (lower.includes("reject scene") && selectedScene) {
      rejectScene.mutate(selectedScene.id);
      setMessages((prev) => [...prev, { role: "assistant", text: `Scene ${selectedScene.scene_number} rejection queued.` }]);
    } else if (lower.includes("regenerate") && selectedScene) {
      regenerateScene.mutate(selectedScene.id);
      setMessages((prev) => [...prev, { role: "assistant", text: `Scene ${selectedScene.scene_number} regeneration queued.` }]);
    } else {
      setMessages((prev) => [...prev, { role: "assistant", text: selectedScene ? `Focused on ${selectedScene.title || `Scene ${selectedScene.scene_number}`}.` : "Open the outline or select a scene." }]);
    }
  };

  const onSubmitPrompt = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    sendMessage(prompt);
    setPrompt("");
  };

  if (storyLoading) return <div className="flex h-screen items-center justify-center bg-[#f2f1f0] text-[#71737a]">Loading workspace...</div>;
  if (!story) return <div className="flex h-screen items-center justify-center bg-[#f2f1f0] text-[#0c0a09]">Story not found.</div>;

  const currentMedia = selectedEpisode?.assembled_video_url || selectedScene?.image_url || selectedScene?.media_url || selectedScene?.clip_url || selectedScene?.video_url;
  const currentKind = selectedEpisode?.assembled_video_url
    ? "video"
    : selectedScene?.media_kind || (selectedScene?.image_url || selectedScene?.media_url ? "image" : "video");
  const expectedScenes = (story.num_episodes || 1) * (story.num_scenes || 0);
  const completedScenes = allScenes.filter((scene) => scene.status === "completed" || scene.status === "ready").length;
  const approvedScenes = allScenes.filter((scene) => scene.approval_status === "approved").length;
  const progressValue = latestStoryJob?.total_steps
    ? Math.min(100, Math.round((latestStoryJob.progress / latestStoryJob.total_steps) * 100))
    : expectedScenes
      ? Math.min(100, Math.round((completedScenes / expectedScenes) * 100))
      : 0;
  const activityItems = useMemo(
    () =>
      buildWorkspaceActivity({
        story,
        episodes,
        allScenes,
        characters,
        storyHistory,
        sceneHistory,
        checkpoints,
        latestStoryJob,
        selectedScene,
      }),
    [story, episodes, allScenes, characters, storyHistory, sceneHistory, checkpoints, latestStoryJob, selectedScene],
  );
  const zoomScale = Math.max(0.62, Math.min(1.1, canvasZoom[0] / 100));

  return (
    <div className="min-h-[calc(100vh-120px)] overflow-hidden bg-background text-foreground">
      <header className="flex h-14 items-center gap-3 border-b border-border bg-white px-4">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm" className="px-2">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-[12px] bg-[color:#96ff1a] text-[color:#083300]">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-extrabold">{story.title}</div>
            <div className="text-[11px] text-muted-foreground">{story.workflow_type}</div>
          </div>
          <Badge className={statusTone(story.status)}>{story.status}</Badge>
          <Badge className="border-border bg-muted text-foreground">{progressValue}%</Badge>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {story.status === "draft" && (
            <Button variant="lime" size="sm" onClick={() => approveOutline.mutate()} disabled={approveOutline.isPending}>
              {approveOutline.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
              Approve outline
            </Button>
          )}
          {story.status === "approved" && (
            <Button variant="lime" size="sm" onClick={() => generateStory.mutate()} disabled={generateStory.isPending}>
              {generateStory.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <WandSparkles className="h-4 w-4" />}
              Generate
            </Button>
          )}
          {activeCheckpoint && (
            <Button variant="outline" size="sm" onClick={() => approveCheckpoint.mutate(activeCheckpoint.id)} disabled={!checkpointAudioReady || approveCheckpoint.isPending}>
              <CheckCircle2 className="h-4 w-4" />
              Approve checkpoint
            </Button>
          )}
        </div>
      </header>

      <div className="grid gap-4 p-4 xl:grid-cols-[320px_minmax(0,1fr)_340px]">
        <aside className="space-y-4">
          <section className="rounded-[24px] border border-border bg-white p-4 shadow-[0_18px_40px_rgba(0,0,0,0.03)]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Workspace</div>
                <div className="mt-1 text-sm font-semibold text-foreground">Production map</div>
              </div>
              <Badge className="border-border bg-muted text-foreground">{allScenes.length}/{expectedScenes || "-"}</Badge>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <button type="button" onClick={() => setTab("outline")} className="flex items-center justify-between rounded-[14px] border border-border bg-muted/30 px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-muted/60">
                <span className="flex items-center gap-2"><FileText className="h-4 w-4" /> Outline</span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
              <button type="button" onClick={() => setTab("script")} className="flex items-center justify-between rounded-[14px] border border-border bg-muted/30 px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-muted/60">
                <span className="flex items-center gap-2"><Clapperboard className="h-4 w-4" /> Story text</span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
              <button type="button" onClick={() => setTab("history")} className="flex items-center justify-between rounded-[14px] border border-border bg-muted/30 px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-muted/60">
                <span className="flex items-center gap-2"><History className="h-4 w-4" /> History</span>
                <span className="text-xs text-muted-foreground">{storyHistory.length}</span>
              </button>
              <button type="button" onClick={() => setInspectorMode("scene")} className="flex items-center justify-between rounded-[14px] border border-border bg-muted/30 px-3 py-2 text-left text-sm font-medium text-foreground hover:bg-muted/60">
                <span className="flex items-center gap-2"><Layers3 className="h-4 w-4" /> Scene controls</span>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
          </section>

          <ConsoleBottomTray
            latestJobLabel={latestStoryJob?.current_step || latestStoryJob?.status || null}
            messages={messages}
            prompt={prompt}
            setPrompt={setPrompt}
            onSubmit={onSubmitPrompt}
            latestAudioCheckpoint={latestAudioCheckpoint}
            activityItems={activityItems}
          />
        </aside>

        <ConsoleStage
          story={story}
          episodes={episodes}
          scenes={allScenes}
          selectedScene={selectedScene}
          selectedEpisode={selectedEpisode}
          onSelectScene={setSelectedSceneId}
          onOpenOutline={() => setTab("outline")}
          onOpenScript={() => setTab("script")}
          onOpenHistory={() => setTab("history")}
          onApproveScene={(sceneId) => approveScene.mutate(sceneId)}
          onRejectScene={(sceneId) => rejectScene.mutate(sceneId)}
          onRegenerateScene={(sceneId) => regenerateScene.mutate(sceneId)}
          onLockScene={(sceneId) => lockScene.mutate(sceneId)}
          currentMedia={currentMedia}
          currentKind={currentKind}
          zoom={canvasZoom[0]}
          onZoomChange={setCanvasZoom}
          latestStepLabel={latestStoryJob?.current_step || latestStoryJob?.status || null}
        />

        <ConsoleInspector
          story={story}
          latestJob={latestStoryJob}
          scene={selectedScene}
          characters={characters}
          storyHistory={storyHistory}
          sceneHistory={sceneHistory}
          referenceUrls={sceneReferenceUrls}
          onReferenceUpload={(files) => void uploadSceneRefs(files)}
          onReferenceRemove={(url) => void (async () => {
            if (!selectedScene) return;
            await api.updateSceneReferences(selectedScene.id, sceneReferenceUrls.filter((item) => item !== url));
            qc.invalidateQueries({ queryKey: ["episodes", id] });
            qc.invalidateQueries({ queryKey: ["scene-history", selectedScene.id] });
          })()}
          onApproveOutline={() => approveOutline.mutate()}
          onGenerate={() => generateStory.mutate()}
          onApproveScene={(sceneId) => approveScene.mutate(sceneId)}
          onRejectScene={(sceneId) => rejectScene.mutate(sceneId)}
          onRegenerateScene={(sceneId) => regenerateScene.mutate(sceneId)}
          onLockScene={(sceneId) => lockScene.mutate(sceneId)}
          onOpenHistory={() => setTab("history")}
          onSetMode={setInspectorMode}
          mode={inspectorMode}
          progressValue={progressValue}
          completedScenes={completedScenes}
          expectedScenes={expectedScenes}
          approvedScenes={approvedScenes}
          sceneRefUploading={sceneRefUploading}
        />
      </div>

      <Dialog open={tab !== "design"} onOpenChange={(open) => !open && setTab("design")}>
        <DialogContent className="max-h-[85vh] max-w-5xl overflow-hidden rounded-[24px] border-[#e6e6e7] bg-white">
          <DialogHeader>
            <DialogTitle className="text-2xl font-extrabold text-[#0c0a09]">
              {tab === "outline" ? "Outline" : tab === "script" ? "Story text" : "History"}
            </DialogTitle>
            <DialogDescription>
              {tab === "outline" ? "Generated structure, episode summaries, and scene guidance." : tab === "script" ? "Readable story text built from the outline." : "Revision history and state snapshots."}
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[70vh] overflow-y-auto">
            {tab === "outline" && <OutlineView story={story} />}
            {tab === "script" && <ScriptView story={story} />}
            {tab === "history" && <HistoryView entries={storyHistory} selected={selectedHistory} onSelect={(entry) => setSelectedHistoryId(entry.id)} />}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
