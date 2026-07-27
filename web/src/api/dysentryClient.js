import db from "@/api/base44Client";
import {request} from "@/api/base44Client"
// Use the centralized request from base44Client
// Auth errors (401/403) are handled by base44Client


function hasSceneMedia(scene) {
  return !!(scene.media_url || scene.clip_url || scene.image_url);
}

/**
 * Map backend scene fields to a single editor workflow status.
 * draft → regenerating → ready → pending_review → approved
 * rejected can appear after a review pass.
 */
function frontendSceneStatus(scene) {
  if (scene.status === "running") return "regenerating";
  if (scene.approval_status === "approved") return "approved";
  if (scene.approval_status === "pending_review") return "pending_review";
  if (scene.approval_status === "rejected") return "rejected";
  if (hasSceneMedia(scene) && (scene.status === "completed" || scene.status === "done")) {
    return "ready";
  }
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
  const mediaUrl = scene.media_url || scene.clip_url || scene.image_url || null;
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
    mood: scene.mood || "",
    location: scene.location || "",
    checkpoint_notes: scene.checkpoint_notes || scene.reviewer_notes || "",
    status: frontendSceneStatus(scene),
    backend_status: scene.status || "draft",
    media_url: mediaUrl,
    clip_url: scene.clip_url || null,
    image_url: scene.image_url || null,
    duration: scene.duration ?? null,
    regeneration_count: scene.regeneration_count || 0,
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

export async function getDashboardBatch(storyIds) {
  // Batch endpoint to avoid N+1 queries
  const ids = storyIds.join(",");
  const data = await request(`/pipeline/stories/batch/dashboard?ids=${ids}`);
  return {
    stories: data.stories.map(mapStoryToSeries),
    episodes: data.episodes.map(mapEpisodeToEditorEpisode),
    runs: data.runs,
  };
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

export async function getEditorEpisode(episodeId) {
  const episode = await request(`/pipeline/episodes/${episodeId}`);
  return mapEpisodeToEditorEpisode(episode);
}

export async function listEditorScenes(_storyId, episodeId) {
  // Prefer single-episode fetch (includes scenes) over reloading the whole story.
  const episode = await request(`/pipeline/episodes/${episodeId}`);
  return (episode?.scenes || []).map(mapSceneToEditorScene);
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
    prompt: scene.prompt || scene.visual_prompt || scene.script || "",
    description: scene.script || "",
    visual_prompt: scene.visual_prompt || scene.prompt || scene.script || "",
    narration: scene.narration || "",
    mood: scene.mood || "",
    location: scene.location || "",
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
    prompt: scene.prompt || scene.visual_prompt || scene.script || scene.title || `Scene ${scene.order}`,
    title: scene.title,
    description: scene.script || "",
    visual_prompt: scene.visual_prompt || scene.prompt || scene.script || "",
    narration: scene.narration || "",
    mood: scene.mood || "",
    location: scene.location || "",
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
  // Returns GenerationJobResponse: { id, status, progress, current_step, ... }
  return request(`/pipeline/scenes/${sceneId}/regenerate`, {
    method: "POST",
  });
}

export async function getEditorScene(sceneId) {
  const scene = await request(`/pipeline/scenes/${sceneId}`);
  return mapSceneToEditorScene(scene);
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
  const updated = await request(`/pipeline/scenes/${sceneId}/lock`, {
    method: "PUT",
  });
  return mapSceneToEditorScene(updated);
}

export async function unlockScene(sceneId) {
  const updated = await request(`/pipeline/scenes/${sceneId}/unlock`, {
    method: "PUT",
  });
  return mapSceneToEditorScene(updated);
}

export async function rejectScene(sceneId) {
  const updated = await request(`/pipeline/scenes/${sceneId}/reject`, {
    method: "PUT",
  });
  return mapSceneToEditorScene(updated);
}

export async function getSceneJobStatus(jobId) {
  // Generation jobs live under /pipeline/jobs, not pipeline runs.
  return request(`/pipeline/jobs/${jobId}`);
}

export async function listSceneJobs(sceneId) {
  return request(`/pipeline/jobs/entity/scene/${sceneId}`);
}

export async function getSceneHistory(sceneId) {
  return request(`/pipeline/scenes/${sceneId}/history`);
}

/** Poll a generation job until it finishes or the timeout elapses. */
export async function pollSceneJob(jobId, { intervalMs = 2000, timeoutMs = 180000, onTick } = {}) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const job = await getSceneJobStatus(jobId);
    onTick?.(job);
    const status = (job.status || "").toLowerCase();
    if (["completed", "failed", "cancelled", "canceled"].includes(status)) {
      return job;
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new Error("Timed out waiting for scene generation");
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

export async function bulkApproveEpisode(episodeId) {
  return request(`/pipeline/episodes/${episodeId}/bulk-approve`, {
    method: "POST",
  });
}

export async function assembleEpisode(episodeId) {
  return request(`/pipeline/episodes/${episodeId}/assemble`, {
    method: "POST",
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

// Story generation operations
export async function approveStoryOutline(storyId) {
  return request(`/pipeline/stories/${storyId}/approve-outline`, {
    method: "PUT",
  });
}

export async function startStoryGeneration(storyId) {
  return request(`/pipeline/stories/${storyId}/generate`, {
    method: "POST",
  });
}

export async function cancelStoryJob(storyId) {
  // Get the active job for this story and cancel it
  const jobs = await request(`/pipeline/jobs/entity/story/${storyId}`);
  const activeJob = jobs.find(
    (j) => j.status === "running" || j.status === "pending"
  );
  if (activeJob) {
    return request(`/pipeline/jobs/${activeJob.id}/cancel`, {
      method: "POST",
    });
  }
  return { message: "No active job found" };
}

export async function getStoryCheckpoints(storyId) {
  return request(`/pipeline/stories/${storyId}/checkpoints`);
}

export async function approveCheckpoint(storyId, checkpointId) {
  return request(`/pipeline/stories/${storyId}/checkpoints/${checkpointId}/approve`, {
    method: "PUT",
  });
}

export async function regenerateCheckpointAudio(storyId, checkpointId, options = {}) {
  return request(`/pipeline/stories/${storyId}/checkpoints/${checkpointId}/audio/regenerate`, {
    method: "POST",
    body: JSON.stringify(options),
  });
}

export async function getNarrationVoices() {
  return request("/pipeline/narration/voices");
}

export async function getStoryHistory(storyId) {
  return request(`/pipeline/stories/${storyId}/history`);
}

export async function getStoryRuns(storyId) {
  return request(`/pipeline/runs/story/${storyId}`);
}

export async function getJobStatus(jobId) {
  return request(`/pipeline/jobs/${jobId}`);
}

export async function cancelJob(jobId) {
  return request(`/pipeline/jobs/${jobId}/cancel`, {
    method: "POST",
  });
}

export async function retryJob(jobId) {
  return request(`/pipeline/jobs/${jobId}/retry`, {
    method: "POST",
  });
}
