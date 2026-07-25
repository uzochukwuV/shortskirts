#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

import httpx


BASE_URL = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000/pipeline").rstrip("/")
EMAIL = os.getenv("SMOKE_EMAIL") or f"storyforge.smoke+{int(time.time())}@example.com"
PASSWORD = os.getenv("SMOKE_PASSWORD", "StoryForgeSmoke123!")
MEDIA_KIND = os.getenv("SMOKE_MEDIA_KIND", "video")
RATIO = os.getenv("SMOKE_RATIO", "9:16")
TIMEOUT_SECONDS = int(os.getenv("SMOKE_TIMEOUT_SECONDS", "1800"))
POLL_SECONDS = int(os.getenv("SMOKE_POLL_SECONDS", "15"))


def _print(event: str, **data: Any) -> None:
    print(json.dumps({"event": event, **data}, default=str), flush=True)


class Api:
    def __init__(self, base_url: str):
        self.client = httpx.Client(base_url=base_url, timeout=60)
        self.token: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        headers = kwargs.pop("headers", {})
        headers = {**self._headers(), **headers}
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {response.status_code}: {response.text[:1000]}")
        if not response.content:
            return None
        return response.json()

    def authenticate(self) -> dict[str, Any]:
        payload = {"email": EMAIL, "password": PASSWORD}
        try:
            data = self.request("POST", "/auth/register", json=payload, headers={})
            auth_mode = "registered"
        except RuntimeError as exc:
            if "409" not in str(exc):
                raise
            data = self.request("POST", "/auth/login", json=payload, headers={})
            auth_mode = "logged_in"
        self.token = data["token"]
        _print("auth_ok", mode=auth_mode, email=data["user"]["email"], user_id=data["user"]["id"])
        return data


def _story_payload() -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "title": f"Smoke Test Production {now}",
        "prompt": (
            "Create a short cinematic creator-series teaser about a young founder discovering "
            "an AI studio that turns a rough story idea into a polished short-form production. "
            "Keep the scenes simple, visually distinct, and safe for all audiences."
        ),
        "genre": "startup adventure",
        "style": "cinematic anime",
        "frame_ratio": RATIO,
        "requested_video_ratio": RATIO,
        "num_episodes": 1,
        "num_scenes": 3,
        "workflow_type": "social_short",
        "requested_media_kind": MEDIA_KIND,
        "pipeline_config": {
            "media": {
                "kind": MEDIA_KIND,
                "ratio": RATIO,
                "duration_seconds": 5,
                "quality": "standard",
            },
            "approvals": {
                "outline_required": True,
                "checkpoint_batch_size": 3,
                "publish_requires_approval": True,
            },
            "providers": {
                "video_preference": ["dashscope", "aiml"],
                "image_preference": ["qwen-image-edit-plus", "qwen-image-plus"],
                "allow_fallback_to_image": False,
            },
            "continuity": {
                "use_character_refs": True,
                "use_previous_exit_frame": True,
                "max_reference_images": 6,
            },
        },
    }


def _latest_run(api: Api, story_id: str) -> dict[str, Any]:
    runs = api.request("GET", f"/runs/story/{story_id}")
    if not runs:
        raise RuntimeError("No pipeline run found for generated story")
    return api.request("GET", f"/runs/{runs[0]['id']}")


def _summarize_failed_run(run_detail: dict[str, Any] | None) -> dict[str, Any]:
    if not run_detail:
        return {}
    failed_steps = [
        {
            "id": step["id"],
            "step_key": step["step_key"],
            "step_type": step["step_type"],
            "status": step["status"],
            "provider": step.get("provider"),
            "provider_model": step.get("provider_model"),
            "provider_task_id": step.get("provider_task_id"),
            "error": step.get("error"),
        }
        for step in run_detail.get("steps", [])
        if step.get("status") in {"failed", "retryable"}
    ]
    return {"run": run_detail.get("run"), "failed_steps": failed_steps[-10:]}


def main() -> int:
    api = Api(BASE_URL)
    _print("smoke_start", base_url=BASE_URL, email=EMAIL, media_kind=MEDIA_KIND, ratio=RATIO)
    api.authenticate()

    story = api.request("POST", "/stories", json=_story_payload())
    story_id = story["id"]
    _print("story_created", story_id=story_id, status=story["status"])

    updated = api.request(
        "PUT",
        f"/stories/{story_id}/pipeline-config",
        json={"pipeline_config": story["pipeline_config"]},
    )
    _print("pipeline_config_updated", story_id=story_id, media=updated["pipeline_config"]["media"])

    approved = api.request("PUT", f"/stories/{story_id}/approve-outline")
    _print("outline_approved", story_id=story_id, status=approved["status"])

    job = api.request("POST", f"/stories/{story_id}/generate")
    job_id = job["id"]
    _print("generation_started", story_id=story_id, job_id=job_id)

    deadline = time.time() + TIMEOUT_SECONDS
    run_detail: dict[str, Any] | None = None
    while time.time() < deadline:
        job = api.request("GET", f"/jobs/{job_id}")
        _print(
            "job_poll",
            job_id=job_id,
            status=job["status"],
            progress=job.get("progress"),
            current_step=job.get("current_step"),
            attempts=job.get("attempts"),
        )
        try:
            run_detail = _latest_run(api, story_id)
        except Exception:
            run_detail = None
        if job["status"] in {"completed", "failed", "canceled"}:
            break
        time.sleep(POLL_SECONDS)
    else:
        raise RuntimeError(f"Generation did not finish within {TIMEOUT_SECONDS}s")

    if job["status"] != "completed":
        _print("generation_not_completed", job=job, **_summarize_failed_run(run_detail))
        return 1

    run_detail = run_detail or _latest_run(api, story_id)
    episodes = api.request("GET", f"/episodes/story/{story_id}")
    artifacts = run_detail.get("artifacts", [])
    steps = run_detail.get("steps", [])
    provider_attempts = [s for s in steps if s.get("step_type") == "provider_attempt"]
    scene_artifacts = [a for a in artifacts if a.get("artifact_type") == "scene_media"]
    assembled = [a for a in artifacts if a.get("artifact_type") == "assembled_episode"]
    media_scenes = [
        scene
        for episode in episodes
        for scene in episode.get("scenes", [])
        if scene.get("clip_url") or scene.get("image_url")
    ]

    expected_scenes = 3
    failures = []
    if len(media_scenes) < expected_scenes:
        failures.append(f"Expected {expected_scenes} scenes with media, got {len(media_scenes)}")
    if len(scene_artifacts) < expected_scenes:
        failures.append(f"Expected {expected_scenes} scene_media artifacts, got {len(scene_artifacts)}")
    if MEDIA_KIND == "video" and not provider_attempts:
        failures.append("Expected provider_attempt steps for video generation, got none")
    if not assembled:
        failures.append("Expected assembled_episode artifact, got none")

    summary = {
        "story_id": story_id,
        "job_id": job_id,
        "run_id": run_detail["run"]["id"],
        "run_status": run_detail["run"]["status"],
        "step_count": len(steps),
        "provider_attempt_count": len(provider_attempts),
        "scene_artifact_count": len(scene_artifacts),
        "assembled_artifact_count": len(assembled),
        "episode_count": len(episodes),
        "media_scene_count": len(media_scenes),
        "assembled_urls": [a.get("url") for a in assembled if a.get("url")],
        "scene_urls": [s.get("clip_url") or s.get("image_url") for s in media_scenes],
    }
    if failures:
        _print("smoke_failed", failures=failures, summary=summary, **_summarize_failed_run(run_detail))
        return 1
    _print("smoke_passed", summary=summary)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _print("smoke_error", error=str(exc))
        raise
