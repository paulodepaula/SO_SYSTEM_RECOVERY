#!/usr/bin/env python3
"""RedeTI Recovery OS — READ-ONLY SSH and tailnet diagnosis.

This tool does not repair or change anything. It never queries customer disks,
prints keys, network addresses, hostnames, usernames, or raw command output.
The only network operation is a local TCP probe to 127.0.0.1:22.
It is intended for the Recovery OS itself; it is NOT a Hermes diagnostic.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import socket
import subprocess
import sys

_STATUS = Path("/run/redeti/remote-status.json")
_SSH_STATUS = Path("/run/redeti/lan-ssh-status.json")
_BANNER = Path("/opt/redeti-appliance/remote/ssh-banner.txt")

_VPN_STATES = frozenset({
    "starting", "bootstrap_failed", "vpn_binary_missing",
    "firewall_unverified", "unsafe_runtime_storage", "firewall_blocked",
    "invalid_auth_key", "awaiting_provision", "connecting",
    "vpn_daemon_failed", "vpn_auth_failed", "vpn_no_ip", "connected",
})
_LAN_STATES = frozenset({
    "starting", "invalid_user_home", "sshd_missing",
    "sshd_invalid_config", "ready", "waiting_lan", "awaiting_key",
})
_MODES = {"managed": "managed", "disabled": "native"}
_FIXED = {"yes", "no", "unknown"}


def _status(path: Path, *, key: str, allow: frozenset[str]) -> str:
    """Read only tiny JSON state, never print untrusted file contents."""
    try:
        if path.is_symlink() or path.stat().st_size > 2048:
            return "unavailable"
        data = json.loads(path.read_bytes())
        value = data.get(key) if isinstance(data, dict) else None
        return value if isinstance(value, str) and value in allow else "unavailable"
    except (OSError, ValueError, TypeError, UnicodeError):
        return "unavailable"


def _ssh_mode(path: Path) -> str:
    try:
        if path.is_symlink() or path.stat().st_size > 2048:
            return "unknown"
        data = json.loads(path.read_bytes())
        return _MODES.get(data.get("vpn_ssh_mode"), "unknown") if isinstance(data, dict) else "unknown"
    except (OSError, ValueError, TypeError, UnicodeError):
        return "unknown"


def _local_banner_probe(timeout: float = 3.0) -> str:
    """Test only local SSH identification; does NOT authenticate."""
    try:
        with socket.create_connection(("127.0.0.1", 22), timeout=timeout) as peer:
            peer.settimeout(timeout)
            received = peer.recv(256)
        if received.startswith(b"SSH-2.0-") or received.startswith(b"SSH-1.99-"):
            return "ssh_identification_ok"
        if not received:
            return "closed_before_identification"
        return "unexpected_identification"
    except socket.timeout:
        return "identification_timeout"
    except (OSError, ValueError):
        return "local_connection_failed"


def _sshd_listening() -> str:
    """Parse 'ss' output in memory; never print addresses/hostnames."""
    try:
        result = subprocess.run(
            ["ss", "-H", "-ltn"], capture_output=True, text=True,
            timeout=4, check=False,
        )
        if result.returncode != 0:
            return "unknown"
        for line in result.stdout.splitlines():
            cols = line.split()
            if len(cols) >= 4 and re.search(r":22$", cols[3]):
                return "yes"
        return "no"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _firewall() -> str:
    """Read iptables chain configuration; no flush, insert or deletion."""
    try:
        status = subprocess.run(
            ["iptables", "-S", "REDETI_VPN_INPUT"],
            capture_output=True, text=True, timeout=4, check=False,
        )
        entry = subprocess.run(
            ["iptables", "-S", "INPUT"],
            capture_output=True, text=True, timeout=4, check=False,
        )
        if status.returncode or entry.returncode:
            return "unavailable"
        rules = status.stdout
        jumps = entry.stdout
        if ("-j REDETI_VPN_INPUT" in jumps and
            "--dport 22" in rules and
            "-j DROP" in rules):
            return "vpn_ssh_rule_present"
        return "vpn_ssh_rule_missing"
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"


def _packaged_banner() -> str:
    try:
        if _BANNER.is_symlink() or _BANNER.stat().st_size > 2048:
            return "missing"
        data = _BANNER.read_bytes()
        return "present" if b"REDETI RECOVERY OS" in data else "missing"
    except OSError:
        return "missing"


def diagnose() -> dict[str, str]:
    return {
        "vpn_state": _status(_STATUS, key="state", allow=_VPN_STATES),
        "vpn_ssh_mode": _ssh_mode(_STATUS),
        "lan_ssh_state": _status(_SSH_STATUS, key="state", allow=_LAN_STATES),
        "sshd_port_22_listening": _sshd_listening(),
        "local_ssh_identification": _local_banner_probe(),
        "vpn_firewall": _firewall(),
        "native_ssh_banner": _packaged_banner(),
    }


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--read-only"]:
        print("BLOCKED: specify --read-only")
        return 2
    for name, value in diagnose().items():
        print(name + "=" + value)
    print("diagnostic_complete=read_only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
