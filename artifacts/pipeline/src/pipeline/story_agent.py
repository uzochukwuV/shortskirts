import os
import json
from openai import AsyncOpenAI

from pipeline.provider_policy import run_provider_step

# ─── Clients ──────────────────────────────────────────────────────────────────

_brain_client: AsyncOpenAI | None = None

_using_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_API_URL" if _using_openrouter else "TOKENROUTER_API_URL",
    "https://openrouter.ai/api/v1" if _using_openrouter else "https://api.tokenrouter.com/v1",
)
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL" if _using_openrouter else "TOKENROUTER_MODEL",
    "openai/gpt-4o-mini" if _using_openrouter else "moonshotai/kimi-k3-free",
)
MODEL_BRAIN_API_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("TOKENROUTER_API_KEY", "")


def get_client() -> AsyncOpenAI:
    global _brain_client
    if _brain_client is None:
        if not MODEL_BRAIN_API_KEY:
            raise RuntimeError("No model-brain API key configured")
        _brain_client = AsyncOpenAI(
            api_key=MODEL_BRAIN_API_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
    return _brain_client


async def _chat(messages: list, temperature: float = 0.8, max_tokens: int = 4096) -> str:
    last_err = None
    client = get_client()
    try:
        resp = await run_provider_step(
            "qwen_llm",
            f"llm:{OPENROUTER_MODEL}",
            lambda: client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ),
            extra={"model": OPENROUTER_MODEL, "provider": "model_brain"},
        )
        content = resp.choices[0].message.content
        if content:
            print(f"[story_agent] Used model brain: {OPENROUTER_MODEL}")
            return content.strip()
    except Exception as e:
        last_err = e

    raise RuntimeError(f"All LLM models exhausted. Last error: {last_err}")


# ─── Workflow-type system prompts ─────────────────────────────────────────────

_SHARED_JSON_SCHEMA = """
Return ONLY valid JSON with this exact structure:
{
  "synopsis": "2-3 sentence overview",
  "setting": "world/location description",
  "themes": ["theme1", "theme2"],
  "characters": [
    {
      "name": "Character Name",
      "role": "main|supporting|antagonist",
      "description": "brief description",
      "personality": "personality traits",
      "appearance": "visual description — hair color, eye color, clothing, style, specific details"
    }
  ],
  "episodes": [
    {
      "episode_number": 1,
      "title": "Episode Title",
      "summary": "episode summary",
      "scenes": [
        {
          "scene_number": 1,
          "title": "Scene Title",
          "description": "what happens",
          "characters_present": ["Character Name"],
          "location": "specific location",
          "mood": "emotional tone",
          "action": "key action or event",
          "visual_prompt": "detailed cinematic generation prompt, specific visual details",
          "duration_seconds": 6,
          "narration": "optional narration or voiceover line for the scene"
        }
      ]
    }
  ]
}"""

WORKFLOW_SYSTEM_PROMPTS = {
    "creator_series": f"""You are a creative video series showrunner. Given a story premise, genre, and style,
generate a detailed serialized episode plan. Focus on: consistent cast across episodes, escalating story arcs,
compelling character development, and cinematic visual prompts for each scene.
{_SHARED_JSON_SCHEMA}""",

    "brand_campaign": f"""You are a brand creative director specializing in short-form video ads.
Given a product/service brief, generate a campaign plan with 1–3 video concepts (episodes).
Each episode is a 15/30/60-second ad concept with: a strong hook, product demonstration or story,
and a clear CTA in the final scene. Characters should be relatable brand personas.
Visual prompts must be on-brand, modern, and attention-grabbing.
{_SHARED_JSON_SCHEMA}""",

    "social_short": f"""You are a social content strategist specializing in TikTok, Reels, and YouTube Shorts.
Given a topic or content brief, generate a plan for vertical short-form videos.
Each episode is one short (15–60s). Structure: punchy hook scene (1–2s), tension/content (middle scenes),
payoff + CTA (final scene). Keep visual prompts dynamic, fast-paced, and trending aesthetic.
Characters should be relatable, energetic, and modern.
{_SHARED_JSON_SCHEMA}""",

    "educational": f"""You are an instructional designer and animated explainer producer.
Given an educational topic, generate an explainer video plan.
Each episode covers one key concept. Characters include: a guide/host character who explains,
and optional supporting characters who demonstrate or ask questions.
Each scene = one concept beat. Visual prompts should be clear, informative, and engaging for learners.
Use analogies, demonstrations, and step-by-step visuals.
{_SHARED_JSON_SCHEMA}""",

    "game_lore": f"""You are a cinematic narrative director for game/IP world-building content.
Given an IP bible or world concept, generate a lore video plan.
Episodes are cinematic shorts: character origin stories, world reveals, faction trailers, or lore drops.
Visual prompts must be epic, cinematic, atmospheric — think AAA game trailers. Characters are iconic,
with detailed designs that will appear consistently across lore content.
{_SHARED_JSON_SCHEMA}""",

    "narrated_image_story": f"""You are a visual story producer for narrated image sequences.
Given a story premise, generate a plan where each scene is a still image that advances the story
while narration carries the timeline forward. Optimize for character consistency, clear visual
continuity, and cost-efficient production. Each scene should include a strong single-image
composition, a scene-specific narration line, and a duration_seconds value between 5 and 10.
The main character and cast should be described consistently so future image generations can reuse
those references from scene to scene.
{_SHARED_JSON_SCHEMA}""",
}


# ─── Bible injection ──────────────────────────────────────────────────────────

def _format_bibles_for_prompt(bibles: list[dict]) -> str:
    """Serialize bibles into a prompt-friendly block."""
    if not bibles:
        return ""
    parts = ["\n\n## PRODUCTION MEMORY — follow these constraints exactly:\n"]
    for b in bibles:
        content = b.get("content", {})
        parts.append(f"### {b['bible_type'].upper()} BIBLE: {b['name']}")
        for k, v in content.items():
            if isinstance(v, list):
                parts.append(f"- {k}: {', '.join(str(i) for i in v)}")
            else:
                parts.append(f"- {k}: {v}")
        parts.append("")
    return "\n".join(parts)


# ─── Plan generation ──────────────────────────────────────────────────────────

async def generate_episode_plan(
    prompt: str,
    genre: str,
    style: str,
    num_episodes: int,
    num_scenes: int,
    workflow_type: str = "creator_series",
    bibles: list[dict] | None = None,
    reference_context: dict | None = None,
) -> dict:
    system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(
        workflow_type,
        WORKFLOW_SYSTEM_PROMPTS["creator_series"],
    )

    bible_block = _format_bibles_for_prompt(bibles or [])
    ref_lines: list[str] = []
    reference_context = reference_context or {}
    frame_ratio = reference_context.get("frame_ratio") or "16:9"
    requested_media_kind = reference_context.get("requested_media_kind") or "auto"
    for label, urls in (
        ("style_reference_urls", reference_context.get("style_reference_urls") or []),
        ("character_reference_urls", reference_context.get("character_reference_urls") or []),
        ("scene_reference_urls", reference_context.get("scene_reference_urls") or []),
    ):
        cleaned = [u for u in urls if u]
        if cleaned:
            ref_lines.append(f"- {label}: {len(cleaned)} uploaded image(s)")
    reference_block = ""
    if ref_lines:
        reference_block = "\n\n## USER-UPLOADED IMAGE REFERENCES\n" + "\n".join(ref_lines) + "\n"

    user_msg = (
        f"Brief/Prompt: {prompt}\n"
        f"Genre: {genre}\n"
        f"Style: {style}\n"
        f"Number of episodes: {num_episodes}\n"
        f"Scenes per episode: {num_scenes}\n"
        f"Workflow type: {workflow_type}\n"
        f"Requested media kind: {requested_media_kind}\n"
        f"Frame ratio: {frame_ratio}\n"
        f"{reference_block}"
        f"{bible_block}\n"
        "Generate the complete production plan as JSON."
    )

    content = await _chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
        max_tokens=4096,
    )

    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]

    return json.loads(content.strip())


# ─── Character image prompt ───────────────────────────────────────────────────

async def generate_character_image_prompt(character: dict, style: str = "") -> str:
    style_hint = f"Style: {style}" if style else ""
    user_msg = (
        f"Write a detailed image generation prompt for this character:\n"
        f"Name: {character['name']}\n"
        f"Appearance: {character.get('appearance', '')}\n"
        f"Personality: {character.get('personality', '')}\n"
        f"Role: {character.get('role', 'main')}\n\n"
        f"{style_hint}. Include: character facing forward, full body or portrait, "
        f"specific hair color and style, eye color, clothing details, expression. "
        f"End with: high quality illustration, detailed art."
    )
    return await _chat(
        messages=[
            {"role": "system", "content": "You are an expert at writing image generation prompts for character portraits. Write concise, vivid prompts under 200 words."},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=256,
    )


# ─── Scene prompt builder ─────────────────────────────────────────────────────

async def build_scene_prompt(
    scene: dict,
    story_context: dict,
    previous_scene_summary: str = "",
    style: str = "",
    media_kind: str = "video",
) -> str:
    """Build enhanced scene prompt with cinematography guidance.
    
    Produces prompts optimized for Qwen/Wan video models with:
    - Cinematic shot composition
    - Camera motion descriptions
    - Lighting atmosphere
    - Mood and emotion guidance
    """
    base = scene.get("visual_prompt", scene.get("description", ""))
    location = scene.get("location", "")
    mood = scene.get("mood", "")
    action = scene.get("action", "")
    shot_type = scene.get("shot_type", "medium shot")
    camera_motion = scene.get("camera_motion", "static")
    lighting = scene.get("lighting", "")

    frame_ratio = (
        scene.get("frame_ratio")
        or _safe_story_ratio(story_context)
        or "16:9"
    )
    
    # Build cinematic prompt components
    parts = [base.strip()]
    
    # Cinematography section
    if shot_type:
        parts.append(f"Shot: {shot_type}.")
    
    # Camera motion for dynamic videos
    if camera_motion and camera_motion != "static":
        parts.append(f"Camera: {camera_motion}.")
    else:
        parts.append("Camera: stable, professional cinematography.")
    
    # Location with atmosphere
    if location:
        parts.append(f"Setting: {location}.")
    
    # Lighting atmosphere
    if lighting:
        parts.append(f"Lighting: {lighting}.")
    elif mood:
        # Inferred lighting from mood
        mood_lighting = {
            "dramatic": "high contrast, dramatic shadows, single key light",
            "serene": "soft diffused lighting, warm tones, natural",
            "intense": "harsh lighting, strong shadows, tension",
            "mysterious": "low key, volumetric fog, rim lighting",
            "romantic": "golden hour, warm soft light, lens flare",
            "dark": "low light, deep shadows, noir style",
        }
        lighting_hint = mood_lighting.get(mood.lower(), "")
        if lighting_hint:
            parts.append(f"Lighting: {lighting_hint}.")
    
    # Action with dynamic verbs
    if action:
        parts.append(f"Action: {action}.")
    
    # Mood and emotion
    if mood:
        parts.append(f"Mood: {mood}, emotional depth.")
    
    # Previous scene continuity (critical for multi-scene stories)
    if previous_scene_summary:
        parts.append(f"Continuity: {previous_scene_summary}")
    
    # Style guidance (make it neutral, not anime-specific)
    if style:
        parts.append(f"Visual style: {style}.")
    
    # Technical specs
    if media_kind == "video":
        parts.append(f"Frame ratio: {frame_ratio}, high quality production value.")
        parts.append("Cinematic, smooth motion, professional film quality.")
    else:
        parts.append("High detail still image, no text overlay.")
    
    # Join with proper spacing
    prompt = " ".join(parts)
    
    # Ensure prompt isn't too long (Qwen models have limits)
    if len(prompt) > 1000:
        prompt = prompt[:997] + "..."
    
    return prompt


# Mapping of moods to cinematography guidance
MOOD_CINEMATOGRAPHY = {
    "dramatic": {"lighting": "high contrast", "camera": "slow push-in"},
    "serene": {"lighting": "soft diffused", "camera": "slow tracking"},
    "intense": {"lighting": "harsh", "camera": "handheld shake"},
    "mysterious": {"lighting": "low key fog", "camera": "dolly in"},
    "romantic": {"lighting": "golden warm", "camera": "slow orbit"},
    "comedic": {"lighting": "bright flat", "camera": "quick cuts"},
    "horror": {"lighting": "single source dark", "camera": "static"},
    "epic": {"lighting": "rim light", "camera": "aerial sweep"},
}


async def suggest_story_edit(story: dict, instruction: str) -> dict:
    plan = story.get("episode_plan") or {}
    workflow_type = story.get("workflow_type", "creator_series")
    content = await _chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You revise production outlines for AI video pipelines. "
                    "Return only valid JSON with this shape: "
                    '{"message":"short summary","story_patch":{"title":"optional","prompt":"optional","genre":"optional","style":"optional","synopsis":"optional","setting":"optional","themes":["optional"]}}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Workflow type: {workflow_type}\n"
                    f"Title: {story.get('title', '')}\n"
                    f"Prompt: {story.get('prompt', '')}\n"
                    f"Genre: {story.get('genre', '')}\n"
                    f"Style: {story.get('style', '')}\n"
                    f"Current synopsis: {plan.get('synopsis', '')}\n"
                    f"Current setting: {plan.get('setting', '')}\n"
                    f"Current themes: {json.dumps(plan.get('themes', []))}\n"
                    f"Instruction: {instruction}\n"
                    "Keep the patch narrowly scoped to the instruction."
                ),
            },
        ],
        temperature=0.6,
        max_tokens=1200,
    )
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


async def suggest_scene_edit(story: dict, scene: dict, instruction: str) -> dict:
    plan = story.get("episode_plan") or {}
    content = await _chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You revise a single scene in an AI video production console. "
                    "Return only valid JSON with this shape: "
                    '{"message":"short summary","scene_patch":{"title":"optional","description":"optional","visual_prompt":"optional","mood":"optional","location":"optional","action":"optional","narration":"optional","prompt":"optional"}}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Story title: {story.get('title', '')}\n"
                    f"Story synopsis: {plan.get('synopsis', '')}\n"
                    f"Scene title: {scene.get('title', '')}\n"
                    f"Scene description: {scene.get('description', '')}\n"
                    f"Scene visual prompt: {scene.get('visual_prompt', '')}\n"
                    f"Scene mood: {scene.get('mood', '')}\n"
                    f"Scene location: {scene.get('location', '')}\n"
                    f"Scene action: {scene.get('action', '')}\n"
                    f"Scene narration: {scene.get('narration', '')}\n"
                    f"Instruction: {instruction}\n"
                    "Keep character continuity and preserve the existing scene intent unless the instruction changes it."
                ),
            },
        ],
        temperature=0.6,
        max_tokens=1200,
    )
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


async def suggest_story_operation(
    story: dict,
    scene: dict | None,
    checkpoint: dict | None,
    instruction: str,
    valid_actions: list[str],
) -> dict:
    content = await _chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an operations coordinator for an AI story production console. "
                    "Choose the single best operation for the user's instruction. "
                    "You may only choose from the valid actions list. "
                    "If none fit, return operation unsupported. "
                    "Return only valid JSON with this exact shape: "
                    '{"operation":"edit_story|edit_scene|approve_outline|regenerate_outline|start_generation|regenerate_scene|approve_checkpoint|cancel_run|retry_failed_step|unsupported",'
                    '"target":"story|scene|checkpoint|run",'
                    '"message":"short explanation",'
                    '"requires_confirmation":false}'
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Story title: {story.get('title', '')}\n"
                    f"Story status: {story.get('status', '')}\n"
                    f"Instruction: {instruction}\n"
                    f"Valid actions: {json.dumps(valid_actions)}\n"
                    f"Scene context: {json.dumps(scene or {}, default=str)}\n"
                    f"Checkpoint context: {json.dumps(checkpoint or {}, default=str)}\n"
                    "Pick the smallest correct action. "
                    "Use edit_story for storyline, prompt, synopsis, theme, or outline text changes. "
                    "Use edit_scene for one-scene text or prompt changes. "
                    "Use regenerate_outline when the user wants a new outline generated. "
                    "Use start_generation when they want to render approved work. "
                    "Use regenerate_scene when they want the selected scene rerendered. "
                    "Use approve_checkpoint only when the intent is to continue past a review gate. "
                    "Use cancel_run or retry_failed_step only for run control."
                ),
            },
        ],
        temperature=0.2,
        max_tokens=500,
    )
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else parts[0]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


def _safe_story_ratio(story_context: dict) -> str | None:
    workflow_state = story_context.get("workflow_state") or {}
    if isinstance(workflow_state, str):
        try:
            workflow_state = json.loads(workflow_state)
        except Exception:
            workflow_state = {}
    return workflow_state.get("frame_ratio")
