import os
import hashlib
import httpx
import math
from typing import Optional

from storage.b2 import upload_bytes, build_key
from pipeline.story_agent import get_client, generate_character_image_prompt

AIML_BASE_URL = "https://api.aimlapi.com"
IMAGE_MODELS = ["alibaba/wan2.7-image", "flux/schnell"]


async def generate_character_references(
    story_id: str,
    character_id: str,
    character: dict,
    style: str = "anime",
    num_refs: int = 3,
) -> list[str]:
    angles = ["front view portrait", "3/4 view portrait", "side profile"][:num_refs]
    base_prompt = await generate_character_image_prompt(character, style)

    urls = []
    for i, angle in enumerate(angles):
        prompt = f"{base_prompt}, {angle}"
        image_bytes = await _generate_image(prompt)
        if image_bytes:
            key = build_key(story_id, "characters", character_id, "refs", f"ref_{i}.jpg")
            b2_url = upload_bytes(image_bytes, key, "image/jpeg")
            urls.append(b2_url)
        else:
            print(f"[character_gen] Skipped ref {i} for {character['name']} — generation failed")

    return urls


async def _generate_image(prompt: str) -> Optional[bytes]:
    last_err = None
    for model in IMAGE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=60) as http:
                r = await http.post(
                    f"{AIML_BASE_URL}/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {os.environ['AIML_API_KEY']}",
                        "Content-Type": "application/json",
                    },
                    json={"model": model, "prompt": prompt, "n": 1, "size": "1024x1024"},
                )
                r.raise_for_status()
                data = r.json()

            image_url = data["data"][0]["url"]
            async with httpx.AsyncClient(timeout=60) as http:
                img_r = await http.get(image_url, follow_redirects=True)
                img_r.raise_for_status()
                return img_r.content

        except Exception as e:
            last_err = e
            print(f"[character_gen] Image model {model} failed: {e}")
            continue

    print(f"[character_gen] All image models failed. Last: {last_err}")
    return None


def get_character_embedding(character: dict) -> list[float]:
    """
    Deterministic pseudo-embedding from character description.
    Stored as JSONB in CockroachDB for semantic similarity queries.
    In production: swap for a real embedding API call.
    """
    text = (
        f"{character['name']} {character.get('appearance', '')} "
        f"{character.get('personality', '')} {character.get('role', '')}"
    ).lower()

    dim = 128
    vec = [0.0] * dim
    for i, ch in enumerate(text):
        vec[i % dim] += ord(ch) / 1000.0

    # Normalise
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
