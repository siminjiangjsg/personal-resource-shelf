from pathlib import Path

from fastapi.testclient import TestClient

from toolbox.app import create_app


def client_at(path: Path) -> TestClient:
    return TestClient(create_app(path), base_url="http://127.0.0.1:8765")


def test_save_survives_application_restart(tmp_path: Path) -> None:
    # Given an empty on-disk library.
    client = client_at(tmp_path)
    # When a link with a meaningful fragment is saved and the app restarts.
    saved = client.post("/api/resources", json={"url": "https://example.com/guide?a=1#chapter2"})
    # Then the exact link remains present in the new application instance.
    assert saved.status_code == 201
    restarted = client_at(tmp_path)
    resources = restarted.get("/api/state").json()["resources"]
    assert resources[0]["url"] == "https://example.com/guide?a=1#chapter2"


def test_duplicate_url_does_not_overwrite_notes(tmp_path: Path) -> None:
    # Given an existing resource with a private note.
    client = client_at(tmp_path)
    client.post("/api/resources", json={"url": "https://EXAMPLE.com", "note": "保留这条笔记"})
    # When the equivalent root URL is collected again.
    result = client.post("/api/resources", json={"url": "https://example.com/"})
    # Then duplicate collection is rejected without overwriting the record.
    assert result.status_code == 409
    assert client.get("/api/state").json()["resources"][0]["note"] == "保留这条笔记"


def test_invalid_url_is_rejected(tmp_path: Path) -> None:
    # Given a local library.
    client = client_at(tmp_path)
    # When a non-web URL is submitted.
    result = client.post("/api/resources", json={"url": "javascript:alert(1)"})
    # Then no resource is created.
    assert result.status_code == 422
    assert client.get("/api/state").json()["resources"] == []


def test_edit_category_tags_and_archive(tmp_path: Path) -> None:
    # Given a saved resource.
    client = client_at(tmp_path)
    resource = client.post("/api/resources", json={"url": "https://example.com/tool"}).json()
    # When its classification is edited and it is archived.
    updated = client.put(
        "/api/resources/" + resource["id"],
        json={
            "url": resource["url"],
            "title": "科研工具",
            "kind": "Skill",
            "category": "科研",
            "tags": ["写作", "写作", "自动化"],
            "note": "私人内容",
            "status": "已用",
            "inbox": False,
            "archived": True,
        },
    )
    # Then the persisted record contains the requested values and deduplicated tags.
    assert updated.status_code == 200
    stored = client.get("/api/state").json()["resources"][0]
    assert (stored["category"], stored["kind"], stored["archived"]) == ("科研", "Skill", True)
    assert stored["tags"] == ["写作", "自动化"]


def test_backup_merge_preserves_existing_records(tmp_path: Path) -> None:
    # Given a backup and a separate library with a newer copy of one URL.
    source = client_at(tmp_path / "source")
    source.post("/api/resources", json={"url": "https://example.com/a", "note": "旧笔记"})
    source.post("/api/resources", json={"url": "https://example.com/b"})
    backup = source.get("/api/backup").json()
    target = client_at(tmp_path / "target")
    target.post("/api/resources", json={"url": "https://example.com/a", "note": "新笔记"})
    # When the backup is merged.
    result = target.post("/api/restore", json=backup)
    # Then only the missing URL is inserted and the newer note is retained.
    assert result.status_code == 200
    resources = target.get("/api/state").json()["resources"]
    assert len(resources) == 2
    assert next(item["note"] for item in resources if item["url"].endswith("/a")) == "新笔记"


def test_foreign_origin_cannot_modify_library(tmp_path: Path) -> None:
    # Given an app that only accepts its own browser origin.
    client = client_at(tmp_path)
    # When another web page submits a request to the loopback app.
    result = client.post(
        "/api/resources",
        json={"url": "https://example.com"},
        headers={"Origin": "https://unrelated.example"},
    )
    # Then the request is rejected.
    assert result.status_code == 403


def test_info_declares_utf8_for_windows_launcher(tmp_path: Path) -> None:
    # Given a library inside a Chinese-named directory.
    client = client_at(tmp_path / "中文资料")
    # When Windows PowerShell reads its readiness response.
    response = client.get("/api/info")
    # Then the declared encoding preserves the path used for instance matching.
    assert "charset=utf-8" in response.headers["content-type"]
