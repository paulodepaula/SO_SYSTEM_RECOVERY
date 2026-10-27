#!/usr/bin/env python3
"""Optional boot agent for the Hermes enrollment client.

No endpoint is configured in the ISO by default. When a reviewed HTTPS URL is
provided by the deployment image, this process keeps the pairing secret and
Tailscale auth key in RAM only. It never prints either value.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from enrollment_client import EnrollmentClient, VpnState, write_status  # noqa: E402

STATUS = Path("/run/redeti/enrollment-status.json")
AUTH_FILE = Path("/run/redeti/ts-authkey")
ENDPOINT_FILE = Path("/etc/redeti/enrollment-url")


def network_available() -> bool:
    try:
        result = subprocess.run(
            ["/usr/bin/ip", "route", "show", "default"],
            check=False, capture_output=True, text=True, timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def safe_status(client: EnrollmentClient) -> None:
    write_status(STATUS, client.status)


def read_endpoint() -> str | None:
    try:
        value = ENDPOINT_FILE.read_text(encoding="ascii").strip()
    except (OSError, UnicodeDecodeError):
        return None
    return value or None


def main() -> int:
    endpoint = read_endpoint()
    if endpoint is None:
        return 0
    try:
        client = EnrollmentClient(endpoint)
    except ValueError:
        return 1
    status = client.start(network_available=network_available())
    safe_status(client)
    while status.state == VpnState.AGUARDANDO_AUTORIZACAO:
        time.sleep(2)
        status = client.poll()
        safe_status(client)
    if status.state != VpnState.AUTORIZADO:
        return 0
    try:
        key = client.claim_auth_key()
        AUTH_FILE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = 0o600
        fd = AUTH_FILE.open("x", encoding="ascii")
        try:
            fd.write(key + "\n")
        finally:
            fd.close()
        AUTH_FILE.chmod(flags)
        # Erase the client-held copy before allowing the VPN consumer to run.
        client.consume_auth_key()
        safe_status(client)
        return 0
    except Exception:
        client.close(reason="claim_failed")
        safe_status(client)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
