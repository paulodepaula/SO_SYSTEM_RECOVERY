#!/usr/bin/env bash
# RedeTI Recovery OS v0.4 - start the local dashboard and keep it available
# for the entire graphical session, even if Firefox returns immediately.
set -euo pipefail

mkdir -p /run/redeti
log=/run/redeti/gui.log
url=http://127.0.0.1:8765/
server_pid=""
browser_pid=""

cleanup() {
  if [ -n "$server_pid" ]; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT
trap 'exit 0' INT TERM

# Use only an existing responsive local instance, otherwise launch Python.
if ! curl --noproxy '*' -fsS --max-time 2 "${url}api/overview" >/dev/null 2>&1; then
  echo "Starting RedeTI API on 127.0.0.1:8765" > "$log"
  python3 -u /opt/redeti-recovery/app/server.py --live >>"$log" 2>&1 &
  server_pid=$!
fi

ready=0
for _ in $(seq 1 80); do
  if curl --noproxy '*' -fsS --max-time 2 "${url}api/overview" >/dev/null 2>&1; then
    ready=1
    break
  fi
  if [ -n "$server_pid" ] && ! kill -0 "$server_pid" 2>/dev/null; then
    echo "RedeTI API exited before becoming ready; see $log" >&2
    cat "$log" >&2
    exit 1
  fi
  sleep 0.5
done

if [ "$ready" -ne 1 ]; then
  echo "RedeTI API unavailable after readiness timeout; see $log" >&2
  cat "$log" >&2 || true
  exit 1
fi

echo "RedeTI API ready at $url" >> "$log"
if command -v firefox >/dev/null 2>&1; then
  firefox --kiosk "$url" &
  browser_pid=$!
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$url" &
  browser_pid=$!
else
  echo "No graphical browser found. API available at $url" >> "$log"
fi

# Critical: GUI programs can fork/reuse another process and return immediately.
# Waiting on the backend keeps the Python service alive while XFCE is running.
if [ -n "$server_pid" ]; then
  wait "$server_pid" || true
else
  # An existing API instance may be managed by a different launcher.
  while curl --noproxy '*' -fsS --max-time 2 "${url}api/overview" >/dev/null 2>&1; do
    sleep 5
  done
fi
