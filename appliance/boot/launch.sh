#!/usr/bin/env bash
# RedeTI Appliance: runs on SystemRescue console, without desktop or web.
# Boot media is read-only; all runtime output stays in /run (tmpfs).
set -euo pipefail
umask 077
install -d -m 0700 /run/redeti
printf '%s\n' "RedeTI: reconhecendo hardware (somente leitura)" > /run/redeti/appliance.log
/usr/bin/python3 /opt/redeti-appliance/probe.py --output /run/redeti/hardware.json \
  >> /run/redeti/appliance.log 2>&1
printf '%s\n' "RedeTI: abrindo interface DRM/KMS" >> /run/redeti/appliance.log
exec /opt/redeti-appliance/bin/redeti-ui /run/redeti/hardware.json
