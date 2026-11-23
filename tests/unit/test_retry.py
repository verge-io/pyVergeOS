"""Automatic retries must not send a non-idempotent request twice."""

from __future__ import annotations

import json
import socket
import ssl
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from pyvergeos import VergeClient
from pyvergeos.exceptions import APIError, VergeConnectionError, VergeTimeoutError

Behavior = Callable[[str, str, int], str]

# A TLS alert record written on the raw socket, so the client fails in the
# SSL layer while reading the response instead of seeing an HTTP status.
_BAD_TLS_RECORD = b"\x15\x03\x03\x00\x02\x02\x2a"


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        self._dispatch()

    def do_POST(self) -> None:
        self._dispatch()

    def do_PUT(self) -> None:
        self._dispatch()

    def do_DELETE(self) -> None:
        self._dispatch()

    def do_PATCH(self) -> None:
        self._dispatch()

    def _dispatch(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)
        server = self.server
        assert isinstance(server, _ApiServer)
        path = self.path.split("?", 1)[0]
        server.seen.append((self.command, path))
        attempt = sum(
            1 for method, seen_path in server.seen if method == self.command and seen_path == path
        )
        action = server.behavior(self.command, path, attempt)
        if action == "drop":
            self._drop()
            return
        if action == "corrupt":
            self._corrupt()
            return
        if action == "hold":
            self._hold(server)
            return
        self._send(int(action), path)

    def _drop(self) -> None:
        self.close_connection = True
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            return

    def _corrupt(self) -> None:
        self.close_connection = True
        try:
            socket.socket.sendall(self.connection, _BAD_TLS_RECORD)
            socket.socket.close(self.connection)
        except OSError:
            return

    def _hold(self, server: _ApiServer) -> None:
        self.close_connection = True
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not server.stopping.is_set():
            time.sleep(0.05)

    def _send(self, status: int, path: str) -> None:
        if path.endswith("/system"):
            payload: dict[str, object] = {
                "$key": 1,
                "yb_version": "26.2.2",
                "os_version": "26.2",
                "cloud_name": "test",
            }
        elif status == 200:
            payload = {"ok": True}
        else:
            payload = {"err": "temporary"}
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class _ApiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, certfile: str, keyfile: str, behavior: Behavior) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.seen: list[tuple[str, str]] = []
        self.behavior = behavior
        self.stopping = threading.Event()
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile, keyfile)
        self.socket = context.wrap_socket(self.socket, server_side=True)


def _always(action: str) -> Behavior:
    def behavior(method: str, path: str, attempt: int) -> str:
        del method, attempt
        if path.endswith("/system"):
            return "200"
        return action

    return behavior


def _recover(action: str, suffix: str) -> Behavior:
    def behavior(method: str, path: str, attempt: int) -> str:
        del method
        if path.endswith("/system"):
            return "200"
        if path.endswith(suffix) and attempt == 1:
            return action
        return "200"

    return behavior


@pytest.fixture(scope="module")
def tls_material(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, str]:
    directory = tmp_path_factory.mktemp("retry-tls")
    cert = directory / "cert.pem"
    key = directory / "key.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=127.0.0.1",
            "-addext",
            "subjectAltName=IP:127.0.0.1",
        ],
        check=True,
        capture_output=True,
    )
    return str(cert), str(key)


@contextmanager
def _serve(certfile: str, keyfile: str, behavior: Behavior) -> Iterator[_ApiServer]:
    server = _ApiServer(certfile, keyfile, behavior)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.stopping.set()
        server.shutdown()
        server.server_close()


def _client(server: _ApiServer, *, timeout: int = 1) -> VergeClient:
    host = server.server_address[0]
    port = server.server_address[1]
    return VergeClient(
        host=f"{host}:{port}",
        username="admin",
        password="secret",
        verify_ssl=False,
        timeout=timeout,
        retry_total=3,
        retry_backoff_factor=0,
    )


def _count(server: _ApiServer, method: str, suffix: str) -> int:
    return sum(
        1 for seen_method, path in server.seen if seen_method == method and path.endswith(suffix)
    )


class TestNonIdempotentRequestsAreNotRetried:
    """A POST or PATCH whose reply is lost or late is sent once."""

    @pytest.mark.parametrize("method", ["POST", "PATCH"])
    def test_timeout_is_not_resent(self, tls_material: tuple[str, str], method: str) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _always("hold")) as server:
            client = _client(server)
            try:
                with pytest.raises(VergeTimeoutError):
                    client._request(method, "machine_drives", json_data={"size_gb": 1})
            finally:
                client.disconnect()
            assert _count(server, method, "/machine_drives") == 1

    @pytest.mark.parametrize("method", ["POST", "PATCH"])
    def test_lost_reply_is_not_resent(self, tls_material: tuple[str, str], method: str) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _always("drop")) as server:
            client = _client(server)
            try:
                with pytest.raises(VergeConnectionError):
                    client._request(method, "machine_drives", json_data={"size_gb": 1})
            finally:
                client.disconnect()
            assert _count(server, method, "/machine_drives") == 1

    @pytest.mark.parametrize("method", ["POST", "PATCH"])
    def test_tls_read_error_is_not_resent(self, tls_material: tuple[str, str], method: str) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _always("corrupt")) as server:
            client = _client(server)
            try:
                with pytest.raises(VergeConnectionError):
                    client._request(method, "machine_drives", json_data={"size_gb": 1})
            finally:
                client.disconnect()
            assert _count(server, method, "/machine_drives") == 1

    def test_gateway_timeout_is_not_resent(self, tls_material: tuple[str, str]) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _always("504")) as server:
            client = _client(server)
            try:
                with pytest.raises(APIError) as exc_info:
                    client._request("POST", "machine_drives", json_data={"size_gb": 1})
            finally:
                client.disconnect()
            assert exc_info.value.status_code == 504
            assert _count(server, "POST", "/machine_drives") == 1


class TestIdempotentRequestsAreRetried:
    """GET, PUT, and DELETE are still retried after the same failures."""

    @pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
    def test_status_retry_then_succeeds(self, tls_material: tuple[str, str], method: str) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _recover("503", "/vms")) as server:
            client = _client(server)
            try:
                result = client._request(method, "vms")
            finally:
                client.disconnect()
            assert result == {"ok": True}
            assert _count(server, method, "/vms") == 2

    def test_get_lost_reply_is_retried(self, tls_material: tuple[str, str]) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _recover("drop", "/vms")) as server:
            client = _client(server)
            try:
                result = client._request("GET", "vms")
            finally:
                client.disconnect()
            assert result == {"ok": True}
            assert _count(server, "GET", "/vms") == 2

    def test_get_timeout_is_retried(self, tls_material: tuple[str, str]) -> None:
        certfile, keyfile = tls_material

        def behavior(method: str, path: str, attempt: int) -> str:
            del method
            if path.endswith("/system"):
                return "200"
            if path.endswith("/vms") and attempt == 1:
                return "hold"
            return "200"

        with _serve(certfile, keyfile, behavior) as server:
            client = _client(server)
            try:
                result = client._request("GET", "vms")
            finally:
                client.disconnect()
            assert result == {"ok": True}
            assert _count(server, "GET", "/vms") == 2

    def test_get_tls_read_error_is_retried(self, tls_material: tuple[str, str]) -> None:
        certfile, keyfile = tls_material
        with _serve(certfile, keyfile, _recover("corrupt", "/vms")) as server:
            client = _client(server)
            try:
                result = client._request("GET", "vms")
            finally:
                client.disconnect()
            assert result == {"ok": True}
            assert _count(server, "GET", "/vms") == 2
