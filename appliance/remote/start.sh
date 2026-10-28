#!/usr/bin/env bash
# RedeTI Recovery OS: temporary private VPN over Tailscale.
# No public listener, no embedded credential; same hardened OpenSSH on LAN/VPN.
set -euo pipefail
umask 077

base=/run/redeti
socket="$base/tailscaled.sock"
public_base=/run/redeti-status
public_status_file="$public_base/vpn-status.json"
ts=/opt/redeti-appliance/bin/tailscale
daemon=/opt/redeti-appliance/bin/tailscaled
provision_script=/opt/redeti-appliance/remote/provision.py
# Secure default: preserve key-only OpenSSH on tailnet until admin explicitly
# opts in to Tailscale-managed SSH *after* verifying restrictive tailnet ACLs.
ssh_managed=false
vpn_ssh_mode="disabled"
mkdir -p "$base"
chmod 0700 "$base"
install -d -o root -g root -m 0755 "$public_base"

public_status() {
  local state="$1" connectivity=failed failure_code=registration_failed registration_stage=registration
  case "$state" in
    starting|bootstrap_failed) connectivity=starting; failure_code=none; registration_stage=bootstrap ;;
    awaiting_provision) connectivity=not_configured; failure_code=provisioning_missing; registration_stage=provisioning ;;
    invalid_auth_key) failure_code=provisioning_invalid; registration_stage=provisioning ;;
    connecting) connectivity=connecting; failure_code=none; registration_stage=connecting ;;
    firewall_unverified|unsafe_runtime_storage|firewall_blocked) failure_code=connectivity_firewall; registration_stage=preflight ;;
    vpn_binary_missing) failure_code=connectivity_daemon; registration_stage=daemon ;;
    vpn_daemon_failed) failure_code=connectivity_daemon; registration_stage=daemon ;;
    vpn_auth_failed) failure_code=authentication ;;
    vpn_tag_failed) failure_code=tag_authorization ;;
    vpn_connectivity_failed) failure_code=connectivity ;;
    vpn_no_ip) failure_code=connectivity_no_ip ;;
    connected) connectivity=connected; failure_code=none; registration_stage=registered ;;
  esac
  printf '{"state":"%s","connectivity":"%s","failure_code":"%s","registration_stage":"%s","vpn_ssh_mode":"%s"}\n' \
    "$state" "$connectivity" "$failure_code" "$registration_stage" "$vpn_ssh_mode" > "$public_status_file.tmp"
  chmod 0644 "$public_status_file.tmp"
  mv -f "$public_status_file.tmp" "$public_status_file"
}

status() {
  # Fixed, non-secret state codes and a validated tailnet IPv4 address only.
  printf '{"state":"%s","ssh_user":"paulo","vpn_ip":"%s","vpn_ssh_mode":"%s"}\n' \
    "$1" "${2:-}" "$vpn_ssh_mode" > "$base/remote-status.json.tmp"
  chmod 0644 "$base/remote-status.json.tmp"
  mv -f "$base/remote-status.json.tmp" "$base/remote-status.json"
  public_status "$1"
}
status "starting"
trap 'status "bootstrap_failed"' ERR

# Live SystemRescue: transient host, no passwords and no storage on client disks.
if ! id paulo >/dev/null 2>&1; then
  useradd --create-home --user-group --shell /usr/bin/bash --password '*' paulo
fi
usermod --password '*' paulo
if [ ! -x "$ts" ] || [ ! -x "$daemon" ]; then
  status "vpn_binary_missing"
  exit 1
fi
if ! command -v iptables >/dev/null 2>&1; then
  status "firewall_unverified"
  exit 1
fi
# Refuse to store even a short-lived enrollment token outside RAM.
if [ "$(findmnt -n -o FSTYPE -T "$base" 2>/dev/null)" != "tmpfs" ]; then
  status "unsafe_runtime_storage"
  exit 1
fi

# Provision a short-lived, tagged Tailscale auth key from the physical USB.
# The ISO contains this code but NEVER contains the key itself. A key is
# copied only to tmpfs, then removed before returning.
auth_file="$base/ts-authkey"
provision="$base/vpn-provision"
install -d -m 0700 "$provision"
cleanup() {
  rm -f -- "$auth_file"
  # Unmount only a mount that this script owns; never remove Ventoy's mount.
  if [ "${mounted_here:-false}" = true ]; then
    umount -- "$provision" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

found=false
invalid_seen=false
# Central Hermes enrollment, when explicitly configured, writes this one-use
# key into tmpfs. Validate it without printing it; otherwise use the existing
# read-only USB contingency below.
if [ -f "$auth_file" ] && [ ! -L "$auth_file" ] &&
   grep -Eq '^tskey-auth-[A-Za-z0-9_-]{10,240}$' "$auth_file" &&
   [ "$(wc -l < "$auth_file")" -eq 1 ]; then
  found=true
else
  rm -f -- "$auth_file"
fi
for attempt in $(seq 1 15); do
  if [ "$found" != true ] && [ -f "$auth_file" ] && [ ! -L "$auth_file" ] &&
     grep -Eq '^tskey-auth-[A-Za-z0-9_-]{10,240}$' "$auth_file" &&
     [ "$(wc -l < "$auth_file")" -eq 1 ]; then
    found=true
  fi
  if [ "$found" = true ]; then break; fi
  # source candidates are restricted to USB Ventoy/REDETI_CFG FAT/exFAT and
  # validated device-mapper aliases, not customer SATA/NVMe partitions.
  mapfile -t sources < <(python3 "$provision_script" sources 2>/dev/null || true)
  for source in "${sources[@]}"; do
    keyroot=""
    mounted_here=false
    existing="$(findmnt -r -n -S "$source" -o TARGET 2>/dev/null | sed -n '1p' || true)"
    if [[ "$existing" = /* && "$existing" != "/" && -d "$existing" && ! -L "$existing" ]]; then
      keyroot="$existing"
    elif mount -o ro,nosuid,nodev,noexec -- "$source" "$provision" 2>/dev/null; then
      keyroot="$provision"
      mounted_here=true
    else
      continue
    fi
    file="$keyroot/REDETI/ts-authkey"
    if [ -d "$keyroot/REDETI" ] && [ ! -L "$keyroot/REDETI" ] &&
       [ -f "$file" ] && [ ! -L "$file" ]; then
      # Never echo/trace auth key. Strict format/length; no other USB files.
      if python3 - "$file" "$auth_file" <<'PY'
import os, pathlib, re, sys
src, dst = map(pathlib.Path, sys.argv[1:])
try:
    value = src.read_bytes()
    key = value.decode("ascii").strip()
except (OSError, UnicodeDecodeError):
    raise SystemExit(2)
if len(value) > 300 or not re.fullmatch(r"tskey-auth-[A-Za-z0-9_-]{10,240}", key):
    raise SystemExit(2)
fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "w", encoding="ascii") as stream:
    stream.write(key + "\n")
PY
      then
        found=true
        # An empty opt-in marker is *not* a credential. Its only purpose is
        # to require a deliberate approval before switching SSH auth paths.
        # Tailscale SSH ACLs must restrict access to paulo and approved staff.
        marker="$keyroot/REDETI/tailscale-ssh.enable"
        if [ -f "$marker" ] && [ ! -L "$marker" ] &&
           [ "$(wc -c < "$marker")" -eq 0 ]; then
          ssh_managed=true
          vpn_ssh_mode="managed"
        fi
      else
        invalid_seen=true
        status "invalid_auth_key"
      fi
    fi
    if [ "$mounted_here" = true ]; then
      umount -- "$provision" >/dev/null 2>&1 || true
      mounted_here=false
    fi
    # The first readable validated partition is authoritative.
    break
  done
  if [ "$found" = true ]; then break; fi
  if [ -f "$auth_file" ]; then rm -f -- "$auth_file"; fi
  sleep 2
done
if [ "$found" != true ]; then
  if [ "$invalid_seen" = true ]; then
    status "invalid_auth_key"
  else
    status "awaiting_provision"
  fi
  exit 0
fi
status "connecting"

# Install fail-closed VPN firewall BEFORE starting tailscaled. The off mode
# prevents its automatic rules from bypassing our restriction or reordering it.
# Never flush a chain that might already be enforcing a deny policy.
if ! iptables -N REDETI_VPN_INPUT 2>/dev/null; then
  status "firewall_blocked"
  exit 1
fi
if ! iptables -A REDETI_VPN_INPUT -j DROP ||
   ! iptables -I INPUT 1 -i tailscale0 -j REDETI_VPN_INPUT ||
   ! iptables -I OUTPUT 1 -o tailscale0 -m conntrack --ctstate NEW -j DROP; then
  status "firewall_blocked"
  exit 1
fi

# Tailscale sessions are ephemeral: state lives in RAM, never in client disks.
systemd-run --quiet --collect --unit=redeti-tailscaled \
  --property=Restart=on-failure --property=RestartSec=2 \
  "$daemon" --state=mem: --socket="$socket" >/dev/null
for attempt in $(seq 1 40); do
  [ -S "$socket" ] && break
  sleep 0.5
done
if [ ! -S "$socket" ]; then
  status "vpn_daemon_failed"
  exit 1
fi

# Tailscale-managed SSH is opt-in only. When enabled it authenticates using
# tailnet SSH ACLs and managed host keys on the Tailscale IP. The LAN remains
# OpenSSH with Ed25519 keys; no private keys are persisted on customer disks.
suffix="$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')"
hostname="redeti-recovery-$suffix"
if ! timeout 150 "$ts" --socket="$socket" up \
  --auth-key="file:$auth_file" \
  --ssh="$ssh_managed" --hostname="$hostname" --advertise-tags=tag:redeti-recovery \
  --netfilter-mode=off --accept-routes=false --accept-dns=false \
  >> "$base/remote.log" 2>&1; then
  if grep -Eiq 'tag|advertise-tags|not authorized' "$base/remote.log"; then
    status "vpn_tag_failed"
  elif grep -Eiq 'auth|unauthori[sz]ed|expired|invalid.*key' "$base/remote.log"; then
    status "vpn_auth_failed"
  else
    status "vpn_connectivity_failed"
  fi
  exit 1
fi
rm -f -- "$auth_file"

# Tailnet policy must allow only authorized technicians to reach this tag
# on port 22. Host firewall additionally denies ALL other tailnet ingress,
# and denies new outbound tailnet connections from the client machine.
ip="$("$ts" --socket="$socket" ip -4 2>/dev/null | sed -n '1p')"
if [[ ! "$ip" =~ ^100\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
  "$ts" --socket="$socket" down >/dev/null 2>&1 || true
  status "vpn_no_ip"
  exit 1
fi
if ! iptables -I REDETI_VPN_INPUT 1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT ||
   ! iptables -I REDETI_VPN_INPUT 2 -d "$ip/32" -p tcp --dport 22 -j ACCEPT; then
  "$ts" --socket="$socket" down >/dev/null 2>&1 || true
  status "firewall_blocked"
  exit 1
fi

# The network connection is ready; SSH additionally requires the USB public
# key state ready in lan-ssh-status.json (shown separately on the dashboard).
status "connected" "$ip"
