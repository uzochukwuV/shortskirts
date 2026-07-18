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
