import os
import math
import asyncio
import time
import httpx
from typing import Optional

from storage.b2 import upload_bytes, build_key
from pipeline.story_agent import generate_character_image_prompt
from pipeline.provider_policy import run_provider_step

QWEN_IMAGE_BASE = "https://dashscope-intl.aliyuncs.com/api/v1"
QWEN_IMAGE_STUDIO_BASE = "https://{workspace_id}.cn-beijing.maas.aliyuncs.com/api/v1"
AIML_BASE_URL = "https://api.aimlapi.com"

# DashScope image models (primary)
QWEN_IMAGE_MODELS = ["wanx2.1-t2i-turbo", "wanx-v1"]
QWEN_IMAGE_REF_MODEL = "wan2.7-image-pro"
QWEN_IMAGE_EDIT_MODEL = os.getenv("QWEN_IMAGE_EDIT_MODEL", "qwen-image-edit-plus")
# AIML image models (fallback)
AIML_IMAGE_MODELS = ["alibaba/wan2.7-image", "flux/schnell"]


async def generate_character_references(
    story_id: str,
    character_id: str,
    character: dict,
    style: str = "",
    num_refs: int = 3,
) -> list[str]:
    angles = ["front view portrait", "3/4 view portrait", "side profile"][:num_refs]
    base_prompt = await generate_character_image_prompt(character, style)

    urls = []
    for i, angle in enumerate(angles):
        prompt = f"{base_prompt}, {angle}"
        image_bytes = await generate_image_bytes(prompt)
        if image_bytes:
            key = build_key(story_id, "characters", character_id, "refs", f"ref_{i}.jpg")
            b2_url = upload_bytes(image_bytes, key, "image/jpeg")
            urls.append(b2_url)
        else:
            print(f"[character_gen] Skipped ref {i} for {character['name']} — generation failed")

    return urls


async def generate_image_bytes(
    prompt: str,
    reference_image_urls: list[str] | None = None,
) -> Optional[bytes]:
    reference_image_urls = [u for u in (reference_image_urls or []) if u][:9]

    if reference_image_urls:
        result = await _try_qwen_image_edit_max(prompt, reference_image_urls)
        if result:
            return result

    # Try Qwen image generation first
    result = await _try_qwen_image_plus(prompt)
    if result:
        return result

    # Fallback: AIML
    return await _try_aiml_image(prompt)


async def _generate_image(prompt: str) -> Optional[bytes]:
    return await generate_image_bytes(prompt)


def _extract_image_url(data: dict) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in ("image_url", "url", "output_url"):
        if data.get(key):
            return data[key]
    output = data.get("output")
    if isinstance(output, dict):
        for key in ("image_url", "url", "output_url"):
            if output.get(key):
                return output[key]
        choices = output.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                if not isinstance(choice, dict):
                    continue
                message = choice.get("message") or {}
                content = message.get("content") or []
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            for key in ("image", "image_url", "url"):
                                if item.get(key):
                                    return item[key]
        results = output.get("results")
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    for key in ("url", "image_url", "output_url"):
                        if item.get(key):
                            return item[key]
    return None


async def _try_qwen_image_plus(prompt: str) -> Optional[bytes]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return None

    endpoint = f"{QWEN_IMAGE_BASE}/services/aigc/multimodal-generation/generation"
    models = [
        os.getenv("QWEN_IMAGE_MODEL", "qwen-image-plus"),
        "qwen-image",
    ]
    for model in list(dict.fromkeys([m for m in models if m])):
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ]
            },
            "parameters": {"n": 1, "watermark": False},
        }

        try:
            async with httpx.AsyncClient(timeout=120) as http:
                data = await run_provider_step(
                    "dashscope_image",
                    f"image:{model}",
                    lambda: _post_json(
                        http,
                        endpoint,
                        headers={
                            "Authorization": f"Bearer {dashscope_key}",
                            "Content-Type": "application/json",
                        },
                        payload=payload,
                    ),
                    extra={"model": model},
                    extra_builder=lambda result: {
                        "model": model,
                        "task_id": result.get("output", {}).get("task_id") or result.get("task_id") or result.get("id"),
                    },
                )

            image_url = _extract_image_url(data)
            if not image_url:
                raise RuntimeError(f"{model} succeeded but no image URL: {data}")
            async with httpx.AsyncClient(timeout=60) as http:
                img_r = await run_provider_step(
                    "dashscope_image",
                    f"image:{model}:download",
                    lambda: http.get(image_url, follow_redirects=True),
                    extra={"model": model},
                )
                return img_r.content
        except Exception as e:
            print(f"[character_gen] {model} failed: {str(e)[:120]}")
            continue
    return None


async def _try_qwen_image_edit_max(prompt: str, reference_image_urls: list[str]) -> Optional[bytes]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not dashscope_key:
        return None

    endpoint = f"{QWEN_IMAGE_BASE}/services/aigc/multimodal-generation/generation"
    content = [{"image": url} for url in reference_image_urls] + [{"text": prompt}]
    payload = {
        "model": QWEN_IMAGE_EDIT_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ]
        },
        "parameters": {"n": 1, "negative_prompt": "", "watermark": False},
    }

    try:
        async with httpx.AsyncClient(timeout=120) as http:
            data = await run_provider_step(
                "dashscope_image",
                f"image:{QWEN_IMAGE_EDIT_MODEL}",
                lambda: _post_json(
                    http,
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {dashscope_key}",
                        "Content-Type": "application/json",
                    },
                    payload=payload,
                ),
                extra={"model": QWEN_IMAGE_EDIT_MODEL, "reference_count": len(reference_image_urls)},
                extra_builder=lambda result: {
                    "model": QWEN_IMAGE_EDIT_MODEL,
                    "reference_count": len(reference_image_urls),
                    "task_id": result.get("output", {}).get("task_id") or result.get("task_id") or result.get("id"),
                },
            )

        image_url = _extract_image_url(data)
        if not image_url:
            raise RuntimeError(f"{QWEN_IMAGE_EDIT_MODEL} succeeded but no image URL: {data}")
        async with httpx.AsyncClient(timeout=60) as http:
            img_r = await run_provider_step(
                "dashscope_image",
                f"image:{QWEN_IMAGE_EDIT_MODEL}:download",
                lambda: http.get(image_url, follow_redirects=True),
                extra={"model": QWEN_IMAGE_EDIT_MODEL},
            )
            return img_r.content
    except Exception as e:
        print(f"[character_gen] {QWEN_IMAGE_EDIT_MODEL} failed: {str(e)[:120]}")
        return None


async def _try_wan_reference_image(prompt: str, reference_image_urls: list[str]) -> Optional[bytes]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    workspace_id = os.environ.get("DASHSCOPE_WORKSPACE_ID", "").strip()
    if not dashscope_key or not workspace_id:
        return None

    endpoint = f"{QWEN_IMAGE_STUDIO_BASE.format(workspace_id=workspace_id)}/services/aigc/image-generation/generation"
    content = [{"image": url} for url in reference_image_urls] + [{"text": prompt}]
    payload = {
        "model": QWEN_IMAGE_REF_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ]
        },
        "parameters": {"size": "2K"},
    }

    try:
        async with httpx.AsyncClient(timeout=90) as http:
            data = await run_provider_step(
                "dashscope_image",
                f"image:{QWEN_IMAGE_REF_MODEL}:submit",
                lambda: _post_json(
                    http,
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {dashscope_key}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "enable",
                    },
                    payload=payload,
                ),
                extra={"model": QWEN_IMAGE_REF_MODEL, "reference_count": len(reference_image_urls)},
                extra_builder=lambda result: {
                    "model": QWEN_IMAGE_REF_MODEL,
                    "reference_count": len(reference_image_urls),
                    "task_id": result.get("output", {}).get("task_id") or result.get("task_id") or result.get("id"),
                },
            )

        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"No task ID from wan2.7-image-pro submit: {data}")

        return await _poll_wan_reference_image(task_id, dashscope_key)
    except Exception as e:
        print(f"[character_gen] wan2.7-image-pro reference generation failed: {str(e)[:120]}")
        return None


async def _poll_wan_reference_image(task_id: str, api_key: str, timeout: int = 600) -> Optional[bytes]:
    workspace_id = os.environ.get("DASHSCOPE_WORKSPACE_ID", "").strip()
    if not workspace_id:
        return None

    poll_url = f"{QWEN_IMAGE_STUDIO_BASE.format(workspace_id=workspace_id)}/tasks/{task_id}"
    stop_at = time.time() + timeout

    while time.time() < stop_at:
        await asyncio.sleep(8)
        async with httpx.AsyncClient(timeout=90) as http:
            data = await run_provider_step(
                "dashscope_image",
                f"image:{QWEN_IMAGE_REF_MODEL}:poll",
                lambda: _get_json(
                    http,
                    poll_url,
                    headers={"Authorization": f"Bearer {api_key}"},
                ),
                extra={"task_id": task_id, "model": QWEN_IMAGE_REF_MODEL},
            )

        status = (
            data.get("output", {}).get("task_status")
            or data.get("task_status")
            or ""
        ).upper()
        if status in {"SUCCEEDED", "SUCCESS", "COMPLETED"}:
            image_url = _extract_image_url(data)
            if not image_url:
                raise RuntimeError(f"wan2.7-image-pro task succeeded but no image URL: {data}")
            async with httpx.AsyncClient(timeout=60) as http:
                img_r = await run_provider_step(
                    "dashscope_image",
                    f"image:{QWEN_IMAGE_REF_MODEL}:download",
                    lambda: http.get(image_url, follow_redirects=True),
                    extra={"task_id": task_id, "model": QWEN_IMAGE_REF_MODEL},
                )
                return img_r.content
        if status in {"FAILED", "CANCELLED", "CANCELED"}:
            raise RuntimeError(f"wan2.7-image-pro task failed: {data}")

    raise TimeoutError(f"wan2.7-image-pro task {task_id} timed out after {timeout}s")


async def _try_dashscope_image(prompt: str) -> Optional[bytes]:
    dashscope_key = os.environ.get("DASHSCOPE_API_KEY", "")
    workspace_id = os.environ.get("DASHSCOPE_WORKSPACE_ID", "").strip()
    if not dashscope_key or not workspace_id:
        return None

    endpoint = f"{QWEN_IMAGE_STUDIO_BASE.format(workspace_id=workspace_id)}/services/aigc/image-generation/generation"
    payload = {
        "model": QWEN_IMAGE_REF_MODEL,
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"text": prompt},
                    ],
                }
            ]
        },
        "parameters": {"size": "2K", "n": 1, "watermark": False, "thinking_mode": True},
    }

    try:
        async with httpx.AsyncClient(timeout=90) as http:
            data = await run_provider_step(
                "dashscope_image",
                f"image:{QWEN_IMAGE_REF_MODEL}:submit",
                lambda: _post_json(
                    http,
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {dashscope_key}",
                        "Content-Type": "application/json",
                        "X-DashScope-Async": "enable",
                    },
                    payload=payload,
                ),
                extra={"model": QWEN_IMAGE_REF_MODEL},
            )

        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            raise RuntimeError(f"No task ID from wan2.7-image-pro submit: {data}")

        async with httpx.AsyncClient(timeout=90) as http:
            image_r = await run_provider_step(
                "dashscope_image",
                f"image:{QWEN_IMAGE_REF_MODEL}:download",
                lambda: _poll_wan_image(task_id, http, dashscope_key, workspace_id),
                extra={"task_id": task_id, "model": QWEN_IMAGE_REF_MODEL},
            )
        print(f"[character_gen] Generated image via DashScope model: {QWEN_IMAGE_REF_MODEL}")
        return image_r

    except Exception as e:
        print(f"[character_gen] DashScope image generation failed: {str(e)[:120]}")
        return None


async def _poll_wan_image(task_id: str, http: httpx.AsyncClient, api_key: str, workspace_id: str, timeout: int = 600) -> bytes:
    poll_url = f"{QWEN_IMAGE_STUDIO_BASE.format(workspace_id=workspace_id)}/tasks/{task_id}"
    stop_at = time.time() + timeout

    while time.time() < stop_at:
        await asyncio.sleep(8)
        data = await _get_json(
            http,
            poll_url,
            headers={"Authorization": f"Bearer {api_key}"},
        )

        status = (
            data.get("output", {}).get("task_status")
            or data.get("task_status")
            or ""
        ).upper()
        if status in {"SUCCEEDED", "SUCCESS", "COMPLETED"}:
            image_url = _extract_image_url(data)
            if not image_url:
                raise RuntimeError(f"wan2.7-image-pro task succeeded but no image URL: {data}")
            async with httpx.AsyncClient(timeout=60) as download_http:
                img_r = await download_http.get(image_url, follow_redirects=True)
                img_r.raise_for_status()
                return img_r.content
        if status in {"FAILED", "CANCELLED", "CANCELED"}:
            raise RuntimeError(f"wan2.7-image-pro task failed: {data}")

    raise TimeoutError(f"wan2.7-image-pro task {task_id} timed out after {timeout}s")


async def _try_aiml_image(prompt: str) -> Optional[bytes]:
    aiml_key = os.environ.get("AIML_API_KEY", "")
    if not aiml_key:
        return None

    for model in AIML_IMAGE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=60) as http:
                data = await run_provider_step(
                    "aiml_image",
                    f"image:{model}:submit",
                    lambda: _post_json(
                        http,
                        f"{AIML_BASE_URL}/v1/images/generations",
                        headers={
                            "Authorization": f"Bearer {aiml_key}",
                            "Content-Type": "application/json",
                        },
                        payload={"model": model, "prompt": prompt, "n": 1, "size": "1024x1024"},
                    ),
                    extra={"model": model},
                )

            image_url = data["data"][0]["url"]
            async with httpx.AsyncClient(timeout=60) as http:
                img_r = await run_provider_step(
                    "aiml_image",
                    f"image:{model}:download",
                    lambda: http.get(image_url, follow_redirects=True),
                    extra={"model": model},
                )
                print(f"[character_gen] Generated image via AIML model: {model}")
                return img_r.content

        except Exception as e:
            print(f"[character_gen] AIML image model {model} failed: {str(e)[:80]}")
            continue

    print("[character_gen] All image models failed.")
    return None


async def _post_json(http: httpx.AsyncClient, url: str, headers: dict, payload: dict):
    r = await http.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


def get_character_embedding(character: dict) -> list[float]:
    """Deterministic pseudo-embedding. Replace with real embedding API in production."""
    text = (
        f"{character['name']} {character.get('appearance', '')} "
        f"{character.get('personality', '')} {character.get('role', '')}"
    ).lower()

    dim = 128
    vec = [0.0] * dim
    for i, ch in enumerate(text):
        vec[i % dim] += ord(ch) / 1000.0

    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
