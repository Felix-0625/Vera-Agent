"""The terminal WebSocket: working-directory checks, and a real shell round trip when PowerShell exists."""

import shutil

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from vera_agent.server.app import create_app

HAS_POWERSHELL = bool(shutil.which("powershell.exe") or shutil.which("pwsh.exe"))


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(repo_root=tmp_path), base_url="http://127.0.0.1")


def test_unknown_project_is_closed_with_a_reason(client):
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect("/api/terminal/session?project_id=nope"),
    ):
        pass
    assert closed.value.code == 4404


def test_unknown_group_is_closed_with_a_reason(client):
    with pytest.raises(WebSocketDisconnect) as closed, client.websocket_connect("/api/terminal/session?group_id=nope"):
        pass
    assert closed.value.code == 4404


@pytest.mark.skipif(not HAS_POWERSHELL, reason="PowerShell is not installed")
def test_shell_runs_a_command_in_the_project_directory(client, tmp_path):
    with client.websocket_connect("/api/terminal/session") as socket:
        connected = socket.receive_json()
        assert connected["type"] == "connected" and connected["cwd"] == str(tmp_path.resolve())

        socket.send_json({"type": "input", "data": "Write-Output ('vera-' + 'terminal-ok')"})
        # End the shell ourselves: TestClient cancels the server task the moment the test leaves the
        # `with` block, which would race the server's cleanup and leave a PowerShell process behind.
        socket.send_json({"type": "input", "data": "exit"})
        received = ""
        for _ in range(500):
            message = socket.receive_json()
            if message["type"] == "output":
                received += message["data"]
            elif message["type"] == "exit":
                break
        assert "vera-terminal-ok" in received
        assert message == {"type": "exit", "exit_code": 0}
