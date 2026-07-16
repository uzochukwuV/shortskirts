#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WORKER_WORKLOAD=media
exec "$SCRIPT_DIR/run-worker.sh"
