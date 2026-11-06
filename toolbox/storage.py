"""SQLite persistence. Every write is a short, atomic transaction."""

import sqlite3
from collections.abc import Generator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from pydantic import TypeAdapter

from toolbox.models import (
    Collection,
    CollectionDraft,
    CollectionId,
    LibraryBackup,
    LibraryState,
    Resource,
    ResourceDraft,
    ResourceId,
    RestoreResult,
    url_key,
)

ROWS: Final = TypeAdapter(tuple[tuple[str], ...])


class LibraryError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status: int = status


def payloads(
    connection: sqlite3.Connection, query: str, parameters: tuple[str, ...] = ()
) -> tuple[str, ...]:
    rows = ROWS.validate_python(connection.execute(query, parameters).fetchall())
    return tuple(row[0] for row in rows)


@dataclass(frozen=True, slots=True)
class LibraryStore:
    directory: Path

    def __post_init__(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.executescript(
                "CREATE TABLE IF NOT EXISTS resources "
                "(id TEXT PRIMARY KEY, url_key TEXT UNIQUE NOT NULL, data TEXT NOT NULL);"
                "CREATE TABLE IF NOT EXISTS collections (id TEXT PRIMARY KEY, data TEXT NOT NULL);"
                "PRAGMA user_version=1;"
            )

    @property
    def path(self) -> Path:
        return self.directory / "library.sqlite3"

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection]:
        with closing(sqlite3.connect(self.path, timeout=10)) as connection, connection:
            yield connection

    def state(self) -> LibraryState:
        with self.connection() as connection:
            resources = payloads(connection, "SELECT data FROM resources ORDER BY rowid DESC")
            collections = payloads(connection, "SELECT data FROM collections ORDER BY rowid DESC")
        return LibraryState(
            resources=tuple(Resource.model_validate_json(data) for data in resources),
            collections=tuple(Collection.model_validate_json(data) for data in collections),
        )

    def resource(self, resource_id: ResourceId) -> Resource:
        with self.connection() as connection:
            records = payloads(connection, "SELECT data FROM resources WHERE id=?", (resource_id,))
        if not records:
            raise LibraryError("这个资源已不存在，请刷新列表。", 404)
        return Resource.model_validate_json(records[0])

    def save_resource(
        self, draft: ResourceDraft, resource_id: ResourceId | None = None
    ) -> Resource:
        previous = self.resource(resource_id) if resource_id else None
        now = datetime.now(UTC)
        parts = urlsplit(draft.url)
        source = "GitHub" if parts.hostname in {"github.com", "www.github.com"} else parts.hostname
        title = draft.title or unquote(parts.path.rstrip("/").split("/")[-1]) or parts.netloc
        record = Resource(
            id=resource_id or ResourceId(uuid4().hex),
            url=draft.url,
            title=title[:300],
            source=source or parts.netloc,
            kind=draft.kind,
            category=draft.category,
            tags=draft.tags,
            description=draft.description,
            note=draft.note,
            status=draft.status,
            inbox=draft.inbox,
            archived=draft.archived,
            created_at=previous.created_at if previous else now,
            updated_at=now,
        )
        try:
            with self.connection() as connection:
                connection.execute(
                    "INSERT INTO resources(id,url_key,data) VALUES(?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET url_key=excluded.url_key,data=excluded.data",
                    (record.id, url_key(record.url), record.model_dump_json()),
                )
        except sqlite3.IntegrityError as error:
            raise LibraryError("链接已收藏，原记录未改动。", 409) from error
        return record

    def collection(self, collection_id: CollectionId) -> Collection:
        with self.connection() as connection:
            records = payloads(
                connection, "SELECT data FROM collections WHERE id=?", (collection_id,)
            )
        if not records:
            raise LibraryError("这个分享清单已不存在。", 404)
        return Collection.model_validate_json(records[0])

    def save_collection(
        self, draft: CollectionDraft, collection_id: CollectionId | None = None
    ) -> Collection:
        previous = self.collection(collection_id) if collection_id else None
        now = datetime.now(UTC)
        record = Collection(
            id=collection_id or CollectionId(uuid4().hex),
            title=draft.title,
            show_tags=draft.show_tags,
            items=draft.items,
            created_at=previous.created_at if previous else now,
            updated_at=now,
        )
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO collections(id,data) VALUES(?,?) "
                "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (record.id, record.model_dump_json()),
            )
        return record

    def backup(self) -> LibraryBackup:
        state = self.state()
        return LibraryBackup(
            resources=state.resources,
            collections=state.collections,
            exported_at=datetime.now(UTC),
        )

    def restore(self, backup: LibraryBackup) -> RestoreResult:
        """Merge missing records; retain the current library and a pre-restore backup."""
        current = self.backup()
        backup_dir = self.directory / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_file = backup_dir / ("before-restore-" + uuid4().hex + ".json")
        backup_file.write_text(current.model_dump_json(indent=2), encoding="utf-8")
        by_url = {url_key(record.url): record.id for record in current.resources}
        ids = {record.id for record in current.resources}
        collection_ids = {record.id for record in current.collections}
        mapping: dict[ResourceId, ResourceId] = {}
        added_resources = added_collections = 0
        with self.connection() as connection:
            for record in backup.resources:
                key = url_key(record.url)
                if key in by_url:
                    mapping[record.id] = by_url[key]
                    continue
                new_id = ResourceId(uuid4().hex) if record.id in ids else record.id
                restored = record.model_copy(update={"id": new_id})
                connection.execute(
                    "INSERT INTO resources VALUES(?,?,?)", (new_id, key, restored.model_dump_json())
                )
                mapping[record.id] = new_id
                by_url[key] = new_id
                ids.add(new_id)
                added_resources += 1
            for collection in backup.collections:
                if collection.id in collection_ids:
                    continue
                items = tuple(
                    item.model_copy(
                        update={
                            "resource_id": mapping.get(item.resource_id, item.resource_id),
                        }
                    )
                    for item in collection.items
                )
                restored_collection = collection.model_copy(update={"items": items})
                connection.execute(
                    "INSERT INTO collections VALUES(?,?)",
                    (collection.id, restored_collection.model_dump_json()),
                )
                collection_ids.add(collection.id)
                added_collections += 1
        return RestoreResult(
            added_resources=added_resources,
            added_collections=added_collections,
            skipped_resources=len(backup.resources) - added_resources,
        )
