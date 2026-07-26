import asyncio
import json
import os
import tempfile
import time
from typing import Optional

import httpx

from storage.b2 import upload_bytes, download_url_to_bytes, build_key
from pipeline.provider_policy import run_provider_step

DASHSCOPE_TTS_BASE = os.getenv("DASHSCOPE_TTS_BASE", "https://dashscope.aliyuncs.com/api/v1")
NARRATION_AUDIO_MODEL = os.getenv("NARRATION_AUDIO_MODEL", "qwen-audio-3.0-tts-plus")
NARRATION_AUDIO_VOICE = os.getenv("NARRATION_AUDIO_VOICE", "longanfengyue")
NARRATION_AUDIO_LANGUAGE = os.getenv("NARRATION_AUDIO_LANGUAGE", "English")


def build_narration_script(scenes: list[dict]) -> str:
    chunks: list[str] = []
    for scene in scenes:
        title = scene.get("title") or f"Scene {scene.get('scene_number', '')}"
        narration = (scene.get("narration") or scene.get("description") or "").strip()
        if narration:
            chunks.append(f"{title}. {narration}")
    return "\n\n".join(chunks).strip()


def _extract_audio_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in ("audio_url", "url"):
        if data.get(key):
            return data[key]
    output = data.get("output")
    if isinstance(output, dict):
        audio = output.get("audio")
        if isinstance(audio, dict):
            for key in ("url", "audio_url"):
                if audio.get(key):
                    return audio[key]
        for key in ("audio_url", "url"):
            if output.get(key):
                return output[key]
    return None


async def synthesize_narration_audio(
    story_id: str,
    checkpoint_id: str,
    scenes: list[dict],
    narration_model: Optional[str] = None,
    narration_voice: Optional[str] = None,
) -> dict:
    model = narration_model or NARRATION_AUDIO_MODEL
    voice = narration_voice or NARRATION_AUDIO_VOICE
    script = build_narration_script(scenes)
    if not script:
        raise ValueError("No narration text found for checkpoint")

    endpoint = f"{DASHSCOPE_TTS_BASE}/services/aigc/multimodal-generation/generation"
    payload = {
        "model": model,
        "input": {
            "text": script,
            "voice": voice,
            "language_type": NARRATION_AUDIO_LANGUAGE,
        },
    }

    dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        raise RuntimeError("DASHSCOPE_API_KEY environment variable is required for audio synthesis")

    async with httpx.AsyncClient(timeout=120) as http:
        data = await run_provider_step(
            "dashscope_audio",
            f"audio:{model}:submit",
            lambda: _post_json(
                http,
                endpoint,
                headers={
                    "Authorization": f"Bearer {dashscope_key}",
                    "Content-Type": "application/json",
                },
                payload=payload,
            ),
            extra={"model": model, "voice": voice, "checkpoint_id": checkpoint_id},
            extra_builder=lambda result: {
                "model": model,
                "voice": voice,
                "checkpoint_id": checkpoint_id,
                "task_id": result.get("output", {}).get("task_id") or result.get("task_id") or result.get("id"),
            },
        )

    audio_url = _extract_audio_url(data)
    if not audio_url:
        raise RuntimeError(f"No audio URL returned from TTS: {data}")

    async with httpx.AsyncClient(timeout=120) as http:
        audio_r = await run_provider_step(
            "dashscope_audio",
            f"audio:{model}:download",
            lambda: http.get(audio_url, follow_redirects=True),
            extra={"model": model, "voice": voice, "checkpoint_id": checkpoint_id},
            extra_builder=lambda _result: {
                "model": model,
                "voice": voice,
                "checkpoint_id": checkpoint_id,
                "audio_source_url": audio_url,
            },
        )

    key = build_key(story_id, "checkpoints", checkpoint_id, "narration.mp3")
    narration_audio_url = upload_bytes(audio_r.content, key, "audio/mpeg")

    manifest = {
        "story_id": story_id,
        "checkpoint_id": checkpoint_id,
        "model": model,
        "voice": voice,
        "language": NARRATION_AUDIO_LANGUAGE,
        "audio_source_url": audio_url,
        "script": script,
    }
    manifest_bytes = json.dumps(manifest, indent=2).encode()
    manifest_key = build_key(story_id, "checkpoints", checkpoint_id, "narration-manifest.json")
    narration_audio_manifest_url = upload_bytes(manifest_bytes, manifest_key, "application/json")

    return {
        "narration_audio_url": narration_audio_url,
        "narration_audio_manifest_url": narration_audio_manifest_url,
        "narration_text": script,
        "narration_model": model,
        "narration_voice": voice,
    }


async def _post_json(http: httpx.AsyncClient, url: str, headers: dict, payload: dict):
    r = await http.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()
