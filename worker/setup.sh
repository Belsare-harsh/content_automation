#!/bin/sh
# Setup for the cloud worker (fresh session each run). Safe to run twice.
set -e
cd "$(dirname "$0")/.."
python3 -c "import yaml, PIL" 2>/dev/null || pip install --quiet --break-system-packages pyyaml pillow
if [ -d tools/remotion ] && [ ! -d tools/remotion/node_modules ]; then (cd tools/remotion && npm ci --silent --no-audit --no-fund); fi
command -v google-chrome >/dev/null || echo "WARN: no google-chrome; video renders will fail (Remotion needs a browser)."
python3 -m pytest -q tests >/dev/null 2>&1 && echo "Engine tests pass." || echo "WARN: engine tests failed; check before rendering."
echo "Worker ready."
