#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WORKER_WORKLOAD=story
exec "$SCRIPT_DIR/run-worker.sh"
