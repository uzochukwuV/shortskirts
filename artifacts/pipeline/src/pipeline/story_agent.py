import os
import json
from openai import AsyncOpenAI

# ─── Clients ──────────────────────────────────────────────────────────────────

_qwen_client: AsyncOpenAI | None = None
_aiml_client: AsyncOpenAI | None = None

QWEN_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
AIML_BASE_URL = "https://api.aimlapi.com/v1"

QWEN_LLM_MODELS = ["qwen-plus", "qwen-turbo", "qwen-max"]
AIML_LLM_MODELS = ["Qwen/Qwen2.5-7B-Instruct-Turbo", "gpt-4o-mini"]


def get_qwen_client() -> AsyncOpenAI:
    global _qwen_client
    if _qwen_client is None:
        _qwen_client = AsyncOpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url=QWEN_BASE_URL,
        )
    return _qwen_client


def get_aiml_client() -> AsyncOpenAI:
    global _aiml_client
    if _aiml_client is None:
        _aiml_client = AsyncOpenAI(
            api_key=os.environ.get("AIML_API_KEY", ""),
            base_url=AIML_BASE_URL,
        )
    return _aiml_client


def get_client() -> AsyncOpenAI:
    return get_qwen_client()


async def _chat(messages: list, temperature: float = 0.8, max_tokens: int = 4096) -> str:
    last_err = None
    qwen = get_qwen_client()
    for model in QWEN_LLM_MODELS:
        try:
            resp = await qwen.chat.completions.create(
                model=model, messages=messages,
                temperature=temperature, max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            if content:
                print(f"[story_agent] Used Qwen Cloud: {model}")
                return content.strip()
        except Exception as e:
            print(f"[story_agent] Qwen {model} failed: {str(e)[:80]}")
            last_err = e
            continue

    aiml_key = os.environ.get("AIML_API_KEY", "")
    if aiml_key:
        aiml = get_aiml_client()
        for model in AIML_LLM_MODELS:
            try:
                resp = await aiml.chat.completions.create(
                    model=model, messages=messages,
                    temperature=temperature, max_tokens=max_tokens,
                )
                content = resp.choices[0].message.content
                if content:
                    print(f"[story_agent] AIML fallback: {model}")
                    return content.strip()
            except Exception as e:
                last_err = e
                continue

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
          "visual_prompt": "detailed cinematic video generation prompt, anime style, specific visual details"
        }
      ]
    }
  ]
}"""

WORKFLOW_SYSTEM_PROMPTS = {
    "creator_series": f"""You are a creative anime showrunner. Given a story premise, genre, and style,
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
) -> dict:
    system_prompt = WORKFLOW_SYSTEM_PROMPTS.get(
        workflow_type,
        WORKFLOW_SYSTEM_PROMPTS["creator_series"],
    )

    bible_block = _format_bibles_for_prompt(bibles or [])

    user_msg = (
        f"Brief/Prompt: {prompt}\n"
        f"Genre: {genre}\n"
        f"Style: {style}\n"
        f"Number of episodes: {num_episodes}\n"
        f"Scenes per episode: {num_scenes}\n"
        f"Workflow type: {workflow_type}\n"
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

async def generate_character_image_prompt(character: dict, style: str = "anime") -> str:
    user_msg = (
        f"Write a detailed image generation prompt for this character:\n"
        f"Name: {character['name']}\n"
        f"Appearance: {character.get('appearance', '')}\n"
        f"Personality: {character.get('personality', '')}\n"
        f"Role: {character.get('role', 'main')}\n\n"
        f"Style: {style}. Include: character facing forward, full body or portrait, "
        f"specific hair color and style, eye color, clothing details, expression. "
        f"End with: high quality anime art, detailed illustration."
    )
    return await _chat(
        messages=[
            {"role": "system", "content": "You are an expert at writing image generation prompts for anime characters. Write concise, vivid prompts under 200 words."},
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
    style: str = "anime",
) -> str:
    base      = scene.get("visual_prompt", scene.get("description", ""))
    location  = scene.get("location", "")
    mood      = scene.get("mood", "")
    action    = scene.get("action", "")

    parts = [
        base,
        f"Location: {location}." if location else "",
        f"Mood: {mood}." if mood else "",
        f"Action: {action}." if action else "",
        f"Previous context: {previous_scene_summary}." if previous_scene_summary else "",
        f"Style: {style}, cinematic anime, high quality, detailed backgrounds, consistent character design.",
    ]
    return " ".join(p for p in parts if p)
