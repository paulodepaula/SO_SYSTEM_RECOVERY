"""Private UNIX-socket operator channel for the Hermes enrollment broker.

Never bound to TCP. Intended for an authenticated Service Desk backend to
submit short-lived signed approvals after authorization of the technician and
work order. Not deployed and no reverse proxy rule is installed here.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import stat

from .operator_auth import OperatorApprovalVerifier, OperatorAuthError

_ROUTE = re.compile(r"^/v1/operator/sessions/([A-Za-z0-9_-]{24,80})/approve$")
_MAX_BODY = 4096


class _UnixHttpServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False

    def server_close(self) -> None:
        super().server_close()
        # Explicit socket cleanup on shutdown, without symlinks or redirects.
        try:
            os.unlink(self.server_address)
        except FileNotFoundError:
            pass


def _handler(verifier: OperatorApprovalVerifier) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "RecoveryApprovalBroker"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        def address_string(self) -> str:
            return "local"

        def log_message(self, format: str, *args: object) -> None:
            # Never emit route parameters, session codes or signed assertions.
            pass

        def _reply(self, status: int) -> None:
            self.send_response(status)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store, private")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

        def do_POST(self) -> None:
            match = _ROUTE.fullmatch(self.path)
            if match is None:
                self._reply(404)
                return
            if self.headers.get("Transfer-Encoding") is not None:
                self._reply(400)
                return
            length = self.headers.get("Content-Length", "")
            if not length.isascii() or not length.isdigit():
                self._reply(400)
                return
            n = int(length)
            if n < 1 or n > _MAX_BODY:
                self._reply(413)
                return
            if self.headers.get_content_type() != "application/json":
                self._reply(415)
                return
            payload = self.rfile.read(n)
            try:
                parsed = json.loads(payload)
                if (not isinstance(parsed, dict)
                    or set(parsed) != {"assertion"}
                    or not isinstance(parsed["assertion"], str)):
                    raise ValueError("bad body")
                verifier.approve_signed(
                    parsed["assertion"], expected_session_id=match.group(1)
                )
            except (UnicodeError, ValueError, OperatorAuthError):
                self._reply(403)
                return
            self._reply(204)

        def do_GET(self) -> None:
            self._reply(404)

    return Handler


def create_operator_socket_server(
    verifier: OperatorApprovalVerifier, *, directory: str, filename: str = "approval.sock"
) -> _UnixHttpServer:
    """Create a UNIX-only socket in a pre-existing private directory.

    The directory must be owned by the current service user and mode 0700.
    A Service Desk adapter would need an explicitly authorized process user
    or an access proxy within this boundary. No TCP port is opened.
    """
    folder = Path(directory)
    st = os.lstat(folder)
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or (stat.S_IMODE(st.st_mode) & 0o077):
        raise PermissionError("operator socket directory is not private")
    if not re.fullmatch(r"[A-Za-z0-9_-]+\.sock", filename):
        raise ValueError("invalid operator socket name")
    path = folder / filename
    if path.exists() or path.is_symlink():
        raise FileExistsError("operator socket path already in use")
    server = _UnixHttpServer(str(path), _handler(verifier))
    os.chmod(path, 0o600)
    return server
