#!/usr/bin/env bash
# RedeTI Recovery OS: always start LAN SSH with a fixed paulo user.
# No password and no customer disks. Accept keys only from labelled USB media.
set -euo pipefail
umask 077
BASE=/run/redeti
DIR="$BASE/ssh"
ROOT=/opt/redeti-appliance/remote
CONFIG="$ROOT/sshd_config"
mkdir -p "$DIR"
chmod 0700 "$BASE" "$DIR"

status() {
  # caller supplies only fixed states and numeric IPv4 addresses.
  printf '{"state":"%s","ssh_user":"paulo","lan_ip":"%s"}\n' "$1" "${2:-}" > "$BASE/lan-ssh-status.json.tmp"
  chmod 0644 "$BASE/lan-ssh-status.json.tmp"
  mv -f "$BASE/lan-ssh-status.json.tmp" "$BASE/lan-ssh-status.json"
}

status "starting"
if ! id paulo >/dev/null 2>&1; then
  useradd --create-home --user-group --shell /usr/bin/bash --password '*' paulo
fi
# The star is an invalid password hash, not the '!' shadow lock marker.
# Public key and Tailscale SSH are the only permitted authentication paths.
usermod --password '*' paulo
home="$(getent passwd paulo | cut -d: -f6)"
[ "$home" = "/home/paulo" ] || { status "invalid_user_home"; exit 2; }
install -d -o paulo -g paulo -m 0700 "$home/.ssh"
install -o paulo -g paulo -m 0600 /dev/null "$home/.ssh/authorized_keys"

if [ ! -x /usr/bin/sshd ] && ! command -v sshd >/dev/null 2>&1; then
  status "sshd_missing"
  exit 1
fi

# Use a new host key in RAM on every boot, not a private key baked into ISO.
if [ ! -s "$DIR/ssh_host_ed25519_key" ]; then
  ssh-keygen -q -t ed25519 -N '' -f "$DIR/ssh_host_ed25519_key"
fi
ssh-keygen -lf "$DIR/ssh_host_ed25519_key.pub" > "$DIR/host_fingerprint"

# Stop the default SystemRescue SSH daemon, which may otherwise offer root login.
systemctl stop sshd.service sshd.socket >/dev/null 2>&1 || true
/usr/bin/sshd -t -f "$CONFIG" || { status "sshd_invalid_config"; exit 1; }
# Configure INPUT allowlist before opening any listener to avoid a brief
# unprotected startup window.
# Put an explicit allowlist before any pre-existing permissive rules.
# A preexisting tailnet-specific rule in INPUT remains effective via RETURN.
iptables -N REDETI_LAN_SSH >/dev/null 2>&1 || true
iptables -C REDETI_LAN_SSH -i tailscale0 -j RETURN >/dev/null 2>&1 ||
  iptables -I REDETI_LAN_SSH 1 -i tailscale0 -j RETURN
iptables -C REDETI_LAN_SSH -j DROP >/dev/null 2>&1 ||
  iptables -A REDETI_LAN_SSH -j DROP
iptables -C INPUT -p tcp --dport 22 -j REDETI_LAN_SSH >/dev/null 2>&1 ||
  iptables -I INPUT 1 -p tcp --dport 22 -j REDETI_LAN_SSH
systemd-run --quiet --collect --unit=redeti-lan-sshd \
  --property=Restart=on-failure --property=RestartSec=2 \
  /usr/bin/sshd -D -e -f "$CONFIG"

# The LAN listener starts even without an SSH key, but no login can succeed.
# Recheck the USB and IP addresses for DHCP changes and hot-plugged media.
key_loaded=false
while true; do
  if [ "$key_loaded" = false ]; then
    device="$(python3 "$ROOT/provision.py" 2>/dev/null || true)"
    if [ -n "$device" ]; then
      mountpoint="$BASE/lan-provision"
      mkdir -p "$mountpoint"
      if mount -o ro,nosuid,nodev,noexec -- "$device" "$mountpoint" 2>/dev/null; then
        key_src="$mountpoint/REDETI/authorized_keys"
        if [ -f "$key_src" ] && [ ! -L "$key_src" ]; then
          if python3 "$ROOT/lan.py" install-key "$key_src" "$home/.ssh/authorized_keys"; then
            chown paulo:paulo "$home/.ssh/authorized_keys"
            chmod 0600 "$home/.ssh/authorized_keys"
            key_loaded=true
          fi
        fi
        umount -- "$mountpoint" || true
      fi
    fi
  fi

  primary_ip=""
  while IFS=$'\t' read -r iface subnet address; do
    [ -n "$iface" ] || continue
    if ! iptables -C REDETI_LAN_SSH -i "$iface" -s "$subnet" -p tcp --dport 22 -j ACCEPT >/dev/null 2>&1; then
      # Insert before the terminal DROP; no blanket INPUT ACCEPT.
      iptables -I REDETI_LAN_SSH 1 -i "$iface" -s "$subnet" -p tcp --dport 22 -j ACCEPT
    fi
    [ -n "$primary_ip" ] || primary_ip="$address"
  done < <(python3 "$ROOT/lan.py" networks 2>/dev/null || true)

  if [ "$key_loaded" = true ] && [ -n "$primary_ip" ]; then
    status "ready" "$primary_ip"
  elif [ -z "$primary_ip" ]; then
    status "waiting_lan"
  else
    status "awaiting_key" "$primary_ip"
  fi
  sleep 10
done
