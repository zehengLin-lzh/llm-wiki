#!/bin/bash
cd "$(dirname "$0")"
echo "==> Syncing dependencies..."
uv sync --quiet
echo "==> Starting Personal LLM Wiki on http://127.0.0.1:7823"
uv run uvicorn app.main:app --host 127.0.0.1 --port 7823 &
APP_PID=$!
sleep 2
open http://localhost:7823
wait $APP_PID
