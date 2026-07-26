from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable


class MediaToolError(RuntimeError):
    pass


def ffmpeg_path() -> str | None:
    configured = os.getenv("FFMPEG_BINARY")
    if configured:
        return configured
    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def ffmpeg_available() -> bool:
    return bool(ffmpeg_path())


async def _run_ffmpeg(args: list[str], *, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    exe = ffmpeg_path()
    if not exe:
        raise MediaToolError("ffmpeg binary is not available")

    cmd = [exe, *args]

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )

    result = await asyncio.to_thread(_run)
    if result.returncode != 0:
        rendered = " ".join(shlex.quote(part) for part in cmd)
        stderr = (result.stderr or result.stdout or "").strip()
        raise MediaToolError(f"ffmpeg failed: {rendered}\n{stderr[-2000:]}")
    return result


async def extract_last_frame_jpeg(video_bytes: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.mp4"
        output_path = Path(tmpdir) / "exit.jpg"
        input_path.write_bytes(video_bytes)

        try:
            await _run_ffmpeg(
                [
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-sseof",
                    "-0.2",
                    "-i",
                    str(input_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(output_path),
                ],
                timeout=90,
            )
        except Exception:
            await _run_ffmpeg(
                [
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(input_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(output_path),
                ],
                timeout=90,
            )

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise MediaToolError("ffmpeg did not produce an exit frame")
        return output_path.read_bytes()


async def concatenate_video_files(input_paths: Iterable[str], output_path: str) -> None:
    paths = [Path(path) for path in input_paths]
    if not paths:
        raise ValueError("No videos to concatenate")

    with tempfile.TemporaryDirectory() as tmpdir:
        list_path = Path(tmpdir) / "clips.txt"
        list_path.write_text(
            "".join(f"file {shlex.quote(str(path))}\n" for path in paths),
            encoding="utf-8",
        )
        await _run_ffmpeg(
            [
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            timeout=max(300, 120 * len(paths)),
        )

    if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
        raise MediaToolError("ffmpeg did not produce an assembled video")


async def image_sequence_to_video(
    image_paths: list[str],
    durations: list[float],
    output_path: str,
    *,
    fps: int = 24,
) -> None:
    if not image_paths:
        raise ValueError("No images to assemble")

    tmp_files: list[str] = []
    try:
        for index, image_path in enumerate(image_paths):
            duration = max(0.1, float(durations[index] if index < len(durations) else 6.0))
            segment = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            segment.close()
            tmp_files.append(segment.name)
            await _run_ffmpeg(
                [
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-loop",
                    "1",
                    "-t",
                    f"{duration:.3f}",
                    "-i",
                    image_path,
                    "-r",
                    str(fps),
                    "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
                    "-an",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                    segment.name,
                ],
                timeout=180,
            )

        await concatenate_video_files(tmp_files, output_path)
    finally:
        for path in tmp_files:
            try:
                os.unlink(path)
            except Exception:
                pass
