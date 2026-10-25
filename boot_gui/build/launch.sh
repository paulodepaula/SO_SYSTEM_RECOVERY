#!/usr/bin/env bash
# Graphical launcher; backend is independently managed by systemd.
set -euo pipefail

mkdir -p /run/redeti
log=/run/redeti/launcher.log
url=http://127.0.0.1:8765/
fallback=file:///opt/redeti-recovery/ui/offline.html

echo "RedeTI launcher: $(date -u +%FT%TZ)" >> "$log"

# The backend should start at system boot. Retry through systemd in case
# SRM loading or service startup was delayed by the live boot process.
if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload >>"$log" 2>&1 || true
  if ! systemctl is-active --quiet redeti-cockpit.service; then
    systemctl start redeti-cockpit.service >>"$log" 2>&1 || true
  fi
else
  echo "ERROR: systemd not available" >> "$log"
fi

target="$fallback"
for i in $(seq 1 60); do
  if curl --noproxy '*' -fsS --max-time 2 "${url}api/overview" >/dev/null 2>&1; then
    target="$url"
    echo "RedeTI backend available after check $i" >> "$log"
    break
  fi
  sleep 0.5
done

if [ "$target" = "$fallback" ]; then
  echo "ERROR: backend did not respond on 127.0.0.1:8765" >> "$log"
  systemctl --no-pager status redeti-cockpit.service >> "$log" 2>&1 || true
  journalctl -u redeti-cockpit.service -n 25 --no-pager >> "$log" 2>&1 || true
fi

# Starting the browser does not control the lifetime of the Python service.
if command -v firefox >/dev/null 2>&1; then
  exec firefox --kiosk "$target"
elif command -v xdg-open >/dev/null 2>&1; then
  exec xdg-open "$target"
fi
echo "ERROR: no browser found" >> "$log"
exit 1
