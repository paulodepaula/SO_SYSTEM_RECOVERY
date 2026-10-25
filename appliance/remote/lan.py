"""Local SSH key and LAN scope helpers (no disk writes or mounts)."""
from __future__ import annotations
import base64
import ipaddress
import json
import re
import subprocess
import sys
from pathlib import Path

RFC1918 = [ipaddress.ip_network(item) for item in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
)]
EXCLUDE_PREFIX = ("tailscale", "wg", "tun", "tap", "docker", "br-", "veth", "virbr", "lo", "zt")

def local_networks(interfaces):
    """Only directly attached ethernet/Wi-Fi interfaces on RFC1918 subnets."""
    items = []
    for interface in interfaces:
        ifname = interface.get("ifname", "")
        if (not re.fullmatch(r"[A-Za-z0-9_.-]{1,15}", ifname)
            or ifname.startswith(EXCLUDE_PREFIX)
            or interface.get("operstate") == "DOWN"):
            continue
        for addr in interface.get("addr_info") or []:
            if addr.get("family") != "inet" or addr.get("scope") != "global":
                continue
            try:
                ip = ipaddress.ip_address(addr["local"])
                prefix = int(addr["prefixlen"])
                network = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
            except (ValueError, TypeError, KeyError):
                continue
            if ip.version != 4:
                continue
            if not any(network.subnet_of(parent) for parent in RFC1918):
                continue
            entry = (ifname, str(network), str(ip))
            if entry not in items:
                items.append(entry)
    return items


def valid_keys(data: bytes) -> bytes:
    """Allow only ed25519 public keys, never an authorized_keys options line."""
    if len(data) > 8192:
        raise ValueError("authorized_keys is too large")
    lines = [s.strip() for s in data.decode("ascii").splitlines() if s.strip()]
    if not 1 <= len(lines) <= 4:
        raise ValueError("expected between one and four SSH public keys")
    validated = []
    for line in lines:
        parts = line.split()
        if len(parts) < 2 or parts[0] != "ssh-ed25519":
            raise ValueError("only ssh-ed25519 keys without options are accepted")
        raw = base64.b64decode(parts[1], validate=True)
        if len(raw) != 51 or raw[:15] != b"\x00\x00\x00\x0bssh-ed25519":
            raise ValueError("invalid Ed25519 SSH key payload")
        validated.append((parts[0] + " " + parts[1]).encode("ascii"))
    return b"\n".join(validated) + b"\n"


def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] == "networks":
        try:
            p = subprocess.run(["ip", "-j", "-4", "addr", "show"], capture_output=True,
                               text=True, timeout=10, check=True)
            interfaces = json.loads(p.stdout)
        except (OSError, ValueError, subprocess.SubprocessError):
            return 2
        for name, network, ip in local_networks(interfaces):
            print(name, network, ip, sep="\t")
        return 0
    if len(sys.argv) == 4 and sys.argv[1] == "install-key":
        src, dst = (Path(s) for s in sys.argv[2:])
        if src.is_symlink() or not src.is_file():
            return 2
        try:
            content = valid_keys(src.read_bytes())
        except (UnicodeDecodeError, ValueError):
            return 2
        dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        import os
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(content)
        return 0
    print("usage: lan.py networks | install-key SOURCE DEST", file=sys.stderr)
    return 2

if __name__ == "__main__":
    sys.exit(main())
