#!/usr/bin/env bash
# RedeTI Recovery OS: always start LAN SSH with a fixed paulo user.
# No password and no customer disks. Accept keys only from labelled USB media.
set -euo pipefail
umask 077
BASE=/run/redeti
DIR="$BASE/ssh"
PUBLIC_BASE=/run/redeti-status
PUBLIC_STATUS="$PUBLIC_BASE/ssh-status.json"
ROOT=/opt/redeti-appliance/remote
CONFIG="$ROOT/sshd_config"
mkdir -p "$DIR"
chmod 0700 "$BASE" "$DIR"
install -d -o root -g root -m 0755 "$PUBLIC_BASE"

status() {
  # All status and reason values are fixed tokens. No keys/secrets are logged.
  printf '{"state":"%s","ssh_user":"paulo","lan_ip":"%s","key_reason":"%s"}\n' \
    "$1" "${2:-}" "${3:-unknown}" > "$BASE/lan-ssh-status.json.tmp"
  chmod 0644 "$BASE/lan-ssh-status.json.tmp"
  mv -f "$BASE/lan-ssh-status.json.tmp" "$BASE/lan-ssh-status.json"
  printf '{"state":"%s","key_reason":"%s"}\n' "$1" "${3:-unknown}" > "$PUBLIC_STATUS.tmp"
  chmod 0644 "$PUBLIC_STATUS.tmp"
  mv -f "$PUBLIC_STATUS.tmp" "$PUBLIC_STATUS"
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
systemd-run --quiet --no-block --collect --unit=redeti-lan-sshd \
  --property=Restart=on-failure --property=RestartSec=2 \
  /usr/bin/sshd -D -e -f "$CONFIG"

# The LAN listener starts even without an SSH key, but no login can succeed.
# Recheck the USB and IP addresses for DHCP changes and hot-plugged media.
# Classify kernel/mount diagnostics without showing raw device output or keys.
# The UI receives only a small, fixed vocabulary of non-secret codes.
classify_mount_error() {
  if grep -Eiq 'busy|already mounted' "$DIR/last-mount-error.log" 2>/dev/null; then
    key_reason="usb_device_busy"
  elif grep -Eiq 'filesystem type|wrong fs type|bad superblock|unsupported' "$DIR/last-mount-error.log" 2>/dev/null; then
    key_reason="usb_filesystem_error"
  else
    key_reason="usb_mount_failed"
  fi
}

key_loaded=false
key_reason="waiting_usb"
while true; do
  if [ "$key_loaded" = false ]; then
    key_reason="waiting_usb"
    # For Ventoy boot, /dev/sdb1 may be busy with the ISO's device-mapper.
    # sources prints the validated physical USB followed by VentoyPart
    # ONLY when /sys confirms that the mapper has this exact USB backing.
    mapfile -t sources < <(python3 "$ROOT/provision.py" sources 2>/dev/null || true)
    if [ "${#sources[@]}" -gt 0 ]; then
      key_reason="usb_mount_failed"
      mountpoint="$BASE/lan-provision"
      mkdir -p "$mountpoint"
      for source in "${sources[@]}"; do
        keyroot=""
        mounted_here=false
        # Reuse existing mount (without remount or unmount): read only from it.
        # Never read a path unless it belongs to the approved block source.
        existing="$(findmnt -r -n -S "$source" -o TARGET 2>/dev/null | sed -n '1p' || true)"
        if [[ "$existing" = /* && "$existing" != "/" && -d "$existing" && ! -L "$existing" ]]; then
          keyroot="$existing"
        elif mount -o ro,nosuid,nodev,noexec -- "$source" "$mountpoint" 2>"$DIR/last-mount-error.log"; then
          keyroot="$mountpoint"
          mounted_here=true
        else
          classify_mount_error
          continue
        fi
        key_src="$keyroot/REDETI/authorized_keys"
        if [ -d "$keyroot/REDETI" ] && [ ! -L "$keyroot/REDETI" ] &&
           [ -f "$key_src" ] && [ ! -L "$key_src" ]; then
          if python3 "$ROOT/lan.py" install-key "$key_src" "$home/.ssh/authorized_keys"; then
            chown paulo:paulo "$home/.ssh/authorized_keys"
            chmod 0600 "$home/.ssh/authorized_keys"
            key_loaded=true
            key_reason="installed"
          else
            key_reason="invalid_public_key"
          fi
        else
          key_reason="key_file_missing"
        fi
        # Never unmount a pre-existing SystemRescue/Ventoy mount.
        if [ "$mounted_here" = true ]; then
          umount -- "$mountpoint" || true
        fi
        # If partition was readable, trying the same filesystem via another
        # device name cannot repair a missing/invalid key; stop here.
        break
      done
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
    status "ready" "$primary_ip" "installed"
  elif [ -z "$primary_ip" ]; then
    status "waiting_lan" "" "$key_reason"
  else
    status "awaiting_key" "$primary_ip" "$key_reason"
  fi
  sleep 10
done
