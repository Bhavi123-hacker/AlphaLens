"""CLI process health is evidence from HTTP, not merely a running CLI interpreter."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from alphalens_api.operations.health import probe_api


@pytest.mark.parametrize("valid", [True, False])
def test_bounded_actual_loopback_liveness(valid: bool) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"status": "alive", "scope": "foundation_only"}
                    if valid
                    else {"private": "TEST_ONLY"}
                ).encode()
            )

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert probe_api(server.server_port) is valid
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_offline_cli_probe_is_persisted_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from alphalens_api.operations.cli import main

    monkeypatch.setenv("ALPHALENS_OPERATIONS_ROOT", str(tmp_path / "ops"))
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))  # Reserved but no accepting HTTP listener.
        monkeypatch.setenv("ALPHALENS_PORT", str(reserve.getsockname()[1]))
        assert probe_api(reserve.getsockname()[1]) is False
        assert main(["init"]) == 0
        capsys.readouterr()
        assert main(["check"]) == 0
    evidence = json.loads(capsys.readouterr().out)["report"]
    assert evidence["components"]["api"]["status"] == "UNAVAILABLE"
