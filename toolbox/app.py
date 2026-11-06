"""Loopback-only HTTP API and static application."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from toolbox.models import (
    AppInfo,
    Collection,
    CollectionDraft,
    CollectionId,
    LibraryBackup,
    LibraryState,
    Resource,
    ResourceDraft,
    ResourceId,
    RestoreResult,
)
from toolbox.security import install_boundary
from toolbox.sharing import download_headers, share_html, share_markdown
from toolbox.storage import LibraryStore


def create_app(data_dir: Path) -> FastAPI:  # noqa: C901 -- Counts simple endpoint registrations.
    """Bind a local data directory without global mutable state."""
    store = LibraryStore(data_dir)
    app = FastAPI(title="我的工具箱", docs_url=None, redoc_url=None, openapi_url=None)
    install_boundary(app)

    @app.get("/api/info")
    def info() -> AppInfo:
        return AppInfo(data_path=str(store.path.resolve()))

    @app.get("/api/state")
    def state() -> LibraryState:
        return store.state()

    @app.post("/api/resources", status_code=201)
    def add_resource(draft: ResourceDraft) -> Resource:
        return store.save_resource(draft)

    @app.put("/api/resources/{resource_id}")
    def edit_resource(resource_id: ResourceId, draft: ResourceDraft) -> Resource:
        return store.save_resource(draft, resource_id)

    @app.post("/api/collections", status_code=201)
    def add_collection(draft: CollectionDraft) -> Collection:
        return store.save_collection(draft)

    @app.put("/api/collections/{collection_id}")
    def edit_collection(collection_id: CollectionId, draft: CollectionDraft) -> Collection:
        return store.save_collection(draft, collection_id)

    @app.get("/api/collections/{collection_id}/html")
    def export_html(collection_id: CollectionId) -> HTMLResponse:
        collection = store.collection(collection_id)
        return HTMLResponse(share_html(collection), headers=download_headers("资源清单.html"))

    @app.get("/api/collections/{collection_id}/markdown")
    def export_markdown(collection_id: CollectionId) -> Response:
        collection = store.collection(collection_id)
        return Response(
            share_markdown(collection),
            media_type="text/markdown; charset=utf-8",
            headers=download_headers("资源清单.md"),
        )

    @app.get("/share/{collection_id}")
    def preview(collection_id: CollectionId) -> HTMLResponse:
        return HTMLResponse(share_html(store.collection(collection_id)))

    @app.get("/api/backup")
    def backup() -> Response:
        return Response(
            store.backup().model_dump_json(indent=2),
            media_type="application/json",
            headers=download_headers("我的工具箱-完整备份.json"),
        )

    @app.post("/api/restore")
    def restore(data: LibraryBackup) -> RestoreResult:
        return store.restore(data)

    web = Path(__file__).resolve().parent.parent / "web"
    if web.exists():

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(web / "index.html")

        app.mount("/assets", StaticFiles(directory=web), name="assets")
    return app
