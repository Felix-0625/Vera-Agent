"""Loopback-only protection: foreign Host or Origin headers must not reach any route."""

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(repo_root=tmp_path), base_url="http://127.0.0.1")


def test_cross_site_write_is_refused_before_it_runs(client):
    """A web page must not be able to create state, for example a conversation, through the API."""
    response = client.post("/api/threads", json={"title": "planted"}, headers={"Origin": "https://evil.example"})

    assert response.status_code == 403
    assert client.get("/api/threads").json()["threads"] == []


def test_cross_site_preflight_gets_no_cors_grant(client):
    response = client.options(
        "/api/threads",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 403
    assert "access-control-allow-origin" not in response.headers


def test_dns_rebinding_host_is_refused(client):
    assert client.get("/api/health", headers={"Host": "rebind.evil.example"}).status_code == 400


def test_foreign_websocket_origin_is_closed(client):
    """The terminal WebSocket runs a shell, so a cross-site page must not be able to open it."""
    with (
        pytest.raises(Exception),
        client.websocket_connect("/api/terminal/session", headers={"Origin": "https://evil.example"}),
    ):
        pass


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:8000"])
def test_loopback_origin_keeps_working(client, origin):
    response = client.get("/api/health", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_built_ui_is_served_from_the_same_origin(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<title>ui</title>", encoding="utf-8")
    client = TestClient(create_app(repo_root=tmp_path, frontend_dist=dist), base_url="http://127.0.0.1")
    assert "<title>ui</title>" in client.get("/").text
    assert client.get("/api/health").status_code == 200
