#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/src"

PORT="${PORT:-5001}"
echo "[pipeline] Starting StoryForge Anime API on port $PORT..."
exec uvicorn main:app --host 0.0.0.0 --port "$PORT" --log-level info
