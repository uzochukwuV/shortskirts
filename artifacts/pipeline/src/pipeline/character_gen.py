import os
import io
import uuid
import asyncio
import httpx
from typing import Optional
from openai import AsyncOpenAI

from storage.b2 import upload_bytes, build_key
from pipeline.story_agent import get_client, generate_character_image_prompt


async def generate_character_references(
    story_id: str,
    character_id: str,
    character: dict,
    style: str = "anime",
    num_refs: int = 3,
) -> list[str]:
    client = get_client()

    angles = ["front view portrait", "3/4 view", "side profile"][:num_refs]
    base_prompt = await generate_character_image_prompt(character, style)

    urls = []
    for i, angle in enumerate(angles):
        prompt = f"{base_prompt}, {angle}"
        try:
            response = await client.images.generate(
                model="wanx2.1-t2i-turbo",
                prompt=prompt,
                n=1,
                size="1024x1024",
            )
            image_url = response.data[0].url

            async with httpx.AsyncClient(timeout=60) as http:
                r = await http.get(image_url, follow_redirects=True)
                r.raise_for_status()
                image_bytes = r.content

            key = build_key(story_id, "characters", character_id, "refs", f"ref_{i}.jpg")
            b2_url = upload_bytes(image_bytes, key, "image/jpeg")
            urls.append(b2_url)

        except Exception as e:
            print(f"[character_gen] Failed ref {i} for {character['name']}: {e}")
            continue

    return urls


async def get_character_embedding(character: dict) -> list[float]:
    client = get_client()
    text = (
        f"Character: {character['name']}. "
        f"Appearance: {character.get('appearance', '')}. "
        f"Personality: {character.get('personality', '')}. "
        f"Role: {character.get('role', 'main')}."
    )
    response = await client.embeddings.create(
        model="text-embedding-v3",
        input=text,
    )
    return response.data[0].embedding
