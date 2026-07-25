import type { GalleryItem } from "@/lib/api";

export const fallbackGallery: GalleryItem[] = [
  {
    id: "demo-episode",
    kind: "episode",
    media_kind: "video",
    story_id: "demo",
    story_title: "Signal City",
    episode_id: "demo-episode",
    episode_number: 1,
    title: "Midnight relay",
    summary: "A serialized AI short assembled from scenes, narration, and model-routed video.",
    media_url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    duration: 8,
    created_at: new Date().toISOString(),
  },
  {
    id: "demo-style-ref",
    kind: "scene",
    media_kind: "image",
    story_id: "demo",
    story_title: "Archive Runner",
    episode_id: "demo-episode",
    episode_number: 1,
    scene_id: "demo-scene-1",
    scene_number: 1,
    title: "Reference pass",
    summary: "Character and style references guide each scene.",
    media_url: "https://images.unsplash.com/photo-1485846234645-a62644f84728?auto=format&fit=crop&w=1400&q=80",
    duration: 6,
    created_at: new Date().toISOString(),
  },
  {
    id: "demo-image-story",
    kind: "scene",
    media_kind: "image",
    story_id: "demo",
    story_title: "Moonroom Lessons",
    episode_id: "demo-episode",
    episode_number: 1,
    scene_id: "demo-scene-2",
    scene_number: 2,
    title: "Voice-led scene",
    summary: "Still images paced to narration for cheaper long-form storytelling.",
    media_url: "https://images.unsplash.com/photo-1535223289827-42f1e9919769?auto=format&fit=crop&w=1400&q=80",
    duration: 7,
    created_at: new Date().toISOString(),
  },
];

export const workflowCards = [
  {
    eyebrow: "01",
    title: "Plan",
    text: "The coordinator converts a user brief into outline, cast, scenes, references, and approval gates.",
  },
  {
    eyebrow: "02",
    title: "Render",
    text: "Each scene becomes a traced job with provider attempts, model routing, retry policy, and artifacts.",
  },
  {
    eyebrow: "03",
    title: "Approve",
    text: "Users review checkpoints before the next batch, regenerate weak scenes, or lock the current version.",
  },
  {
    eyebrow: "04",
    title: "Publish",
    text: "Completed episodes can be scheduled or pushed to connected channels after approval.",
  },
];

export const consoleStats = [
  ["3", "scene batch approvals"],
  ["5", "video model fallback slots"],
  ["24/7", "scheduled series runs"],
];

