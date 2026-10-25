#!/usr/bin/env bash
# RedeTI Appliance: runs on SystemRescue console, without desktop or web.
# Boot media is read-only; all runtime output stays in /run (tmpfs).
set -euo pipefail
umask 077
install -d -m 0700 /run/redeti
printf '%s\n' "RedeTI: reconhecendo hardware (somente leitura)" > /run/redeti/appliance.log
/usr/bin/python3 /opt/redeti-appliance/probe.py --output /run/redeti/hardware.json \
  >> /run/redeti/appliance.log 2>&1
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
printf '%s\n' "RedeTI: abrindo interface DRM/KMS" >> /run/redeti/appliance.log
exec /opt/redeti-appliance/bin/redeti-ui /run/redeti/hardware.json
