"""Skill catalog building (GitHub tree, descriptions, caches) and installing a pinned Skill bundle from an archive."""

import io
import json
import time
import zipfile

import pytest
from starlette.testclient import TestClient

from vera_agent.server.app import create_app
from vera_agent.server.routes import skill_market
from vera_agent.server.routes import skills as skills_routes

SHA = "a" * 40
SOURCES = {
    "sample": {"repo": "sample/skills", "root": "skills", "label": "Sample"},
    "mapped": {"repo": "mapped/skills", "root": "", "label": "Mapped"},
}


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _upstream(routes: dict[str, bytes]):
    """A fake `urlopen` serving the first route whose key appears in the requested URL."""
    seen: list[str] = []

    def urlopen(request, timeout=None):
        url = request.full_url
        seen.append(url)
        for key, body in routes.items():
            if key in url:
                return _Response(body)
        raise OSError(f"unexpected url {url}")

    urlopen.seen = seen
    return urlopen


def _tree(*paths: str) -> bytes:
    return json.dumps({"tree": [{"path": path, "type": "blob"} for path in paths]}).encode()


def _skill_zip(prefix: str, files: dict[str, bytes], link: str | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(f"skills-{SHA[:7]}/{prefix}/{name}", data)
        if link:
            info = zipfile.ZipInfo(f"skills-{SHA[:7]}/{prefix}/{link}")
            info.external_attr = 0o120777 << 16
            archive.writestr(info, "../../etc/passwd")
    return buffer.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(skills_routes, "_MARKET_CACHE", None)
    monkeypatch.setattr(skills_routes, "SKILL_SOURCES", SOURCES)
    app_root = tmp_path / "app"
    app_root.mkdir()
    test_client = TestClient(create_app(repo_root=app_root), base_url="http://127.0.0.1")
    test_client.app_root = app_root
    return test_client


def _catalog_routes() -> dict[str, bytes]:
    frontmatter = b"---\nname: review\ndescription: >\n  Reviews code\n  carefully\n---\nbody"
    return {
        "sample/skills/commits/main": json.dumps({"sha": SHA}).encode(),
        "mapped/skills/commits/main": json.dumps({"sha": SHA}).encode(),
        "sample/skills/git/trees": _tree("skills/review/SKILL.md", "skills/review/notes.md", "other/x/SKILL.md"),
        "mapped/skills/git/trees": _tree("lint/SKILL.md"),
        f"raw.githubusercontent.com/sample/skills/{SHA}/skills/review/SKILL.md": frontmatter,
    }


def test_catalog_lists_skills_with_descriptions_and_persists_a_cache(client, monkeypatch):
    monkeypatch.setattr(skill_market, "urlopen", _upstream(_catalog_routes()))

    response = client.get("/api/skills/market")

    assert response.status_code == 200
    market = {item["market_id"]: item for item in response.json()["market"]}
    assert set(market) == {"sample:review", "mapped:lint"}  # only <root>/<name>/SKILL.md entries count
    assert market["sample:review"]["description"] == "Reviews code carefully"
    assert market["mapped:lint"]["description"] == "lint（Mapped）"  # fallback when no description is found
    assert market["sample:review"]["commit"] == SHA and "skill_file" not in market["sample:review"]
    assert {source["id"] for source in response.json()["sources"]} == set(SOURCES)
    cache = json.loads((client.app_root / ".agents" / "registries" / "skills-market-cache.json").read_text("utf-8"))
    assert cache["version"] == 2 and len(cache["market"]) == 2


def test_catalog_search_filters_on_name_description_and_category(client, monkeypatch):
    monkeypatch.setattr(skill_market, "urlopen", _upstream(_catalog_routes()))

    names = [item["name"] for item in client.get("/api/skills/market", params={"q": "CAREFULLY"}).json()["market"]]

    assert names == ["review"]


def test_a_fresh_disk_cache_is_served_without_touching_the_network(client, monkeypatch):
    cache_file = client.app_root / ".agents" / "registries" / "skills-market-cache.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    item = {"market_id": "sample:cached", "name": "cached", "description": "d", "category": "Sample", "source": "s"}
    cache_file.write_text(json.dumps({"version": 2, "fetched_at": time.time(), "market": [item]}), encoding="utf-8")
    upstream = _upstream({})
    monkeypatch.setattr(skill_market, "urlopen", upstream)

    response = client.get("/api/skills/market")

    assert response.json()["market"] == [item] and upstream.seen == []


def test_one_unreachable_source_does_not_hide_the_others(client, monkeypatch):
    routes = {key: body for key, body in _catalog_routes().items() if "mapped" not in key}
    monkeypatch.setattr(skill_market, "urlopen", _upstream(routes))

    market = client.get("/api/skills/market").json()["market"]

    assert [item["market_id"] for item in market] == ["sample:review"]


def _install(client, **overrides):
    body = {"name": "x", "source_id": "sample", "source_path": "skills/review", "commit": SHA, **overrides}
    return client.post("/api/skills/install", json=body)


def test_install_writes_the_bundle_next_to_other_skills_and_skips_symlinks(client, monkeypatch):
    archive = _skill_zip("skills/review", {"SKILL.md": b"---\nname: review\n---\n", "ref/a.md": b"a"}, link="evil")
    monkeypatch.setattr(skill_market, "urlopen", _upstream({f"codeload.github.com/sample/skills/zip/{SHA}": archive}))

    response = _install(client)

    assert response.status_code == 200 and response.json()["installed_skill"] == "review"
    installed = client.app_root / ".agents" / "skills" / "review"
    assert (installed / "SKILL.md").is_file() and (installed / "ref" / "a.md").read_bytes() == b"a"
    assert not (installed / "evil").exists()
    assert not list((client.app_root / ".agents" / "skills").glob(".review-*"))  # staging directory is gone


@pytest.mark.parametrize(
    ("overrides", "status", "fragment"),
    [
        ({"source_id": "unknown"}, 400, "Invalid Skill catalog source path"),
        ({"source_path": "skills/../escape"}, 400, "Invalid Skill catalog source path"),
        ({"source_path": "other/review"}, 400, "Invalid Skill catalog source path"),
        ({"commit": "main"}, 400, "full upstream commit SHA"),
    ],
)
def test_install_rejects_unpinned_or_foreign_sources(client, monkeypatch, overrides, status, fragment):
    upstream = _upstream({})
    monkeypatch.setattr(skill_market, "urlopen", upstream)

    response = _install(client, **overrides)

    assert response.status_code == status and fragment in response.json()["error"] and upstream.seen == []


@pytest.mark.parametrize(
    ("files", "fragment"),
    [
        ({"notes.md": b"no skill file"}, "does not contain SKILL.md"),
        ({"SKILL.md": b"x", "big.bin": b"0" * 1_000_001}, "5 MB installation limit"),
        ({"SKILL.md": b"x", **{f"f{i}.md": b"x" for i in range(80)}}, "80-file installation limit"),
    ],
)
def test_install_enforces_size_and_content_limits_and_cleans_up(client, monkeypatch, files, fragment):
    archive = _skill_zip("skills/review", files)
    monkeypatch.setattr(skill_market, "urlopen", _upstream({"codeload.github.com": archive}))

    response = _install(client)

    assert response.status_code == 502 and fragment in response.json()["error"]
    assert not (client.app_root / ".agents" / "skills" / "review").exists()


def test_install_refuses_an_existing_skill_and_an_invalid_archive(client, monkeypatch):
    (client.app_root / ".agents" / "skills" / "review").mkdir(parents=True)
    assert _install(client).status_code == 409

    (client.app_root / ".agents" / "skills" / "review").rmdir()
    monkeypatch.setattr(skill_market, "urlopen", _upstream({"codeload.github.com": b"not a zip"}))
    response = _install(client)
    assert response.status_code == 502 and "invalid archive" in response.json()["error"]


def test_plain_install_writes_a_minimal_skill(client):
    response = client.post("/api/skills/install", json={"name": "plain", "description": "d", "instructions": "# hi"})

    assert response.status_code == 200
    text = (client.app_root / ".agents" / "skills" / "plain" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\nname: plain\ndescription: d\n---") and text.rstrip().endswith("# hi")
    assert client.post("/api/skills/install", json={"name": "bad name!"}).status_code == 400
