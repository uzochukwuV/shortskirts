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

### `PipelineRunResponse`
`{ id, owner_id, story_id, job_id, run_type, status, config, summary, error, started_at, completed_at, created_at, updated_at }`

### `PipelineConfig`
`{ media: { kind, ratio, duration_seconds, quality }, approvals: { outline_required, checkpoint_batch_size, publish_requires_approval }, providers: { video_preference, image_preference, allow_fallback_to_image }, continuity: { use_character_refs, use_previous_exit_frame, max_reference_images } }`

### `PipelineStepResponse`
`{ id, run_id, parent_step_id, story_id, episode_id, scene_id, job_id, step_key, step_type, status, attempt, provider, provider_model, provider_task_id, provider_request_id, input, output, error, started_at, completed_at, created_at, updated_at }`

### `PipelineArtifactResponse`
`{ id, run_id, step_id, story_id, episode_id, scene_id, artifact_type, media_kind, url, content, metadata, created_at }`

### `GenerationCheckpointResponse`
`{ id, story_id, job_id, resume_job_id, batch_number, batch_size, start_episode_number, start_scene_number, end_episode_number, end_scene_number, status, generation_version, narration_model, narration_voice, narration_text, audio_job_id, audio_status, narration_audio_url, narration_audio_manifest_url, state_snapshot, resume_state, reviewer_notes, approved_at, reviewed_at, created_at, updated_at }`

### `GalleryItemResponse`
`{ id, kind, media_kind, story_id, story_title, episode_id, episode_number, scene_id, scene_number, title, summary, media_url, duration, created_at }`

### `SocialAccountResponse`
`{ id, platform, platform_user_id, display_name, scopes, status, metadata, token_expires_at, created_at, updated_at }`

### `PublishTargetResponse`
`{ id, platform, social_account_id, story_id, episode_id, scene_id, artifact_id, asset_kind, media_url, title, description, tags, privacy_status, publish_mode, requires_approval, approved_at, scheduled_for, status, error, metadata, created_at, updated_at }`

### `PublishPostResponse`
`{ id, publish_target_id, platform, platform_post_id, public_url, upload_session_id, status, response, error, created_at, updated_at }`

### `ScheduleResponse`
`{ id, story_id, name, schedule_type, cadence, cadence_config, timezone, next_run_at, enabled, pipeline_config, publish_config, approval_policy, status, last_run_at, last_error, created_at, updated_at }`

### `ScheduledRunResponse`
`{ id, schedule_id, story_id, episode_id, publish_target_id, job_id, run_type, due_at, status, result, error, started_at, completed_at, created_at, updated_at }`

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

### `PUT /pipeline/stories/{story_id}/pipeline-config`
Request:
`{ pipeline_config: PipelineConfig }`

Returns:
`StoryResponse`

## Pipeline run debug endpoints

### `GET /pipeline/runs/story/{story_id}`
Returns recent pipeline runs for a story.

Returns:
`PipelineRunResponse[]`

### `GET /pipeline/runs/{run_id}`
Returns one run with ordered steps and artifacts.

Returns:
`{ run: PipelineRunResponse, steps: PipelineStepResponse[], artifacts: PipelineArtifactResponse[] }`

### `GET /pipeline/runs/{run_id}/steps`
Returns:
`PipelineStepResponse[]`

### `GET /pipeline/runs/{run_id}/artifacts`
Returns:
`PipelineArtifactResponse[]`

### `GET /pipeline/runs/steps/{step_id}`
Returns:
`PipelineStepResponse`

### `POST /pipeline/runs/steps/{step_id}/retry`
Queues scene regeneration from a failed `scene_render` step or a failed `provider_attempt` child step.

Returns:
`GenerationJobResponse`

### `POST /pipeline/runs/{run_id}/cancel`
Cancels a pending/running pipeline run and its attached generation job when present.

Returns:
`{ run: PipelineRunResponse, steps: PipelineStepResponse[], artifacts: PipelineArtifactResponse[] }`

## Social account endpoints

### `GET /pipeline/social/accounts`
Returns connected and disconnected social accounts for the signed-in user.

Returns:
`SocialAccountResponse[]`

### `POST /pipeline/social/accounts/mock`
Creates a mock social account for local smoke tests.

Request:
`{ platform: "mock", platform_user_id?, display_name?, scopes?, metadata? }`

Returns:
`SocialAccountResponse`

### `POST /pipeline/social/{platform}/connect`
Starts OAuth for `youtube` or `tiktok`.

Returns:
`{ authorization_url, state }`

### `GET /pipeline/social/youtube/callback`
OAuth callback used by Google. Stores encrypted access/refresh tokens and channel identity.

Query:
`{ code, state }`

Returns:
`{ ok, platform, display_name }`

### `GET /pipeline/social/tiktok/callback`
OAuth callback used by TikTok. Stores encrypted access/refresh tokens and account identity.

Query:
`{ code, state }`

Returns:
`{ ok, platform }`

### `DELETE /pipeline/social/accounts/{account_id}`
Marks the social account disconnected.

Returns:
`{ ok: true }`

## Publishing endpoints

### `POST /pipeline/publish-targets`
Creates a publish target for an assembled episode, generated scene, pipeline artifact, or direct external URL.

Request:
`{ platform, social_account_id?, story_id?, episode_id?, scene_id?, artifact_id?, asset_kind, media_url?, title, description?, tags?, privacy_status?, publish_mode?, requires_approval?, scheduled_for?, metadata? }`

Returns:
`PublishTargetResponse`

### `GET /pipeline/publish-targets`
Returns:
`PublishTargetResponse[]`

### `GET /pipeline/publish-targets/{target_id}`
Returns:
`PublishTargetResponse & { posts: PublishPostResponse[] }`

### `POST /pipeline/publish-targets/{target_id}/approve`
Approves a target that was created with `requires_approval=true`.

Returns:
`PublishTargetResponse`

### `POST /pipeline/publish-targets/{target_id}/publish-now`
Resolves media, queues a `publish_target` job, and returns its job id.

Returns:
`{ job_id, publish_target_id }`

### `POST /pipeline/publish-targets/{target_id}/retry`
Queues a new publish job for a failed/canceled target.

Returns:
`{ job_id, publish_target_id }`

### `POST /pipeline/publish-targets/{target_id}/cancel`
Cancels a target that has not already been published or handed to a platform processor.

Returns:
`PublishTargetResponse`

## Schedule endpoints

### `POST /pipeline/schedules`
Creates an automation schedule.

Supported `schedule_type`:
- `generate_only`
- `publish_existing`
- `generate_and_publish`
- `series_continuation`

Supported `cadence`:
- `once`
- `interval_hours`
- `daily`
- `weekly`

Request:
`{ name, schedule_type, story_id?, cadence?, cadence_config?, timezone?, next_run_at?, enabled?, pipeline_config?, publish_config?, approval_policy? }`

Returns:
`ScheduleResponse`

### `GET /pipeline/schedules`
Returns:
`ScheduleResponse[]`

### `GET /pipeline/schedules/{schedule_id}`
Returns:
`ScheduleResponse`

### `PATCH /pipeline/schedules/{schedule_id}`
Request:
Partial `ScheduleResponse` fields.

Returns:
`ScheduleResponse`

### `DELETE /pipeline/schedules/{schedule_id}`
Returns:
`{ ok: true }`

### `POST /pipeline/schedules/{schedule_id}/run-now`
Queues the schedule immediately.

Returns:
`{ scheduled_run: ScheduledRunResponse }`

### `POST /pipeline/schedules/dispatch-due`
Queues due schedules for the signed-in user. Production can also run `python src/scheduler.py` as a polling process.

Returns:
`{ queued: [{ schedule_id, job_id, job_type }] }`

### `GET /pipeline/schedules/{schedule_id}/runs`
Returns:
`ScheduledRunResponse[]`

## Social publishing environment

Required for all real social publishing:
- `SOCIAL_TOKEN_ENCRYPTION_KEY`
- `PUBLIC_BACKEND_URL`
- `FRONTEND_URL`

YouTube:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- YouTube Data API enabled
- OAuth redirect URI: `{PUBLIC_BACKEND_URL}/pipeline/social/youtube/callback`

TikTok:
- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- Content Posting API approval for `video.upload` and/or `video.publish`
- OAuth redirect URI: `{PUBLIC_BACKEND_URL}/pipeline/social/tiktok/callback`

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
