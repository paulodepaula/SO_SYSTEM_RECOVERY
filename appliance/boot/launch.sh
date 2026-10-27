#!/usr/bin/env bash
# RedeTI Appliance: runs on SystemRescue console, without desktop or web.
# Boot media is read-only; all runtime output stays in /run (tmpfs).
set -euo pipefail
umask 077
install -d -m 0700 /run/redeti
# The early systemd unit normally owns the splash. Keep a late fallback for
# images/boots where the unit was skipped or framebuffer appeared late.
redeti_splash_pid=""
if ! systemctl is-active --quiet redeti-early-splash.service 2>/dev/null; then
  /usr/bin/python3 /opt/redeti-appliance/splash.py \
    >/run/redeti/splash.log 2>&1 &
  redeti_splash_pid=$!
fi
redeti_stop_splash() {
  if [ -n "$redeti_splash_pid" ]; then
    kill "$redeti_splash_pid" 2>/dev/null || true
    wait "$redeti_splash_pid" 2>/dev/null || true
  fi
  systemctl stop redeti-early-splash.service 2>/dev/null || true
}
trap redeti_stop_splash EXIT
printf '%s\n' "RedeTI: reconhecendo hardware (somente leitura)" > /run/redeti/appliance.log
/usr/bin/python3 /opt/redeti-appliance/probe.py --output /run/redeti/hardware.json \
  >> /run/redeti/appliance.log 2>&1
# Ensure both remote services see the same account even if systemd starts
# their transient units concurrently. Login passwords remain impossible.
if ! id paulo >/dev/null 2>&1; then
  useradd --create-home --user-group --shell /usr/bin/bash --password '*' paulo || true
fi
if id paulo >/dev/null 2>&1; then
  usermod --password '*' paulo || true
fi
# Remote access is a separate transient systemd service, never a UI dependency.
# It requires an explicitly provisioned USB VPN auth key to connect.
if command -v systemd-run >/dev/null 2>&1; then
  # LAN SSH is independent from VPN enrollment and starts at every boot.
  systemd-run --quiet --collect --unit=redeti-lan-ssh \
    /usr/bin/bash /opt/redeti-appliance/remote/lan-start.sh \
    >> /run/redeti/appliance.log 2>&1 || true
  systemd-run --quiet --collect --unit=redeti-remote \
    /usr/bin/bash /opt/redeti-appliance/remote/start.sh \
    >> /run/redeti/appliance.log 2>&1 || true
fi
redeti_stop_splash
printf '%s\n' "RedeTI: abrindo interface DRM/KMS" >> /run/redeti/appliance.log
# Capture native crashes (including SIGSEGV/ABI loader failures) in RAM.
# Never conceal the error behind a bare SystemRescue login prompt.
if /opt/redeti-appliance/bin/redeti-ui /run/redeti/hardware.json >> /run/redeti/ui.log 2>&1; then
  echo "RedeTI: UI finished normally" >> /run/redeti/appliance.log
else
  code=$?
  echo "$code" > /run/redeti/ui.exit
  echo "RedeTI: Falha na interface nativa, status $code." | tee -a /run/redeti/appliance.log >&2
  tail -n 35 /run/redeti/ui.log >&2 || true
  echo "Consulte: /run/redeti/ui.log e /var/log/sysrescue-autorun.log" >&2
  exit "$code"
fi
