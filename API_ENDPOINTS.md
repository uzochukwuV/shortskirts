# StoryForge API Reference

This is the public-facing reference for the StoryForge pipeline APIs and the media model settings the app currently relies on.

Base path: `/pipeline`

Auth: protected routes require `Authorization: Bearer <token>`.

## Qwen / DashScope model note

The app uses Qwen image models for character and scene references.

- `qwen-image-plus`
  - Does not take a freeform `aspect_ratio` field.
  - Use the `size` parameter with one of the supported preset resolutions.
  - Supported presets: `1664*928` `16:9`, `1472*1104` `4:3`, `1328*1328` `1:1`, `1104*1472` `3:4`, `928*1664` `9:16`.
- `qwen-image-edit-max`
  - Also uses `size`, not a separate aspect-ratio field.
  - `size` can be any `width*height` where each side is `512` to `2048`.
  - The default output follows the input image ratio unless `size` is provided.

So: yes, users can steer `9:16` or `16:9`, but in practice this is done through image `size` presets rather than a standalone aspect-ratio request field.

## Core response models

### `AuthResponse`
`{ token, user }`

### `UserResponse`
`{ id, email, created_at }`

### `StoryResponse`
`{ id, title, prompt, genre, style, frame_ratio, num_episodes, num_scenes, status, workflow_type, workflow_version, generation_version, approval_status, workflow_state, episode_plan, created_at, updated_at }`

### `CharacterResponse`
`{ id, story_id, name, description, role, personality, appearance, ref_image_urls, approval_status, locked, scene_ids, created_at }`

### `SceneResponse`
`{ id, episode_id, scene_number, prompt, clip_url, image_url, exit_frame_url, duration, status, approval_status, locked, regeneration_count, generation_version, image_model, image_model_version, edit_model, edit_model_version, source_scene_id, state_snapshot, character_ids, primary_character_ids, created_at, title, description, visual_prompt, mood, location, narration, media_kind, frame_ratio }`

### `EpisodeResponse`
`{ id, story_id, episode_number, title, summary, assembled_video_url, manifest_url, status, scenes, created_at }`

### `GenerationJobResponse`
`{ id, entity_type, entity_id, status, progress, total_steps, current_step, error, result, started_at, completed_at, created_at, job_type, attempts, max_attempts, worker_id, leased_at, lease_expires_at, last_heartbeat_at, updated_at }`

### `GenerationCheckpointResponse`
`{ id, story_id, job_id, resume_job_id, batch_number, batch_size, start_episode_number, start_scene_number, end_episode_number, end_scene_number, status, generation_version, narration_model, narration_voice, narration_text, audio_job_id, audio_status, narration_audio_url, narration_audio_manifest_url, state_snapshot, resume_state, reviewer_notes, approved_at, reviewed_at, created_at, updated_at }`

### `GalleryItemResponse`
`{ id, kind, media_kind, story_id, story_title, episode_id, episode_number, scene_id, scene_number, title, summary, media_url, duration, created_at }`

## Auth endpoints

### `POST /pipeline/auth/register`
Request:
`{ email, password }`

Returns:
`AuthResponse`

### `POST /pipeline/auth/login`
Request:
`{ email, password }`

Returns:
`AuthResponse`

### `GET /pipeline/auth/me`
Returns:
`UserResponse`

### `POST /pipeline/auth/logout`
No body required.

Returns:
`{ ok: true }`

## Story endpoints

### `POST /pipeline/stories`
Request:
`{ title, prompt, genre, style, num_episodes, num_scenes, workflow_type, bible_ids, style_reference_urls, character_reference_urls, scene_reference_urls }`

Returns:
`StoryResponse`

### `GET /pipeline/stories`
Returns:
`StoryResponse[]`

### `GET /pipeline/stories/{story_id}`
Returns:
`StoryResponse`

### `PUT /pipeline/stories/{story_id}/approve-outline`
No body required.

Returns:
`StoryResponse`

### `POST /pipeline/stories/{story_id}/generate`
No body required.

Returns:
`GenerationJobResponse`

### `POST /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/audio/regenerate`
Request:
`{ narration_model?, narration_voice? }`

Returns:
`GenerationCheckpointResponse`

### `GET /pipeline/stories/{story_id}/history`
Returns:
`HistoryEntryResponse[]`

### `GET /pipeline/stories/{story_id}/checkpoints`
Returns:
`GenerationCheckpointResponse[]`

### `PUT /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/approve`
No body required.

Returns:
`GenerationCheckpointResponse`

### `GET /pipeline/stories/{story_id}/checkpoints/{checkpoint_id}/history`
Returns:
`HistoryEntryResponse[]`

## Character endpoints

### `POST /pipeline/characters`
Request:
`{ story_id, name, description, role, personality, appearance }`

Returns:
`CharacterResponse`

### `GET /pipeline/characters/story/{story_id}`
Returns:
`CharacterResponse[]`

### `GET /pipeline/characters/{character_id}`
Returns:
`CharacterResponse`

### `PUT /pipeline/characters/{character_id}/approve`
No body required.

Returns:
`CharacterResponse`

### `PUT /pipeline/characters/{character_id}/lock`
No body required.

Returns:
`CharacterResponse`

### `PUT /pipeline/characters/{character_id}`
Request:
`{ name?, description?, role?, personality?, appearance?, ref_image_urls?, approval_status?, locked? }`

Returns:
`CharacterResponse`

### `PUT /pipeline/characters/{character_id}/reject`
No body required.

Returns:
`CharacterResponse`

### `PUT /pipeline/characters/{character_id}/references`
Request:
`{ name?, description?, role?, personality?, appearance?, ref_image_urls?, approval_status?, locked? }`

Returns:
`CharacterResponse`

### `PUT /pipeline/characters/{character_id}/unlock`
No body required.

Returns:
`CharacterResponse`

### `DELETE /pipeline/characters/{character_id}`
No body required.

### `POST /pipeline/characters/{character_id}/regenerate-refs`
No body required.

Returns:
`GenerationJobResponse`

## Scene endpoints

### `GET /pipeline/scenes/{scene_id}`
Returns:
`SceneResponse`

### `PUT /pipeline/scenes/{scene_id}/approve`
No body required.

Returns:
`SceneResponse`

### `PUT /pipeline/scenes/{scene_id}/reject`
No body required.

Returns:
`SceneResponse`

### `PUT /pipeline/scenes/{scene_id}/lock`
No body required.

Returns:
`SceneResponse`

### `POST /pipeline/scenes/{scene_id}/regenerate`
No body required.

Returns:
`GenerationJobResponse`

### `POST /pipeline/scenes`
Request:
`{ episode_id, scene_number, prompt, title?, description?, visual_prompt?, mood?, location?, action?, narration?, duration?, media_kind?, frame_ratio?, character_ids?, reference_image_urls?, generate? }`

Returns:
`SceneResponse`

### `PUT /pipeline/scenes/{scene_id}`
Request:
`{ scene_number?, prompt?, title?, description?, visual_prompt?, mood?, location?, action?, narration?, duration?, media_kind?, frame_ratio?, character_ids?, primary_character_ids?, reference_image_urls?, approval_status?, locked? }`

Returns:
`SceneResponse`

### `PUT /pipeline/scenes/{scene_id}/characters`
Request:
`{ character_ids, primary_character_ids }`

Returns:
`SceneResponse`

### `POST /pipeline/scenes/{scene_id}/reorder`
Request:
`{ new_scene_number }`

Returns:
`SceneResponse`

### `DELETE /pipeline/scenes/{scene_id}`
No body required.

Returns:
`204 No Content`

## Episode endpoints

### `GET /pipeline/episodes/story/{story_id}`
Returns:
`EpisodeResponse[]`

### `GET /pipeline/episodes/{episode_id}`
Returns:
`EpisodeResponse`

The episode response includes:
- `assembled_video_url` for the stitched final episode
- `manifest_url` for the episode manifest
- `scenes[]` with per-scene media URLs

## Job endpoints

### `GET /pipeline/jobs/{job_id}`
Returns:
`GenerationJobResponse`

### `GET /pipeline/jobs/entity/{entity_type}/{entity_id}`
Returns:
`GenerationJobResponse[]`

### `GET /pipeline/jobs/{job_id}/metrics`
Returns an array of metric objects:
`{ id, metric_kind, status, duration_ms, provider_latency_ms, estimated_cost_usd, retries, step_name, provider, provider_task_id, provider_request_id, error, job_id, entity_type, entity_id, workload, extra, created_at }`

### `POST /pipeline/jobs/{job_id}/cancel`
No body required.

Returns:
`GenerationJobResponse`

### `POST /pipeline/jobs/{job_id}/retry`
No body required.

Returns:
`GenerationJobResponse`

## Narration endpoints

### `GET /pipeline/narration/voices`
Returns:
`{ model, language, default_voice, voices[] }`

## Gallery endpoints

### `GET /pipeline/gallery`
Authenticated. Returns:
`GalleryItemResponse[]`

### `GET /pipeline/gallery/public`
Public. Returns:
`GalleryItemResponse[]`

## Upload endpoint

### `POST /pipeline/uploads/image`
Multipart form upload with `file`.

Returns:
`{ url, key, content_type, size }`

## Practical UI notes

- `StoryResponse.episode_plan` is where the generated outline lives.
- `StoryResponse.workflow_state` holds uploaded reference URLs.
- `EpisodeResponse.assembled_video_url` is the final stitched episode link.
- `SceneResponse.image_url` or `clip_url` is the per-scene media the console should preview.
- `GenerationCheckpointResponse.narration_audio_url` is the audio asset for narrated-image workflows.
