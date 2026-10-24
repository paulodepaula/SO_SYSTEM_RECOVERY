#!/usr/bin/env bash
set -eu
mkdir -p /run/redeti
python3 /opt/redeti-recovery/app/server.py --live >/run/redeti/gui.log 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' EXIT
for i in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8765/api/overview >/dev/null 2>&1; then break; fi
  sleep .25
done
if command -v firefox >/dev/null 2>&1; then
  firefox --kiosk http://127.0.0.1:8765/
else
  xdg-open http://127.0.0.1:8765/
fi
