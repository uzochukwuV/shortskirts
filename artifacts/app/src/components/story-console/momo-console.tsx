import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  AudioLines,
  BookOpen,
  Check,
  ChevronRight,
  Clapperboard,
  Clock3,
  FolderKanban,
  History,
  ImagePlus,
  LayoutPanelLeft,
  Lock,
  Play,
  ScrollText,
  Send,
  Sparkles,
  Users2,
  Video,
  WandSparkles,
  XCircle,
} from "lucide-react";
import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import type {
  Character,
  Episode,
  GenerationCheckpoint,
  GenerationJob,
  HistoryEntry,
  Scene,
  Story,
} from "@/lib/api";

export type ConsoleWorkspace = "canvas" | "outline" | "script" | "history" | "cast" | "references" | "runs";
export type AssistantTarget = "story" | "scene";
type ChatMessage = { role: "assistant" | "user"; text: string };

type StoryDraft = Partial<{
  title: string;
  prompt: string;
  genre: string;
  style: string;
  synopsis: string;
  setting: string;
  themes: string[];
}>;

type SceneDraft = Partial<{
  prompt: string;
  title: string;
  description: string;
  visual_prompt: string;
  mood: string;
  location: string;
  action: string;
  narration: string;
}>;

type Props = {
  story: Story;
  episodes: Episode[];
  scenes: Scene[];
  characters: Character[];
  storyHistory: HistoryEntry[];
  sceneHistory: HistoryEntry[];
  selectedScene: Scene | null;
  selectedEpisode?: Episode;
  activeWorkspace: ConsoleWorkspace;
  onChangeWorkspace: (workspace: ConsoleWorkspace) => void;
  onSelectScene: (sceneId: string) => void;
  onApproveOutline: () => void;
  onGenerate: () => void;
  onApproveScene: (sceneId: string) => void;
  onRejectScene: (sceneId: string) => void;
  onRegenerateScene: (sceneId: string) => void;
  onLockScene: (sceneId: string) => void;
  onSaveStoryEdit: (patch: StoryDraft) => void;
  onSaveSceneEdit: (sceneId: string, patch: SceneDraft) => void;
  currentMedia?: string | null;
  currentKind?: "image" | "video";
  latestJob: GenerationJob | null;
  latestAudioCheckpoint: GenerationCheckpoint | null;
  progressValue: number;
  prompt: string;
  setPrompt: (value: string) => void;
  assistantTarget: AssistantTarget;
  setAssistantTarget: (target: AssistantTarget) => void;
  onSendAssistant: () => void;
  messages: ChatMessage[];
  referenceUrls: string[];
  onReferenceUpload: (files: FileList | null) => void;
  onReferenceRemove: (url: string) => void;
  sceneRefUploading: boolean;
  assistantMessage?: string | null;
  storyDraft?: StoryDraft | null;
  sceneDraft?: SceneDraft | null;
  onApplyStoryDraft: () => void;
  onApplySceneDraft: () => void;
  assistantBusy?: boolean;
};

function workflowLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function statusTone(status?: string) {
  if (status === "completed" || status === "ready" || status === "approved") return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100";
  if (status === "failed" || status === "rejected" || status === "canceled") return "border-red-500/30 bg-red-500/10 text-red-100";
  if (status === "generating" || status === "running" || status === "checkpoint_review") return "border-sky-500/30 bg-sky-500/10 text-sky-100";
  return "border-zinc-800 bg-zinc-950 text-zinc-300";
}

function sceneMedia(scene?: Scene | null) {
  if (!scene) return null;
  return scene.image_url || scene.media_url || scene.clip_url || scene.video_url || null;
}

function durationForScene(scene: Scene, fallback = 6) {
  const raw = scene.duration || scene.state_snapshot?.duration_seconds;
  return typeof raw === "number" && raw > 0 ? raw : fallback;
}

function formatDateTime(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function timeAgo(value?: string | null) {
  if (!value) return "";
  const diff = Math.max(0, Date.now() - new Date(value).getTime());
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-zinc-500">{children}</div>;
}

function SidebarButton({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: any;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`grid w-full gap-1 rounded-2xl border px-3 py-3 text-left transition ${
        active
          ? "border-zinc-700 bg-zinc-900 text-white"
          : "border-transparent bg-transparent text-zinc-500 hover:border-zinc-900 hover:bg-zinc-950 hover:text-zinc-200"
      }`}
    >
      <Icon className="h-4 w-4" />
      <span className="text-[11px] font-medium">{label}</span>
    </button>
  );
}

function MetricCard({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "highlight" }) {
  return (
    <div className={`rounded-2xl border p-3 ${tone === "highlight" ? "border-sky-500/30 bg-sky-500/8" : "border-zinc-800 bg-zinc-950"}`}>
      <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">{label}</div>
      <div className="mt-1 text-[13px] font-medium text-white">{value}</div>
    </div>
  );
}

function JsonPreview({ value }: { value: unknown }) {
  return <pre className="overflow-auto rounded-2xl border border-zinc-800 bg-zinc-950 p-3 text-[11px] leading-6 text-zinc-300">{JSON.stringify(value, null, 2)}</pre>;
}

function StoryEditorSheet({
  story,
  onSave,
}: {
  story: Story;
  onSave: (patch: StoryDraft) => void;
}) {
  const plan = story.episode_plan || {};
  const [title, setTitle] = useState(story.title);
  const [prompt, setPrompt] = useState(story.prompt);
  const [synopsis, setSynopsis] = useState(plan.synopsis || "");
  const [setting, setSetting] = useState(plan.setting || "");
  const [themes, setThemes] = useState(Array.isArray(plan.themes) ? plan.themes.join(", ") : "");

  useEffect(() => {
    setTitle(story.title);
    setPrompt(story.prompt);
    setSynopsis(plan.synopsis || "");
    setSetting(plan.setting || "");
    setThemes(Array.isArray(plan.themes) ? plan.themes.join(", ") : "");
  }, [story.title, story.prompt, plan.synopsis, plan.setting, plan.themes]);

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 border-zinc-800 bg-zinc-950 text-[11px] text-zinc-200 hover:bg-zinc-900">
          <ScrollText className="h-3.5 w-3.5" />
          Edit story
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[420px] border-zinc-800 bg-black text-white">
        <SheetHeader>
          <SheetTitle className="text-left text-white">Story editor</SheetTitle>
          <SheetDescription className="text-left text-zinc-500">
            Update the production brief, synopsis, and high-level direction without leaving the console.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          <div className="space-y-2">
            <SectionLabel>Title</SectionLabel>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} className="border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="space-y-2">
            <SectionLabel>Prompt</SectionLabel>
            <Textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} className="min-h-[120px] border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="space-y-2">
            <SectionLabel>Synopsis</SectionLabel>
            <Textarea value={synopsis} onChange={(e) => setSynopsis(e.target.value)} className="min-h-[120px] border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="space-y-2">
            <SectionLabel>Setting</SectionLabel>
            <Textarea value={setting} onChange={(e) => setSetting(e.target.value)} className="min-h-[88px] border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="space-y-2">
            <SectionLabel>Themes</SectionLabel>
            <Input value={themes} onChange={(e) => setThemes(e.target.value)} className="border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <Button
            className="w-full"
            variant="lime"
            onClick={() =>
              onSave({
                title,
                prompt,
                synopsis,
                setting,
                themes: themes.split(",").map((part) => part.trim()).filter(Boolean),
              })
            }
          >
            Save story changes
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function SceneEditorSheet({
  scene,
  onSave,
}: {
  scene: Scene | null;
  onSave: (sceneId: string, patch: SceneDraft) => void;
}) {
  const [title, setTitle] = useState(scene?.title || "");
  const [description, setDescription] = useState(scene?.description || "");
  const [visualPrompt, setVisualPrompt] = useState(scene?.visual_prompt || "");
  const [narration, setNarration] = useState(scene?.narration || "");
  const [mood, setMood] = useState(scene?.mood || "");
  const [location, setLocation] = useState(scene?.location || "");

  useEffect(() => {
    setTitle(scene?.title || "");
    setDescription(scene?.description || "");
    setVisualPrompt(scene?.visual_prompt || "");
    setNarration(scene?.narration || "");
    setMood(scene?.mood || "");
    setLocation(scene?.location || "");
  }, [scene?.id, scene?.title, scene?.description, scene?.visual_prompt, scene?.narration, scene?.mood, scene?.location]);

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 border-zinc-800 bg-zinc-950 text-[11px] text-zinc-200 hover:bg-zinc-900" disabled={!scene}>
          <LayoutPanelLeft className="h-3.5 w-3.5" />
          Edit scene
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[420px] border-zinc-800 bg-black text-white">
        <SheetHeader>
          <SheetTitle className="text-left text-white">{scene?.title || "Scene editor"}</SheetTitle>
          <SheetDescription className="text-left text-zinc-500">
            Tune the selected scene text before approving or regenerating.
          </SheetDescription>
        </SheetHeader>
        <div className="mt-6 space-y-4">
          <div className="space-y-2">
            <SectionLabel>Title</SectionLabel>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} className="border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="space-y-2">
            <SectionLabel>Description</SectionLabel>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} className="min-h-[100px] border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="space-y-2">
            <SectionLabel>Visual prompt</SectionLabel>
            <Textarea value={visualPrompt} onChange={(e) => setVisualPrompt(e.target.value)} className="min-h-[120px] border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <SectionLabel>Mood</SectionLabel>
              <Input value={mood} onChange={(e) => setMood(e.target.value)} className="border-zinc-800 bg-zinc-950 text-zinc-100" />
            </div>
            <div className="space-y-2">
              <SectionLabel>Location</SectionLabel>
              <Input value={location} onChange={(e) => setLocation(e.target.value)} className="border-zinc-800 bg-zinc-950 text-zinc-100" />
            </div>
          </div>
          <div className="space-y-2">
            <SectionLabel>Narration</SectionLabel>
            <Textarea value={narration} onChange={(e) => setNarration(e.target.value)} className="min-h-[100px] border-zinc-800 bg-zinc-950 text-zinc-100" />
          </div>
          <Button
            className="w-full"
            variant="lime"
            disabled={!scene}
            onClick={() =>
              scene &&
              onSave(scene.id, {
                title,
                description,
                visual_prompt: visualPrompt,
                narration,
                mood,
                location,
              })
            }
          >
            Save scene changes
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function StoryOutlineView({ story }: { story: Story }) {
  const episodes = story.episode_plan?.episodes || [];
  return (
    <div className="grid gap-4">
      <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
        <SectionLabel>Synopsis</SectionLabel>
        <div className="mt-3 text-[13px] leading-7 text-zinc-200">{story.episode_plan?.synopsis || story.prompt}</div>
      </div>
      {episodes.map((episode: any) => (
        <div key={episode.episode_number} className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-zinc-500">Episode {episode.episode_number}</div>
              <div className="mt-1 text-[16px] font-medium text-white">{episode.title}</div>
              <div className="mt-2 text-[12px] leading-6 text-zinc-400">{episode.summary}</div>
            </div>
            <Badge className="border-zinc-800 bg-black text-zinc-300">{(episode.scenes || []).length} scenes</Badge>
          </div>
          <div className="mt-4 grid gap-3">
            {(episode.scenes || []).map((scene: any) => (
              <div key={`${episode.episode_number}-${scene.scene_number}`} className="rounded-2xl border border-zinc-800 bg-black/60 p-4">
                <div className="flex items-center gap-3">
                  <Badge className="border-zinc-800 bg-zinc-950 text-zinc-300">Scene {scene.scene_number}</Badge>
                  <div className="text-[13px] font-medium text-white">{scene.title}</div>
                </div>
                <div className="mt-2 text-[12px] leading-6 text-zinc-400">{scene.description}</div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <MetricCard label="Location" value={scene.location || "-"} />
                  <MetricCard label="Mood" value={scene.mood || "-"} />
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ScriptView({ story }: { story: Story }) {
  const plan = story.episode_plan || {};
  const lines: string[] = [];
  if (plan.synopsis) lines.push(plan.synopsis);
  for (const episode of plan.episodes || []) {
    lines.push("");
    lines.push(`Episode ${episode.episode_number}: ${episode.title}`);
    if (episode.summary) lines.push(episode.summary);
    for (const scene of episode.scenes || []) {
      lines.push("");
      lines.push(`Scene ${scene.scene_number}: ${scene.title}`);
      if (scene.description) lines.push(scene.description);
      if (scene.narration) lines.push(`Narration: ${scene.narration}`);
    }
  }

  return (
    <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
      <SectionLabel>Story text</SectionLabel>
      <pre className="mt-4 whitespace-pre-wrap font-sans text-[13px] leading-7 text-zinc-200">{lines.join("\n")}</pre>
    </div>
  );
}

function HistoryView({
  entries,
  selectedId,
  onSelect,
}: {
  entries: HistoryEntry[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const selected = entries.find((entry) => entry.id === selectedId) || entries[0] || null;
  return (
    <div className="grid min-h-0 gap-4 xl:grid-cols-[280px_minmax(0,1fr)]">
      <ScrollArea className="min-h-0 rounded-[24px] border border-zinc-800 bg-zinc-950">
        <div className="p-3">
          {entries.map((entry) => (
            <button
              key={entry.id}
              type="button"
              onClick={() => onSelect(entry.id)}
              className={`mb-2 w-full rounded-2xl border p-3 text-left transition ${
                selected?.id === entry.id ? "border-zinc-700 bg-black text-white" : "border-zinc-900 bg-zinc-950 text-zinc-400 hover:border-zinc-800 hover:bg-black"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <div className="truncate text-[12px] font-medium">{entry.event_type}</div>
                <div className="text-[10px] text-zinc-500">v{entry.revision}</div>
              </div>
              <div className="mt-1 text-[10px] text-zinc-500">{formatDateTime(entry.created_at)}</div>
            </button>
          ))}
        </div>
      </ScrollArea>
      <div className="grid gap-4">
        {selected ? (
          <>
            <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
              <SectionLabel>Selected event</SectionLabel>
              <div className="mt-2 text-[18px] font-medium text-white">{selected.event_type}</div>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-zinc-400">
                <Badge className="border-zinc-800 bg-black text-zinc-300">revision {selected.revision}</Badge>
                <Badge className="border-zinc-800 bg-black text-zinc-300">{selected.generation_version}</Badge>
                <Badge className="border-zinc-800 bg-black text-zinc-300">{formatDateTime(selected.created_at)}</Badge>
              </div>
            </div>
            <JsonPreview value={selected.payload || {}} />
            <JsonPreview value={selected.state_snapshot || {}} />
          </>
        ) : (
          <div className="rounded-[24px] border border-dashed border-zinc-800 bg-zinc-950 p-5 text-[12px] text-zinc-500">No history yet.</div>
        )}
      </div>
    </div>
  );
}

function SceneStrip({
  scenes,
  selectedScene,
  onSelectScene,
}: {
  scenes: Scene[];
  selectedScene: Scene | null;
  onSelectScene: (sceneId: string) => void;
}) {
  return (
    <ScrollArea className="w-full whitespace-nowrap">
      <div className="flex gap-3 pb-1">
        {scenes.map((scene) => {
          const media = sceneMedia(scene);
          const active = selectedScene?.id === scene.id;
          return (
            <button
              key={scene.id}
              type="button"
              onClick={() => onSelectScene(scene.id)}
              className={`w-36 shrink-0 overflow-hidden rounded-2xl border text-left transition ${active ? "border-sky-400 bg-black" : "border-zinc-800 bg-zinc-950 hover:border-zinc-700"}`}
            >
              <div className="relative aspect-video bg-black">
                {media ? (
                  scene.media_kind === "image" || scene.image_url ? (
                    <img src={media} alt={scene.title || `Scene ${scene.scene_number}`} className="h-full w-full object-cover" />
                  ) : (
                    <video src={media} className="h-full w-full object-cover" muted playsInline preload="metadata" />
                  )
                ) : (
                  <div className="flex h-full items-center justify-center text-zinc-600">
                    <Video className="h-5 w-5" />
                  </div>
                )}
                <div className="absolute left-2 top-2 rounded-full bg-black/80 px-2 py-1 text-[9px] font-medium text-white">S{scene.scene_number}</div>
              </div>
              <div className="p-3">
                <div className="truncate text-[12px] font-medium text-white">{scene.title || `Scene ${scene.scene_number}`}</div>
                <div className="mt-1 truncate text-[10px] text-zinc-500">{scene.status}</div>
              </div>
            </button>
          );
        })}
      </div>
    </ScrollArea>
  );
}

export function MomoConsole({
  story,
  episodes,
  scenes,
  characters,
  storyHistory,
  sceneHistory,
  selectedScene,
  selectedEpisode,
  activeWorkspace,
  onChangeWorkspace,
  onSelectScene,
  onApproveOutline,
  onGenerate,
  onApproveScene,
  onRejectScene,
  onRegenerateScene,
  onLockScene,
  onSaveStoryEdit,
  onSaveSceneEdit,
  currentMedia,
  currentKind = "video",
  latestJob,
  latestAudioCheckpoint,
  progressValue,
  prompt,
  setPrompt,
  assistantTarget,
  setAssistantTarget,
  onSendAssistant,
  messages,
  referenceUrls,
  onReferenceUpload,
  onReferenceRemove,
  sceneRefUploading,
  assistantMessage,
  storyDraft,
  sceneDraft,
  onApplyStoryDraft,
  onApplySceneDraft,
  assistantBusy = false,
}: Props) {
  const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(storyHistory[0]?.id || null);
  const ratio = story.workflow_state?.pipeline_config?.media?.ratio || story.workflow_state?.aspect_ratio || "9:16";
  const totalDuration = Math.max(1, scenes.reduce((sum, scene) => sum + durationForScene(scene), 0));
  const currentSceneIndex = selectedScene ? scenes.findIndex((scene) => scene.id === selectedScene.id) : -1;
  const playheadPercent =
    currentSceneIndex < 0
      ? 0
      : (scenes.slice(0, currentSceneIndex).reduce((sum, scene) => sum + durationForScene(scene), 0) / totalDuration) * 100;
  const completedScenes = scenes.filter((scene) => scene.status === "completed" || scene.status === "ready").length;
  const approvedScenes = scenes.filter((scene) => scene.approval_status === "approved").length;
  const recentActivity = useMemo(
    () => [...sceneHistory, ...storyHistory].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).slice(0, 12),
    [sceneHistory, storyHistory],
  );

  const workspaceView = (() => {
    if (activeWorkspace === "outline") return <StoryOutlineView story={story} />;
    if (activeWorkspace === "script") return <ScriptView story={story} />;
    if (activeWorkspace === "history") return <HistoryView entries={storyHistory} selectedId={selectedHistoryId} onSelect={setSelectedHistoryId} />;
    if (activeWorkspace === "cast") {
      return (
        <div className="grid gap-4 lg:grid-cols-2">
          {characters.map((character) => (
            <div key={character.id} className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[15px] font-medium text-white">{character.name}</div>
                  <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-zinc-500">{character.role}</div>
                </div>
                <Badge className={statusTone(character.approval_status)}>{character.approval_status}</Badge>
              </div>
              <div className="mt-3 text-[12px] leading-6 text-zinc-400">{character.description || character.appearance || "No description provided."}</div>
            </div>
          ))}
          {!characters.length && <div className="rounded-[24px] border border-dashed border-zinc-800 bg-zinc-950 p-5 text-[12px] text-zinc-500">No characters yet.</div>}
        </div>
      );
    }
    if (activeWorkspace === "references") {
      return (
        <div className="grid gap-4">
          <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
            <div className="flex items-center justify-between gap-3">
              <SectionLabel>Scene references</SectionLabel>
              <label className="cursor-pointer">
                <span className="inline-flex h-8 items-center gap-2 rounded-xl border border-zinc-800 bg-black px-3 text-[11px] text-zinc-200 hover:bg-zinc-900">
                  <ImagePlus className="h-3.5 w-3.5" />
                  Upload
                </span>
                <input type="file" accept="image/*" multiple className="hidden" disabled={sceneRefUploading} onChange={(e) => onReferenceUpload(e.target.files)} />
              </label>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
              {referenceUrls.map((url) => (
                <div key={url} className="group relative overflow-hidden rounded-2xl border border-zinc-800 bg-black">
                  <img src={url} alt="reference" className="h-28 w-full object-cover" />
                  <button type="button" onClick={() => onReferenceRemove(url)} className="absolute right-2 top-2 rounded-lg bg-black/80 px-2 py-1 text-[10px] text-white opacity-0 transition group-hover:opacity-100">
                    Remove
                  </button>
                </div>
              ))}
              {!referenceUrls.length && <div className="col-span-full rounded-2xl border border-dashed border-zinc-800 bg-black p-5 text-[12px] text-zinc-500">No uploaded scene references.</div>}
            </div>
          </div>
        </div>
      );
    }
    if (activeWorkspace === "runs") {
      return (
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
            <SectionLabel>Run status</SectionLabel>
            <div className="mt-3 flex items-center justify-between gap-4">
              <div>
                <div className="text-[16px] font-medium text-white">{latestJob?.current_step || story.status}</div>
                <div className="mt-1 text-[12px] text-zinc-500">{latestJob?.job_type || workflowLabel(story.workflow_type)}</div>
              </div>
              <Badge className={statusTone(latestJob?.status || story.status)}>{latestJob?.status || story.status}</Badge>
            </div>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-zinc-900">
              <div className="h-full rounded-full bg-sky-400" style={{ width: `${progressValue}%` }} />
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <MetricCard label="Scenes rendered" value={`${completedScenes}/${scenes.length || 0}`} tone="highlight" />
              <MetricCard label="Approved scenes" value={`${approvedScenes}/${scenes.length || 0}`} />
              <MetricCard label="Last update" value={timeAgo(latestJob?.completed_at || latestJob?.started_at || story.updated_at)} />
            </div>
          </div>
          <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-5">
            <SectionLabel>Checkpoint audio</SectionLabel>
            {latestAudioCheckpoint?.narration_audio_url ? (
              <div className="mt-4 space-y-3">
                <audio controls className="w-full" src={latestAudioCheckpoint.narration_audio_url} />
                <div className="text-[12px] leading-6 text-zinc-400">{latestAudioCheckpoint.narration_text || "Narration ready."}</div>
              </div>
            ) : (
              <div className="mt-4 rounded-2xl border border-dashed border-zinc-800 bg-black p-4 text-[12px] text-zinc-500">Narration is not ready yet.</div>
            )}
          </div>
        </div>
      );
    }

    return (
      <div className="grid min-h-0 gap-4">
        <div className="relative min-h-[420px] overflow-hidden rounded-[28px] border border-zinc-800 bg-black">
          {currentMedia ? (
            currentKind === "image" ? (
              <img src={currentMedia} alt={selectedScene?.title || story.title} className="h-full w-full object-cover" />
            ) : (
              <video src={currentMedia} className="h-full w-full object-cover" controls playsInline preload="metadata" />
            )
          ) : (
            <div className="flex h-full items-center justify-center bg-[radial-gradient(circle_at_center,rgba(40,40,48,0.7),rgba(0,0,0,1))]">
              <div className="text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-zinc-900 text-zinc-300">
                  <Play className="h-6 w-6" />
                </div>
                <div className="mt-4 text-[14px] font-medium text-white">No rendered media yet</div>
                <div className="mt-2 text-[12px] text-zinc-500">Approve the outline and start generation to populate the canvas.</div>
              </div>
            </div>
          )}
          <div className="absolute inset-x-0 top-0 flex items-start justify-between p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={statusTone(selectedScene?.approval_status || selectedScene?.status || story.status)}>
                {selectedScene?.approval_status || selectedScene?.status || story.status}
              </Badge>
              <Badge className="border-zinc-800 bg-black/80 text-zinc-300">{selectedEpisode ? `Episode ${selectedEpisode.episode_number}` : "Story preview"}</Badge>
              <Badge className="border-zinc-800 bg-black/80 text-zinc-300">{ratio}</Badge>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="h-8 border-zinc-800 bg-black/80 text-[11px] text-zinc-200 hover:bg-zinc-900">
                  Scene actions
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48 border-zinc-800 bg-black text-zinc-100">
                <DropdownMenuItem onClick={() => onApproveOutline()}>Approve outline</DropdownMenuItem>
                <DropdownMenuItem onClick={() => onGenerate()}>Start generation</DropdownMenuItem>
                {selectedScene ? (
                  <>
                    <DropdownMenuItem onClick={() => onApproveScene(selectedScene.id)}>Approve selected scene</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onRegenerateScene(selectedScene.id)}>Regenerate selected scene</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onLockScene(selectedScene.id)}>Lock selected scene</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onRejectScene(selectedScene.id)} className="text-red-300">
                      Reject selected scene
                    </DropdownMenuItem>
                  </>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black via-black/80 to-transparent p-4">
            <SceneStrip scenes={scenes} selectedScene={selectedScene} onSelectScene={onSelectScene} />
          </div>
        </div>

        <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 text-zinc-400">
              <Clock3 className="h-4 w-4" />
              <div className="text-[11px]">Timeline</div>
            </div>
            <div className="text-[11px] text-zinc-500">{selectedScene ? `${selectedScene.title || `Scene ${selectedScene.scene_number}`}` : "No scene selected"}</div>
          </div>
          <div className="mt-4">
            <div className="mb-2 flex justify-between text-[10px] text-zinc-500">
              <span>0s</span>
              <span>{Math.round(totalDuration)}s</span>
            </div>
            <div className="relative flex h-12 gap-1 rounded-2xl border border-zinc-900 bg-black p-1">
              <div className="absolute bottom-1 top-1 w-0.5 bg-sky-400" style={{ left: `${playheadPercent}%` }} />
              {scenes.map((scene) => {
                const media = sceneMedia(scene);
                const width = `${Math.max(10, (durationForScene(scene) / totalDuration) * 100)}%`;
                const active = selectedScene?.id === scene.id;
                return (
                  <button
                    key={scene.id}
                    type="button"
                    onClick={() => onSelectScene(scene.id)}
                    className={`relative h-full overflow-hidden rounded-xl border ${active ? "border-sky-400" : "border-zinc-800"} bg-zinc-900`}
                    style={{ width }}
                  >
                    {media ? <img src={media} alt={scene.title || `Scene ${scene.scene_number}`} className="h-full w-full object-cover" /> : null}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  })();

  return (
    <div className="h-screen bg-black text-white">
      <div className="grid h-full min-h-0 grid-cols-1 xl:grid-cols-[240px_minmax(0,1fr)_380px]">
        <aside className="hidden min-h-0 border-r border-zinc-900 bg-black xl:flex xl:flex-col">
          <div className="flex items-center gap-3 border-b border-zinc-900 px-5 py-5">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-zinc-800 bg-zinc-950 text-[13px] font-semibold">D</div>
            <div className="min-w-0">
              <div className="truncate text-[14px] font-medium text-white">Dysentry</div>
              <div className="text-[11px] text-zinc-500">Production console</div>
            </div>
          </div>
          <div className="flex min-h-0 flex-1 flex-col px-4 py-4">
            <div className="space-y-2">
              <SidebarButton icon={FolderKanban} label="Canvas" active={activeWorkspace === "canvas"} onClick={() => onChangeWorkspace("canvas")} />
              <SidebarButton icon={BookOpen} label="Outline" active={activeWorkspace === "outline"} onClick={() => onChangeWorkspace("outline")} />
              <SidebarButton icon={ScrollText} label="Script" active={activeWorkspace === "script"} onClick={() => onChangeWorkspace("script")} />
              <SidebarButton icon={Users2} label="Cast" active={activeWorkspace === "cast"} onClick={() => onChangeWorkspace("cast")} />
              <SidebarButton icon={ImagePlus} label="References" active={activeWorkspace === "references"} onClick={() => onChangeWorkspace("references")} />
              <SidebarButton icon={Clapperboard} label="Runs" active={activeWorkspace === "runs"} onClick={() => onChangeWorkspace("runs")} />
              <SidebarButton icon={History} label="History" active={activeWorkspace === "history"} onClick={() => onChangeWorkspace("history")} />
            </div>
            <div className="mt-6 grid gap-3">
              <MetricCard label="Scenes" value={String(scenes.length)} />
              <MetricCard label="Episodes" value={String(episodes.length)} />
              <MetricCard label="Ready" value={`${completedScenes}`} tone="highlight" />
            </div>
          </div>
        </aside>

        <main className="flex min-h-0 flex-col bg-black">
          <header className="flex h-16 flex-none items-center justify-between border-b border-zinc-900 px-4 md:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <Link href="/dashboard">
                <button type="button" className="rounded-xl border border-zinc-900 bg-zinc-950 p-2 text-zinc-300 transition hover:bg-zinc-900 hover:text-white">
                  <ArrowLeft className="h-4 w-4" />
                </button>
              </Link>
              <div className="min-w-0">
                <div className="truncate text-[15px] font-medium text-white">{story.title}</div>
                <div className="mt-0.5 text-[11px] text-zinc-500">{workflowLabel(story.workflow_type)}</div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={statusTone(story.status)}>{story.status}</Badge>
              <Badge className="border-zinc-800 bg-zinc-950 text-zinc-300">{progressValue}%</Badge>
              <StoryEditorSheet story={story} onSave={onSaveStoryEdit} />
              <SceneEditorSheet scene={selectedScene} onSave={onSaveSceneEdit} />
            </div>
          </header>

          <div className="flex flex-none items-center justify-between gap-4 border-b border-zinc-900 px-4 py-3 md:px-6">
            <div className="flex items-center gap-2 overflow-x-auto">
              <Button variant={activeWorkspace === "canvas" ? "lime" : "outline"} size="sm" className="h-8 text-[11px]" onClick={() => onChangeWorkspace("canvas")}>
                Canvas
              </Button>
              <Button variant={activeWorkspace === "outline" ? "lime" : "outline"} size="sm" className="h-8 text-[11px]" onClick={() => onChangeWorkspace("outline")}>
                Outline
              </Button>
              <Button variant={activeWorkspace === "script" ? "lime" : "outline"} size="sm" className="h-8 text-[11px]" onClick={() => onChangeWorkspace("script")}>
                Script
              </Button>
              <Button variant={activeWorkspace === "history" ? "lime" : "outline"} size="sm" className="h-8 text-[11px]" onClick={() => onChangeWorkspace("history")}>
                History
              </Button>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="h-8 border-zinc-800 bg-zinc-950 text-[11px] text-zinc-200 hover:bg-zinc-900" onClick={onApproveOutline}>
                <Check className="h-3.5 w-3.5" />
                Approve outline
              </Button>
              <Button variant="lime" size="sm" className="h-8 text-[11px]" onClick={onGenerate}>
                <WandSparkles className="h-3.5 w-3.5" />
                Generate
              </Button>
            </div>
          </div>

          <ScrollArea className="min-h-0 flex-1">
            <div className="p-4 md:p-6">{workspaceView}</div>
          </ScrollArea>
        </main>

        <aside className="flex min-h-0 flex-col border-l border-zinc-900 bg-black">
          <div className="flex h-16 flex-none items-center justify-between border-b border-zinc-900 px-5">
            <div>
              <div className="text-[13px] font-medium text-white">AI director</div>
              <div className="mt-0.5 text-[11px] text-zinc-500">Edit storyline, scene text, and generation intent</div>
            </div>
            <Badge className="border-zinc-800 bg-zinc-950 text-zinc-300">{assistantTarget}</Badge>
          </div>

          <div className="flex min-h-0 flex-1 flex-col">
            <div className="grid gap-3 border-b border-zinc-900 p-5">
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setAssistantTarget("story")}
                  className={`rounded-2xl border px-3 py-2 text-[11px] font-medium transition ${assistantTarget === "story" ? "border-zinc-700 bg-zinc-900 text-white" : "border-zinc-900 bg-zinc-950 text-zinc-400 hover:text-zinc-200"}`}
                >
                  Story
                </button>
                <button
                  type="button"
                  onClick={() => setAssistantTarget("scene")}
                  className={`rounded-2xl border px-3 py-2 text-[11px] font-medium transition ${assistantTarget === "scene" ? "border-zinc-700 bg-zinc-900 text-white" : "border-zinc-900 bg-zinc-950 text-zinc-400 hover:text-zinc-200"}`}
                >
                  Selected scene
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {[
                  "Tighten the storyline",
                  "Make this scene darker",
                  "Shorten narration",
                  "Raise visual intensity",
                ].map((chip) => (
                  <button
                    key={chip}
                    type="button"
                    onClick={() => setPrompt(chip)}
                    className="rounded-full border border-zinc-800 bg-zinc-950 px-3 py-1.5 text-[10px] text-zinc-300 transition hover:bg-zinc-900"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </div>

            <ScrollArea className="min-h-0 flex-1">
              <div className="space-y-4 p-5">
                <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-4">
                  <SectionLabel>Context</SectionLabel>
                  <div className="mt-3 space-y-2 text-[12px] leading-6 text-zinc-300">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-zinc-500">Story</span>
                      <span className="truncate text-right text-white">{story.title}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-zinc-500">Scene</span>
                      <span className="truncate text-right text-white">{selectedScene?.title || "None selected"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-zinc-500">Run step</span>
                      <span className="truncate text-right text-white">{latestJob?.current_step || story.status}</span>
                    </div>
                  </div>
                </div>

                <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <SectionLabel>Conversation</SectionLabel>
                    <Sparkles className="h-4 w-4 text-zinc-500" />
                  </div>
                  <div className="mt-3 space-y-2">
                    {messages.slice(-8).map((message, index) => (
                      <div
                        key={`${message.role}-${index}`}
                        className={`rounded-2xl px-3 py-2 text-[11px] leading-6 ${
                          message.role === "assistant" ? "border border-zinc-800 bg-black text-zinc-300" : "border border-sky-500/20 bg-sky-500/8 text-sky-100"
                        }`}
                      >
                        {message.text}
                      </div>
                    ))}
                  </div>
                </div>

                {(assistantMessage || storyDraft || sceneDraft) && (
                  <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <SectionLabel>Draft revision</SectionLabel>
                      <ChevronRight className="h-4 w-4 text-zinc-500" />
                    </div>
                    {assistantMessage ? <div className="mt-3 text-[12px] leading-6 text-zinc-300">{assistantMessage}</div> : null}
                    {storyDraft && Object.keys(storyDraft).length ? (
                      <div className="mt-3 space-y-2">
                        <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">Story patch</div>
                        <JsonPreview value={storyDraft} />
                        <Button variant="lime" size="sm" className="w-full text-[11px]" onClick={onApplyStoryDraft}>
                          Apply story draft
                        </Button>
                      </div>
                    ) : null}
                    {sceneDraft && Object.keys(sceneDraft).length ? (
                      <div className="mt-3 space-y-2">
                        <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">Scene patch</div>
                        <JsonPreview value={sceneDraft} />
                        <Button variant="lime" size="sm" className="w-full text-[11px]" onClick={onApplySceneDraft}>
                          Apply scene draft
                        </Button>
                      </div>
                    ) : null}
                  </div>
                )}

                <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <SectionLabel>Scene actions</SectionLabel>
                    <Badge className={statusTone(selectedScene?.approval_status || selectedScene?.status)}>{selectedScene?.approval_status || selectedScene?.status || "none"}</Badge>
                  </div>
                  <div className="mt-3 grid gap-2">
                    <Button size="sm" variant="outline" className="justify-start border-zinc-800 bg-black text-[11px] text-zinc-200 hover:bg-zinc-900" disabled={!selectedScene} onClick={() => selectedScene && onApproveScene(selectedScene.id)}>
                      <Check className="h-3.5 w-3.5" />
                      Approve scene
                    </Button>
                    <Button size="sm" variant="outline" className="justify-start border-zinc-800 bg-black text-[11px] text-zinc-200 hover:bg-zinc-900" disabled={!selectedScene} onClick={() => selectedScene && onRegenerateScene(selectedScene.id)}>
                      <WandSparkles className="h-3.5 w-3.5" />
                      Regenerate scene
                    </Button>
                    <Button size="sm" variant="outline" className="justify-start border-zinc-800 bg-black text-[11px] text-zinc-200 hover:bg-zinc-900" disabled={!selectedScene} onClick={() => selectedScene && onLockScene(selectedScene.id)}>
                      <Lock className="h-3.5 w-3.5" />
                      Lock scene
                    </Button>
                    <Button size="sm" variant="outline" className="justify-start border-red-500/20 bg-red-500/8 text-[11px] text-red-100 hover:bg-red-500/12" disabled={!selectedScene} onClick={() => selectedScene && onRejectScene(selectedScene.id)}>
                      <XCircle className="h-3.5 w-3.5" />
                      Reject scene
                    </Button>
                  </div>
                </div>

                <div className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <SectionLabel>Audio and activity</SectionLabel>
                    <AudioLines className="h-4 w-4 text-zinc-500" />
                  </div>
                  {latestAudioCheckpoint?.narration_audio_url ? <audio controls className="mt-3 w-full" src={latestAudioCheckpoint.narration_audio_url} /> : null}
                  <div className="mt-4 space-y-2">
                    {recentActivity.slice(0, 6).map((entry) => (
                      <div key={entry.id} className="rounded-2xl border border-zinc-800 bg-black p-3">
                        <div className="flex items-center justify-between gap-3">
                          <div className="truncate text-[11px] text-white">{entry.event_type}</div>
                          <div className="text-[10px] text-zinc-500">v{entry.revision}</div>
                        </div>
                        <div className="mt-1 text-[10px] text-zinc-500">{formatDateTime(entry.created_at)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ScrollArea>

            <div className="border-t border-zinc-900 p-5">
              <Textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={assistantTarget === "story" ? "Rewrite the storyline, tighten the synopsis, or change pacing." : "Rewrite the selected scene text, narration, or visual prompt."}
                className="min-h-[132px] resize-none border-zinc-800 bg-zinc-950 text-[12px] text-zinc-100 placeholder:text-zinc-500"
              />
              <div className="mt-3 flex items-center justify-between gap-3">
                <label className="cursor-pointer rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-[11px] text-zinc-200 hover:bg-zinc-900">
                  <span className="inline-flex items-center gap-2">
                    <ImagePlus className="h-3.5 w-3.5" />
                    Upload ref
                  </span>
                  <input type="file" accept="image/*" multiple className="hidden" disabled={sceneRefUploading} onChange={(e) => onReferenceUpload(e.target.files)} />
                </label>
                <Button variant="lime" size="sm" className="text-[11px]" onClick={onSendAssistant} disabled={assistantBusy || !prompt.trim()}>
                  <Send className="h-3.5 w-3.5" />
                  {assistantBusy ? "Working" : "Send"}
                </Button>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
