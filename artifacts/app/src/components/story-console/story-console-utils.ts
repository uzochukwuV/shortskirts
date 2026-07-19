import type { Story, GenerationJob, Episode, Scene, HistoryEntry, Character } from "@/lib/api";

export type WorkspaceTab = "design" | "outline" | "script" | "history";
export type InspectorMode = "scene" | "refs" | "cast" | "history";

export function statusTone(status?: string) {
  if (status === "completed" || status === "ready" || status === "approved") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "draft" || status === "pending_approval") return "border-amber-200 bg-amber-50 text-amber-700";
  if (status === "generating" || status === "checkpoint_review") return "border-[#083300] bg-[#96ff1a] text-[#083300]";
  if (status === "failed" || status === "rejected") return "border-red-200 bg-red-50 text-red-700";
  return "border-[#e6e6e7] bg-white text-[#71737a]";
}

export function formatShortDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function makeStoryText(story: Story) {
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

export type StoryConsoleData = {
  story: Story;
  episodes: Episode[];
  allScenes: Scene[];
  characters: Character[];
  storyHistory: HistoryEntry[];
  sceneHistory: HistoryEntry[];
  checkpoints: any[];
  latestStoryJob: GenerationJob | null;
};

export type WorkspaceActivityTone = "neutral" | "success" | "warning" | "danger" | "accent";

export type WorkspaceActivity = {
  title: string;
  detail: string;
  tone: WorkspaceActivityTone;
  timestamp?: string | null;
};

function minutesSince(value?: string | null) {
  if (!value) return null;
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return null;
  return Math.max(0, Math.round((Date.now() - dt.getTime()) / 60000));
}

function describeScene(scene: Scene) {
  const title = scene.title || `Scene ${scene.scene_number}`;
  const state = scene.status || scene.approval_status || "pending";
  return { title, state };
}

export function buildWorkspaceActivity(data: StoryConsoleData & { selectedScene?: Scene | null }): WorkspaceActivity[] {
  const items: WorkspaceActivity[] = [];
  const latestJob = data.latestStoryJob;
  const selectedScene = data.selectedScene ?? null;
  const generatingScenes = data.allScenes.filter((scene) => scene.status === "generating" || scene.status === "checkpoint_review");
  const completedScenes = data.allScenes.filter((scene) => scene.status === "completed" || scene.status === "ready");

  if (latestJob) {
    const age = minutesSince(latestJob.started_at || latestJob.created_at);
    const stale = latestJob.status === "running" && age !== null && age > 90;
    items.push({
      title: stale ? "Generation is stale" : `Job ${latestJob.status}`,
      detail: stale
        ? `The current job has been running for about ${age} minutes. Check the worker and provider state.`
        : latestJob.current_step || "Active generation step",
      tone: stale ? "danger" : latestJob.status === "completed" ? "success" : latestJob.status === "failed" ? "danger" : "accent",
      timestamp: latestJob.started_at || latestJob.created_at,
    });
  }

  if (selectedScene) {
    const scene = describeScene(selectedScene);
    items.push({
      title: scene.title,
      detail: `Scene ${selectedScene.scene_number} is ${scene.state}. ${selectedScene.narration ? "Narration attached." : "Narration pending."}`,
      tone: selectedScene.status === "completed" || selectedScene.status === "ready" ? "success" : selectedScene.status === "failed" ? "danger" : "neutral",
    });
  }

  if (generatingScenes.length > 0) {
    const scene = generatingScenes[0];
    items.push({
      title: `Generating scene ${scene.scene_number}`,
      detail: scene.title || scene.prompt || "Scene render in progress",
      tone: "accent",
    });
  }

  if (completedScenes.length > 0) {
    const scene = completedScenes[0];
    items.push({
      title: `Completed scene ${scene.scene_number}`,
      detail: scene.title || "Media rendered and stored",
      tone: "success",
    });
  }

  if (data.checkpoints?.length) {
    const pending = data.checkpoints.find((checkpoint: any) => checkpoint.status === "pending_review");
    if (pending) {
      items.push({
        title: `Checkpoint ${pending.batch_number} pending review`,
        detail: pending.narration_audio_url ? "Audio is ready for approval." : "Narration is still processing.",
        tone: pending.narration_audio_url ? "accent" : "warning",
        timestamp: pending.updated_at || pending.created_at,
      });
    }
  }

  for (const entry of data.storyHistory.slice(0, 3)) {
    items.push({
      title: entry.event_type,
      detail: `Revision ${entry.revision} • ${entry.generation_version}`,
      tone: "neutral",
      timestamp: entry.created_at,
    });
  }

  for (const entry of data.sceneHistory.slice(0, 3)) {
    items.push({
      title: `${entry.event_type} • scene`,
      detail: `Revision ${entry.revision} • ${entry.generation_version}`,
      tone: "neutral",
      timestamp: entry.created_at,
    });
  }

  return items.slice(0, 8);
}
