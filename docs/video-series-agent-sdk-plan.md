# Video Series Generator: Continuity and Claude Agent SDK Plan

**Status:** research and implementation plan
**Scope:** replace the current *planning/orchestration experience* with a Claude Agent SDK agent while retaining deterministic jobs, provider adapters, persistence, and media processing.

## Executive summary

The current result feels like clips that were cut together because the pipeline treats continuity as a small amount of prompt context rather than as a first-class production artifact. A scene defaults to five seconds, references favor character images over the prior scene's exit frame, each scene has only a narration string, and assembly concatenates clips without video or audio transitions.

The recommended design introduces a stateful production agent that can converse with the user and invoke narrowly scoped tools to inspect story assets, search the approved reference library, create a continuity plan, queue renders, inspect results, and request targeted retries. The agent should **not** directly mutate the database, execute arbitrary shell commands, or replace the job queue. Existing services remain the safe execution layer; the SDK becomes the reasoning and interaction layer above them.

The media changes should ship independently of the agent migration. Longer, beat-derived shots and continuity-aware references address the largest visual problem; structured dialogue, per-character voice casting, and timeline-aware assembly address the audio and editing problems.

## What the current pipeline actually does

### Duration and pacing

- `scene_gen.generate_scene_clip()` uses `media_config.duration_seconds` and otherwise requests **5 seconds**.
- The story-plan example says 6 seconds, and the series prompt requests values from 5–10 seconds. This makes short clips the normal case, regardless of dialogue or action complexity.
- Provider capabilities are not consulted to select a supported duration before planning the scene. The requested duration is passed through to provider adapters and the stored duration can fall back to five seconds.

### Visual style

- The default series role is a “creative anime showrunner.”
- The plan schema example, character prompt writer, scene prompt defaults, and generated fallback first frame all reinforce anime imagery.
- There is no normalized, story-level style profile with positive constraints, exclusions, reference assets, and a deliberate user choice. Removing one occurrence of “anime” would therefore not remove the bias.

### Continuity and references

- `build_scene_prompt()` adds a prose `Previous context` string, but does not specify the previous shot's final composition, screen direction, character blocking, lighting, camera state, or the intended transition.
- The orchestrator does carry `previous_exit_frame` and `previous_summary` between scenes, which is a useful foundation.
- `scene_gen` fills the reference list with character references first and only uses the previous exit frame when there are no character references. A scene containing a character can consequently omit the strongest temporal continuity reference.
- Reference choice is positional rather than semantic: there is no asset catalog query, character/location/wardrobe filtering, relevance score, provenance, or record of why an image was selected.

### Audio and assembly

- Each scene has one optional `narration` field. `build_narration_script()` combines those fields into one script, and one configured model/voice synthesizes the checkpoint.
- There is no dialogue-turn schema, character-to-voice mapping, emotion/delivery control, timing alignment, room tone, effects track, or audio bridge across a cut.
- `assemble_episode()` downloads clips and calls `concatenate_video_files()`. It has no transition plan and no per-boundary selection of hard cut, match cut, dissolve, J/L cut, or fade.

## Target experience

A user can ask the production agent, for example:

> Make scene three more realistic, keep Mara's coat and the rainy station from scene two, let Mara and Ivo speak in their own voices, and make the cut feel continuous.

The agent should:

1. Load the story bible, scene versions, cast, style profile, provider capabilities, and relevant prior run events.
2. Retrieve approved Mara, Ivo, coat, station, and previous-exit-frame assets with provenance.
3. Explain a proposed patch: shot length, transition, dialogue turns, selected references, and expected cost/latency.
4. Ask for confirmation when policy or cost requires it.
5. Call typed application tools to save a new scene-plan version and enqueue existing jobs.
6. Stream user-readable progress while durable run/step/tool events are recorded.
7. Inspect technical and continuity scores, retry only the failed shot if permitted, and present the resulting assets for approval.

## Proposed architecture

```text
Chat UI / REST or WebSocket stream
              |
      Production Agent service
  (Claude Agent SDK, session per story)
              |
   typed, allowlisted application tools
       |          |            |
  catalog/read  plan/version  enqueue/inspect
       |          |            |
 PostgreSQL + B2  existing coordinator + Redis workers
                              |
        image/video/TTS providers and FFmpeg assembler
```

### Keep deterministic responsibilities outside the model

Retain the current coordinator, provider policy, job queue, versioning, storage, and database transactions. Expose them as idempotent tools with Pydantic-validated inputs. A language model may decide *which approved action to request*, but application code must enforce authorization, story ownership, version checks, provider limits, cost ceilings, and valid state transitions.

Do not grant the production agent general filesystem, shell, network, or SQL tools in production. Use a minimal tool allowlist. Any SDK built-ins that are unnecessary for the product should be disabled.

### Agent tools

Initial read-only tools:

| Tool | Purpose | Important output |
|---|---|---|
| `get_story_context` | Load story/bible/style/cast and current versions | IDs, summaries, style profile, version tokens |
| `list_scene_assets` | List approved/user-uploaded/generated assets | asset ID, tags, source, approval, URL handle |
| `search_reference_assets` | Hybrid metadata/embedding retrieval | ranked IDs, relevance, provenance, usage rights |
| `get_scene_timeline` | Load adjacent shot and audio state | entrance/exit frames, blocking, timing, dialogue |
| `get_provider_capabilities` | Constrain duration/reference count/features | supported values and current availability |
| `get_run_status` | Inspect job/step/provider events | normalized state and failure category |

Mutation tools, added after the read path is proven:

| Tool | Purpose | Guardrails |
|---|---|---|
| `save_scene_plan_version` | Persist a reviewed structured plan | optimistic version token; never overwrite approved data |
| `assign_character_voice` | Save a voice casting choice | consent/licensing metadata; story-scoped voice IDs |
| `enqueue_scene_generation` | Invoke the existing coordinator | idempotency key, budget and provider policy |
| `enqueue_episode_assembly` | Render an approved edit decision list | all required shots/audio validated first |
| `cancel_generation_run` | Request cancellation | ownership and cancellable-state check |

Every mutation returns stable resource IDs rather than large media payloads. Tool responses should be bounded and redact credentials and signed URL query strings before entering model context.

### Sessions and user chat

- Store the SDK session identifier against a story conversation, but keep canonical production state in PostgreSQL. Session history is context, not the source of truth.
- Resume a story session for follow-up instructions. Start a new branch/session for alternative edits so a user can compare versions without corrupting an approved cut.
- Re-read current resource versions before every mutation. A resumed conversation may contain stale assumptions.
- Stream assistant text and normalized tool progress to the UI. On reconnect, rebuild the activity feed from durable application events rather than relying on an in-memory SDK stream.
- Use a project-owned system prompt that defines the producer role, tool policy, approval gates, style neutrality, reference licensing rules, and the requirement to distinguish plans from completed actions.

### Hooks, permission gates, and logging

Use SDK lifecycle hooks where supported, plus wrappers around every application tool, to emit:

- `conversation_id`, SDK session ID, user/story/run/scene IDs, request ID, and trace ID;
- model and agent configuration version;
- tool name, input hash/redacted summary, authorization decision, start/end time, outcome, retry count, and created resource IDs;
- token/cost/latency totals and provider job IDs;
- the scene-plan version and reference asset IDs used for each render.

Never log raw API keys, cloned-voice samples, full signed URLs, or unrestricted user uploads. Apply retention and deletion policy to prompts and tool events. Require explicit confirmation for publishing, destructive replacement, voice cloning/enrollment, or work above the configured cost threshold. Pin and test the SDK version rather than silently accepting breaking upgrades.

The implementation should validate these details against the current official [Claude Agent SDK overview](https://platform.claude.com/docs/en/agent-sdk/overview), [Python SDK reference](https://platform.claude.com/docs/en/agent-sdk/python), and [permissions guidance](https://platform.claude.com/docs/en/agent-sdk/permissions) when development begins. Network access to those sources was unavailable during this repository review, so exact API symbols and hook names are intentionally not hardcoded in this plan.

## New production contracts

### Style profile

Replace string defaults such as `style="anime"` with an explicit story-level object:

```json
{
  "preset": "cinematic_realism",
  "positive": ["natural skin texture", "motivated practical lighting", "subtle film grain"],
  "avoid": ["anime", "cartoon", "cel shading", "illustration", "text", "watermark"],
  "reference_asset_ids": ["asset_style_01"],
  "user_confirmed": true
}
```

Do not always add a negative anime prompt: if a user selects anime, the preset should positively request it. Default new stories to a neutral or cinematic choice in the product UI, require the planner to honor it, and pass the same profile through character, first-frame, and video generation.

### Shot and continuity plan

Plan shots before invoking a video provider:

```json
{
  "shot_id": "scene-03-shot-01",
  "beat": "Mara recognizes Ivo on the opposite platform",
  "duration_seconds": 12,
  "opening_state": {
    "source": "previous_exit_frame",
    "screen_direction": "Mara moving left-to-right",
    "camera": "medium tracking shot",
    "wardrobe": ["mara_raincoat_v2"]
  },
  "action_phases": [
    {"seconds": [0, 4], "action": "track beside Mara"},
    {"seconds": [4, 8], "action": "Mara slows and looks across tracks"},
    {"seconds": [8, 12], "action": "slow push-in as recognition lands"}
  ],
  "exit_state": {
    "composition": "Mara foreground right, Ivo background left",
    "next_scene_hook": "hold Mara's eyeline across the tracks"
  },
  "transition_in": {"type": "match_action", "duration_seconds": 0},
  "reference_asset_ids": ["asset_mara_v2", "asset_station_rain", "scene02_exit"]
}
```

Prompt construction should render this contract into provider-specific language. Include observable movement and camera direction, but avoid cramming multiple cuts into a provider that generates a single continuous shot.

### Dialogue and voice casting

Separate spoken content from shot description:

```json
{
  "dialogue": [
    {
      "speaker_character_id": "mara",
      "text": "Ivo? I thought you were gone.",
      "emotion": "stunned, restrained",
      "pace": "slow",
      "start_hint_seconds": 5.2
    }
  ],
  "narration": [],
  "voice_cast": {
    "mara": {"provider": "configured_tts", "voice_id": "voice_mara_01"}
  }
}
```

Generate each utterance separately, record word/utterance timing when the provider supports it, and mix it on a timeline with room tone, music, and effects. Narration remains available but is not a fallback for every scene. Voice cloning must require documented speaker consent and provider terms review; ordinary licensed stock voices should be the default.

## Duration and transition policy

“Make every clip 10–15 seconds” is safer than five seconds but is still too blunt. Duration should be derived from the beat and spoken-word timing, then clamped to a provider-supported value:

- establishing or reaction shot: 6–8 seconds;
- one simple action beat: 8–12 seconds;
- dialogue shot: speech duration plus pauses and handles, commonly 10–15 seconds;
- complex action: split into coherent 6–10 second shots rather than asking one generation to perform many events.

Add 0.5–1.0 second edit handles where feasible. Do not dissolve every boundary. The planner selects a transition based on narrative intent:

- hard or match cut for continuous action and aligned composition;
- J-cut or L-cut to carry dialogue/ambience across a visual cut;
- short cross-dissolve for elapsed time, location change, or reflective mood;
- dip-to-black only for major chapter boundaries.

Implement the edit as a timeline/filter graph, not the concat demuxer alone. FFmpeg's `xfade` requires compatible video timebases/resolutions/pixel formats, and audio needs corresponding overlap/mix logic such as `acrossfade`; normalize inputs before building the graph. Preserve a hard-cut path for intentional cuts and for providers whose shots cannot tolerate overlap.

## Reference retrieval and continuity

Create an `assets` catalog (or extend the existing asset records) with:

- story/character/location/prop/wardrobe IDs and semantic tags;
- source (`user_upload`, `approved_character_ref`, `scene_exit`, `generated_candidate`);
- approval state, generation/version lineage, perceptual hash/embedding;
- aspect ratio/resolution, provider compatibility, usage rights, consent where relevant;
- immutable storage key plus a short-lived resolved URL returned only at execution time.

Retrieval should first enforce story ownership, approval, rights, and provider constraints; then rank by exact entity/version match, adjacent-scene relationship, semantic relevance, and recency. Always reserve a slot for the immediately previous exit frame when temporal continuity is required. Deduplicate near-identical images and produce a compact reference manifest explaining each selection. The agent proposes IDs; deterministic application code resolves and validates the actual provider inputs.

Generate and store an exit frame plus a structured exit-state summary for every accepted shot. Quality control compares the next opening frame for identity, wardrobe, location, dominant color/lighting, screen direction, and relevant object state. Low scores should trigger review or a bounded targeted retry—not an autonomous regeneration loop.

## Delivery plan

### Phase 0 — Baseline and feature flags

1. Capture a fixed evaluation set spanning realism, anime, two-person dialogue, location changes, and action continuity.
2. Record current cut-boundary continuity, average shot duration, regeneration rate, provider cost, time to approved episode, style violations, and viewer ratings.
3. Add independent flags for structured plans, continuity references, dialogue audio, timeline assembly, and agent chat. Preserve the existing path as rollback.

**Exit:** repeatable baseline renders and metrics exist; flags can select old or new behavior.

### Phase 1 — Contracts, style neutrality, and pacing

1. Add versioned Pydantic models for `StyleProfile`, `ShotPlan`, `ContinuityState`, `DialogueTurn`, `VoiceCast`, `TransitionPlan`, and `ReferenceManifest`.
2. Migrate old scenes: treat their `narration` as narration and infer a legacy style without changing approved work.
3. Remove anime defaults across plan, character, first-frame, and scene generation.
4. Derive duration from beat/dialogue, then validate against provider capabilities.
5. Persist the compiled provider prompt and contract version for reproducibility.

**Exit:** no unselected anime tokens enter a cinematic render; generated plans pass schema/capability validation; median shot duration reflects the selected beat rather than a five-second fallback.

### Phase 2 — Reference catalog and scene chaining

1. Catalog existing user uploads, character references, scene references, and exit frames.
2. Implement deterministic filtered retrieval and expose read-only retrieval tools.
3. Feed the previous exit frame alongside the relevant entity references, subject to provider limits.
4. Store opening/exit states and add automated continuity checks.

**Exit:** every generated shot has a reference manifest and lineage; adjacent-scene evaluation improves without materially increasing identity failures.

### Phase 3 — Dialogue and timeline assembly

1. Add dialogue/voice-cast persistence and APIs; keep narration backward compatible.
2. Synthesize utterances per character and cache by normalized text, voice version, and delivery settings.
3. Build a timeline manifest containing clip trims, dialogue, ambience/music/effects, gain/ducking, captions, and transitions.
4. Replace plain concatenation with normalized FFmpeg filter graphs and validate output duration, streams, loudness, and A/V sync.

**Exit:** a two-character episode consistently uses two stable voices; dialogue remains intelligible; sync is within the selected tolerance; transition fallbacks are deterministic.

### Phase 4 — Read-only Claude Agent SDK integration

1. Pin the Python SDK after verifying its current runtime and packaging requirements.
2. Add a separate agent service/module and story-scoped session table.
3. Connect read-only context, catalog, timeline, capability, and status tools.
4. Stream chat/progress and persist redacted lifecycle events with trace IDs.
5. Run prompt-injection tests using story text and uploaded-asset metadata.

**Exit:** the agent accurately explains current state and proposes schema-valid plans but cannot mutate production resources.

### Phase 5 — Guarded actions

1. Add plan versioning, voice assignment, enqueue, cancellation, and assembly tools one at a time.
2. Enforce auth, optimistic concurrency, idempotency, budget, rate, and approval policy outside the agent.
3. Add confirmation cards showing the exact proposed action, cost range, references, and affected versions.
4. Cap automatic retries and require human review for publishing and voice enrollment.

**Exit:** replayed tool calls do not duplicate jobs; cross-story access tests fail closed; every mutation is attributable and reversible or versioned.

### Phase 6 — Rollout

1. Shadow the agent's proposed plans against the current planner.
2. Enable internally, then for a small opt-in cohort, then increase by measured quality/cost gates.
3. Compare against the baseline and roll back individual flags on regression.

## Acceptance criteria

- **Flow:** blinded reviewers prefer the new sequence continuity over baseline in at least 70% of evaluation pairs.
- **Pacing:** at least 95% of shot durations are justified by their beat/dialogue and supported by the selected provider; no implicit five-second fallback remains.
- **Continuity:** at least 95% of adjacent shots have stored opening/exit states and reference manifests; critical identity/wardrobe changes fall below the agreed threshold.
- **Style:** fewer than 2% of non-animation evaluation frames are classified or reviewed as anime/cartoon, with zero hardcoded anime prompt additions on that path.
- **Voices:** every dialogue turn resolves to its intended character voice; no unconsented cloned voice can be selected.
- **Assembly:** all outputs pass `ffprobe` checks for expected streams/duration, and dialogue sync stays within 100 ms in the evaluation set.
- **Agent safety:** 100% of mutations carry user/story identity, authorization outcome, idempotency key, tool event, and resulting resource IDs; prompt injection cannot obtain cross-story assets or arbitrary execution.
- **Operations:** agent-enabled completion cost and latency remain inside explicitly chosen budgets, with feature-flag rollback tested.

## Principal risks and mitigations

| Risk | Mitigation |
|---|---|
| An “agentic” rewrite makes reliable jobs nondeterministic | Keep SDK above typed services and the existing queue; never let chat history be canonical state |
| Prompt injection in story/upload metadata | Treat retrieved text as untrusted data, restrict tools, authorize every call, and test adversarial fixtures |
| Stale sessions overwrite newer edits | Re-read state and require optimistic version tokens on mutations |
| Reference URLs or voice data leak into logs/model context | Use asset IDs, execution-time URL resolution, redaction, retention controls, and consent metadata |
| Longer clips increase cost and may exceed provider limits | Capability-aware planning, per-story budgets, preview tiers, and short coherent shots for complex action |
| Dissolves create ghosting rather than continuity | Prefer match/hard cuts and audio bridges for continuous action; make transitions explicit per boundary |
| Autonomous retry loops spend excessively | Typed failure categories, maximum attempts, budget gates, and human review |
| SDK/API changes break production | Pin versions, wrap SDK usage behind an adapter, contract-test tools, and retain the legacy path |

## First implementation slice

The smallest valuable vertical slice is **not** a full replacement. Implement one cinematic-realism story with:

1. versioned style/shot/continuity contracts;
2. 8–12 second capability-validated shots;
3. the previous exit frame plus selected character/location references;
4. two licensed stock character voices represented as dialogue turns;
5. one match cut and one audio-led cross-dissolve in a timeline manifest;
6. a read-only agent chat that can explain assets and propose the next scene plan.

This slice tests visual flow, voice identity, retrieval, observability, and the SDK boundary before any model is allowed to take production actions.
