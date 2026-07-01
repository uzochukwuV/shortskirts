import os
import json
from openai import AsyncOpenAI

_client: AsyncOpenAI | None = None

QWEN_MODELS = ["qwen-turbo", "qwen-plus", "qwen-max", "qwen2.5-72b-instruct", "qwen2.5-7b-instruct"]


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=os.environ["DASHSCOPE_API_KEY"],
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
    return _client


async def _chat(messages: list, temperature: float = 0.8, max_tokens: int = 4096) -> str:
    client = get_client()
    last_err = None
    for model in QWEN_MODELS:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if "AccessDenied" in str(e) or "403" in str(e) or "Unpurchased" in str(e):
                last_err = e
                continue
            raise
    raise RuntimeError(
        f"No accessible Qwen model found (tried {QWEN_MODELS}). "
        f"Please activate a model in your DashScope console. Last error: {last_err}"
    )


STORY_PLANNER_SYSTEM = """You are a creative anime story director. Given a story prompt, genre, and style, 
generate a detailed episode plan as valid JSON. Be vivid and cinematic.

Return ONLY valid JSON with this exact structure:
{
  "synopsis": "2-3 sentence story overview",
  "setting": "world/location description",
  "themes": ["theme1", "theme2"],
  "characters": [
    {
      "name": "Character Name",
      "role": "main|supporting|antagonist",
      "description": "brief description",
      "personality": "personality traits",
      "appearance": "visual description for image generation - be specific about hair color, eye color, clothing, style"
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
          "description": "what happens in this scene",
          "characters_present": ["Character Name"],
          "location": "specific location",
          "mood": "emotional tone",
          "action": "key action or event",
          "visual_prompt": "detailed cinematic prompt for video generation, anime style, specific visual details"
        }
      ]
    }
  ]
}"""


async def generate_episode_plan(
    prompt: str,
    genre: str,
    style: str,
    num_episodes: int,
    num_scenes: int,
) -> dict:
    user_msg = (
        f"Story prompt: {prompt}\n"
        f"Genre: {genre}\n"
        f"Style: {style}\n"
        f"Number of episodes: {num_episodes}\n"
        f"Scenes per episode: {num_scenes}\n\n"
        "Generate the complete episode plan as JSON."
    )
    content = await _chat(
        messages=[
            {"role": "system", "content": STORY_PLANNER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.85,
        max_tokens=4096,
    )
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content.strip())


async def generate_character_image_prompt(character: dict, style: str = "anime") -> str:
    user_msg = (
        f"Write a detailed image generation prompt for this anime character:\n"
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
            {
                "role": "system",
                "content": "You are an expert at writing image generation prompts for anime characters. Write concise, vivid prompts.",
            },
            {"role": "user", "content": user_msg},
        ],
        temperature=0.7,
        max_tokens=256,
    )


async def build_scene_prompt(
    scene: dict,
    story_context: dict,
    previous_scene_summary: str = "",
    style: str = "anime",
) -> str:
    base = scene.get("visual_prompt", scene.get("description", ""))
    location = scene.get("location", "")
    mood = scene.get("mood", "")
    action = scene.get("action", "")

    parts = [
        base,
        f"Location: {location}." if location else "",
        f"Mood: {mood}." if mood else "",
        f"Action: {action}." if action else "",
        f"Previous context: {previous_scene_summary}." if previous_scene_summary else "",
        f"Style: {style}, cinematic anime, high quality, detailed backgrounds, consistent character design.",
    ]
    return " ".join(p for p in parts if p)
