import db from "@/api/base44Client";

function apiBaseUrl() {
  const raw = import.meta.env.VITE_API_BASE_URL || "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = db.auth.getToken?.();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...options,
    headers,
  });

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const error = new Error(data?.detail || data || `Request failed with status ${response.status}`);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

function frontendSceneStatus(scene) {
  if (scene.status === "running") return "regenerating";
  if (scene.approval_status === "approved") return "approved";
  if (scene.approval_status === "pending_review") return "pending_review";
  if (scene.approval_status === "rejected") return "draft";
  return "draft";
}

function mediaKindToType(kind) {
  if (kind === "image") return "narrated_image";
  if (kind === "voice") return "voice";
  return "video";
}

function typeToMediaKind(type) {
  if (type === "narrated_image") return "image";
  if (type === "voice") return "voice";
  return "video";
}

export function mapStoryToSeries(story) {
  return {
    id: story.id,
    title: story.title,
    description: story.episode_plan?.synopsis || "",
    status: story.status,
    workflow_type: story.workflow_type,
    style_memory:
      story.pipeline_config?.editor?.style_memory ||
      story.workflow_state?.style_memory ||
      "",
    raw: story,
  };
}

export function mapEpisodeToEditorEpisode(episode) {
  return {
    id: episode.id,
    series_id: episode.story_id,
    episode_number: episode.episode_number,
    title: episode.title,
    summary: episode.summary || "",
    status: episode.status,
    assembled_video_url: episode.assembled_video_url || null,
    raw: episode,
  };
}

export function mapSceneToEditorScene(scene) {
  const script = scene.description || scene.prompt || "";
  return {
    id: scene.id,
    episode_id: scene.episode_id,
    order: scene.scene_number,
    scene_number: scene.scene_number,
    title: scene.title || `Scene ${scene.scene_number}`,
    type: mediaKindToType(scene.media_kind),
    media_kind: scene.media_kind || "video",
    script,
    prompt: scene.prompt || script,
    visual_prompt: scene.visual_prompt || scene.prompt || "",
    narration: scene.narration || "",
    checkpoint_notes: "",
    status: frontendSceneStatus(scene),
    media_url: scene.media_url || scene.clip_url || scene.image_url || null,
    clip_url: scene.clip_url || null,
    image_url: scene.image_url || null,
    approval_status: scene.approval_status || "pending",
    locked: !!scene.locked,
    raw: scene,
  };
}

export function mapCharacterToEditorCharacter(character) {
  return {
    id: character.id,
    series_id: character.story_id,
    name: character.name,
    role: character.role,
    description: character.description || "",
    appearance: character.appearance || "",
    personality: character.personality || "",
    voice: character.voice_ref_url || "",
    ref_image_urls: character.ref_image_urls || [],
    raw: character,
  };
}

export async function getEditorStory(storyId) {
  const story = await request(`/pipeline/stories/${storyId}`);
  return mapStoryToSeries(story);
}

export async function listStories() {
  const stories = await request("/pipeline/stories");
  return stories.map(mapStoryToSeries);
}

export async function createStory(story) {
  const payload = {
    title: story.title,
    prompt: story.prompt || story.description || "",
    genre: story.genre || "action",
    style: story.style || "anime",
    frame_ratio: story.frame_ratio || "16:9",
    requested_video_ratio: story.requested_video_ratio || story.frame_ratio || "16:9",
    num_episodes: story.num_episodes || 1,
    num_scenes: story.num_scenes || 5,
    workflow_type: story.workflow_type || "creator_series",
    requested_media_kind: story.requested_media_kind || "auto",
  };
  const created = await request("/pipeline/stories", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapStoryToSeries(created);
}

export async function listEditorEpisodes(storyId) {
  const episodes = await request(`/pipeline/episodes/story/${storyId}`);
  return episodes.map(mapEpisodeToEditorEpisode);
}

export async function listStoryRuns(storyId) {
  return request(`/pipeline/runs/story/${storyId}`);
}

export async function listSchedules() {
  return request("/pipeline/schedules");
}

export async function createSchedule(payload) {
  return request("/pipeline/schedules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deleteSchedule(scheduleId) {
  return request(`/pipeline/schedules/${scheduleId}`, {
    method: "DELETE",
  });
}

export async function listSocialAccounts() {
  return request("/pipeline/social/accounts");
}

export async function startSocialConnect(platform) {
  return request(`/pipeline/social/${platform}/connect`, {
    method: "POST",
  });
}

export async function disconnectSocialAccount(accountId) {
  return request(`/pipeline/social/accounts/${accountId}`, {
    method: "DELETE",
  });
}

export async function listEditorScenes(storyId, episodeId) {
  const episodes = await request(`/pipeline/episodes/story/${storyId}`);
  const selected = episodes.find((episode) => episode.id === episodeId);
  return (selected?.scenes || []).map(mapSceneToEditorScene);
}

export async function listEditorCharacters(storyId) {
  const characters = await request(`/pipeline/characters/story/${storyId}`);
  return characters.map(mapCharacterToEditorCharacter);
}

export async function saveStyleMemory(storyId, story, styleMemory) {
  const currentConfig = story?.raw?.pipeline_config || {};
  const nextConfig = {
    ...currentConfig,
    editor: {
      ...(currentConfig.editor || {}),
      style_memory: styleMemory,
    },
  };
  const updated = await request(`/pipeline/stories/${storyId}/pipeline-config`, {
    method: "PUT",
    body: JSON.stringify({ pipeline_config: nextConfig }),
  });
  return mapStoryToSeries(updated);
}

export async function updateEditorScene(sceneId, scene) {
  const payload = {
    title: scene.title,
    prompt: scene.prompt || scene.script || "",
    description: scene.script || "",
    visual_prompt: scene.visual_prompt || scene.prompt || scene.script || "",
    narration: scene.narration || "",
    media_kind: typeToMediaKind(scene.type),
  };
  const updated = await request(`/pipeline/scenes/${sceneId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  return mapSceneToEditorScene(updated);
}

export async function createEditorScene(storyId, episodeId, scene) {
  const payload = {
    episode_id: episodeId,
    scene_number: scene.order,
    prompt: scene.prompt || scene.script || scene.title || `Scene ${scene.order}`,
    title: scene.title,
    description: scene.script || "",
    visual_prompt: scene.visual_prompt || scene.prompt || scene.script || "",
    narration: scene.narration || "",
    media_kind: typeToMediaKind(scene.type),
    generate: false,
  };
  const created = await request(`/pipeline/scenes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return mapSceneToEditorScene(created);
}

export async function regenerateEditorScene(sceneId) {
  return request(`/pipeline/scenes/${sceneId}/regenerate`, {
    method: "POST",
  });
}

export async function approveEditorScene(sceneId) {
  const updated = await request(`/pipeline/scenes/${sceneId}/approve`, {
    method: "PUT",
  });
  return mapSceneToEditorScene(updated);
}

export async function requestEditorSceneReview(sceneId) {
  const updated = await request(`/pipeline/scenes/${sceneId}`, {
    method: "PUT",
    body: JSON.stringify({ approval_status: "pending_review" }),
  });
  return mapSceneToEditorScene(updated);
}

export async function assistantForScene(storyId, sceneId, instruction) {
  return request(`/pipeline/stories/${storyId}/assistant`, {
    method: "POST",
    body: JSON.stringify({
      instruction,
      target: "scene",
      scene_id: sceneId,
    }),
  });
}

// Scene operations
export async function deleteScene(sceneId) {
  return request(`/pipeline/scenes/${sceneId}`, {
    method: "DELETE",
  });
}

export async function lockScene(sceneId) {
  return request(`/pipeline/scenes/${sceneId}/lock`, {
    method: "PUT",
  });
}

export async function unlockScene(sceneId) {
  return request(`/pipeline/scenes/${sceneId}/unlock`, {
    method: "PUT",
  });
}

export async function rejectScene(sceneId) {
  return request(`/pipeline/scenes/${sceneId}/reject`, {
    method: "PUT",
  });
}

export async function getSceneJobStatus(jobId) {
  return request(`/pipeline/runs/${jobId}`);
}

// Episode operations
export async function createEpisode(storyId, episodeData) {
  return request(`/pipeline/episodes`, {
    method: "POST",
    body: JSON.stringify({
      story_id: storyId,
      ...episodeData,
    }),
  });
}

// Character operations
export async function createCharacter(storyId, character) {
  return request(`/pipeline/characters`, {
    method: "POST",
    body: JSON.stringify({
      story_id: storyId,
      name: character.name,
      role: character.role || "supporting",
      description: character.description || "",
      appearance: character.appearance || "",
      personality: character.personality || "",
    }),
  });
}

export async function updateCharacter(characterId, character) {
  return request(`/pipeline/characters/${characterId}`, {
    method: "PUT",
    body: JSON.stringify(character),
  });
}

export async function deleteCharacter(characterId) {
  return request(`/pipeline/characters/${characterId}`, {
    method: "DELETE",
  });
}

// Export/Render operations
export async function exportEpisode(episodeId, platform) {
  return request(`/pipeline/episodes/${episodeId}/export`, {
    method: "POST",
    body: JSON.stringify({ platform }),
  });
}
