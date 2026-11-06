from pathlib import Path

from fastapi.testclient import TestClient

from toolbox.app import create_app


def test_share_export_contains_only_selected_public_fields(tmp_path: Path) -> None:
    # Given selected and unselected records with private fields.
    client = TestClient(create_app(tmp_path), base_url="http://127.0.0.1:8765")
    selected = client.post(
        "/api/resources",
        json={
            "url": "https://example.com/selected#part",
            "title": "<script>alert(1)</script>",
            "note": "PRIVATE_SENTINEL",
            "tags": ["HIDDEN_TAG"],
            "status": "已用",
        },
    ).json()
    client.post("/api/resources", json={"url": "https://example.com/unselected"})
    # When a share snapshot with explicitly public fields is exported.
    shared = client.post(
        "/api/collections",
        json={
            "title": "精选清单",
            "show_tags": False,
            "items": [
                {
                    "resource_id": selected["id"],
                    "url": selected["url"],
                    "title": selected["title"],
                    "recommendation": "公开推荐语",
                    "tags": selected["tags"],
                }
            ],
        },
    )
    assert shared.status_code == 201
    collection_id = shared.json()["id"]
    html = client.get("/api/collections/" + collection_id + "/html").text
    markdown = client.get("/api/collections/" + collection_id + "/markdown").text
    # Then both exports exclude private/unselected content and HTML is escaped.
    for text in (html, markdown):
        assert "PRIVATE_SENTINEL" not in text
        assert "unselected" not in text
        assert "HIDDEN_TAG" not in text
        assert "公开推荐语" in text
    assert "<script>alert(1)</script>" not in html
    assert 'href="https://example.com/selected#part"' in html


def test_collection_remains_a_snapshot_after_resource_edit(tmp_path: Path) -> None:
    # Given a saved collection snapshot.
    client = TestClient(create_app(tmp_path), base_url="http://127.0.0.1:8765")
    resource = client.post(
        "/api/resources",
        json={
            "url": "https://example.com/original",
            "title": "原始标题",
        },
    ).json()
    collection = client.post(
        "/api/collections",
        json={
            "title": "清单",
            "items": [
                {"resource_id": resource["id"], "title": resource["title"], "url": resource["url"]}
            ],
        },
    ).json()
    # When the private resource changes.
    client.put(
        "/api/resources/" + resource["id"],
        json={
            "url": "https://example.com/changed",
            "title": "后来的标题",
        },
    )
    # Then exported snapshot content stays unchanged.
    exported = client.get("/api/collections/" + collection["id"] + "/html").text
    assert "原始标题" in exported
    assert "后来的标题" not in exported
    assert "https://example.com/original" in exported


def test_public_schema_rejects_private_field_injection(tmp_path: Path) -> None:
    # Given a collection payload with an extra private field.
    client = TestClient(create_app(tmp_path), base_url="http://127.0.0.1:8765")
    payload = {
        "title": "清单",
        "items": [
            {
                "resource_id": "x",
                "title": "资源",
                "url": "https://example.com",
                "note": "PRIVATE",
            }
        ],
    }
    # When submitted to the public snapshot API.
    result = client.post("/api/collections", json=payload)
    # Then the extra field is refused.
    assert result.status_code == 422
