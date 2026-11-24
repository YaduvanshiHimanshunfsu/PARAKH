"""How FastAPI serves the built frontend (frontend/dist).

Regression tests for a path traversal found during Phase H.0: the SPA route
joined the URL path onto the build directory without containment, so
GET /%2e%2e/%2e%2e/.env returned the .env file (Gemini key, officer password).
"""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.core.middleware import CONTENT_SECURITY_POLICY


@pytest.fixture()
def built_frontend(tmp_path, monkeypatch):
    project = tmp_path / "project"
    dist = project / "frontend" / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>PARAKH</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('ok')", encoding="utf-8")
    (dist / "robots.txt").write_text("User-agent: *", encoding="utf-8")
    (project / ".env").write_text("OFFICER_PASSWORD=secret", encoding="utf-8")
    (project / "frontend" / "package.json").write_text('{"name": "src"}', encoding="utf-8")
    monkeypatch.setattr(main, "_FRONTEND_DIR", dist.resolve())
    monkeypatch.setattr(main, "_INDEX_HTML", dist.resolve() / "index.html")
    return dist


def test_spa_serves_index_assets_and_real_files(built_frontend) -> None:
    client = TestClient(main.create_app())
    assert "PARAKH" in client.get("/").text
    assert "PARAKH" in client.get("/investigate/case/PRK-1").text  # deep link → app shell
    assert client.get("/assets/app.js").text == "console.log('ok')"
    assert client.get("/robots.txt").text == "User-agent: *"


@pytest.mark.parametrize(
    "path",
    [
        "/%2e%2e/%2e%2e/.env",
        "/..%2f..%2f.env",
        "/%2e%2e/package.json",
        "/assets/%2e%2e/%2e%2e/%2e%2e/.env",
        "/%2e%2e%2f%2e%2e%2f.env",
    ],
)
def test_spa_route_never_serves_files_outside_the_build(built_frontend, path) -> None:
    response = TestClient(main.create_app()).get(path)
    assert "OFFICER_PASSWORD" not in response.text
    assert '"name": "src"' not in response.text


def test_unknown_api_paths_are_json_404_not_the_app_shell(built_frontend) -> None:
    client = TestClient(main.create_app())
    response = client.get("/api/v1/no-such-endpoint")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    assert client.get("/api/v1/health").json()["status"] == "ok"


def test_resolve_frontend_file_contains_paths(tmp_path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("s", encoding="utf-8")
    root = tmp_path / "dist"
    assert main.resolve_frontend_file(root, "a.txt") == (root / "a.txt").resolve()
    assert main.resolve_frontend_file(root, "../secret.txt") is None
    assert main.resolve_frontend_file(root, "") is None
    assert main.resolve_frontend_file(root, "missing.js") is None


def test_csp_allows_no_third_party_origins() -> None:
    assert "googleapis" not in CONTENT_SECURITY_POLICY
    assert "gstatic" not in CONTENT_SECURITY_POLICY
    assert "https:" not in CONTENT_SECURITY_POLICY
    assert "script-src 'self';" in CONTENT_SECURITY_POLICY
    assert "font-src 'self';" in CONTENT_SECURITY_POLICY
