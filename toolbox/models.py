"""Validated local records and deliberately separate public share records."""

from datetime import datetime
from typing import Annotated, ClassVar, Literal, NewType
from urllib.parse import urlsplit, urlunsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

ResourceId = NewType("ResourceId", str)
CollectionId = NewType("CollectionId", str)
MAX_PORT = 65535
HTTPS_PORT = 443
HTTP_PORT = 80


def web_url(value: str) -> str:
    """Keep the original URL, including meaningful query strings and fragments."""
    value = value.strip()
    try:
        parts = urlsplit(value)
        valid = parts.scheme in {"http", "https"} and bool(parts.hostname)
        valid = valid and not parts.username and not parts.password
        valid = valid and (parts.port is None or 0 < parts.port <= MAX_PORT)
    except ValueError as error:
        raise PydanticCustomError("web_url", "请输入有效的网页链接") from error
    if not valid or any(character.isspace() for character in value):
        raise PydanticCustomError("web_url", "请使用完整的 http:// 或 https:// 链接")
    return value


WebUrl = Annotated[str, Field(min_length=1, max_length=8192), AfterValidator(web_url)]
Tag = Annotated[str, Field(min_length=1, max_length=60)]


def url_key(url: str) -> str:
    parts = urlsplit(url)
    netloc = parts.netloc.casefold()
    if (parts.scheme == "https" and parts.port == HTTPS_PORT) or (
        parts.scheme == "http" and parts.port == HTTP_PORT
    ):
        netloc = netloc.rsplit(":", 1)[0]
    return urlunsplit(
        (parts.scheme.casefold(), netloc, parts.path or "/", parts.query, parts.fragment)
    )


class Model(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        str_strip_whitespace=True,
    )


class ResourceDraft(Model):
    url: WebUrl
    title: str = Field(default="", max_length=300)
    kind: Literal["网页", "工具", "Skill", "MCP", "文章", "教程", "文档", "资源合集"] = "网页"
    category: str = Field(default="", max_length=80)
    tags: tuple[Tag, ...] = Field(default=(), max_length=30)
    description: str = Field(default="", max_length=2000)
    note: str = Field(default="", max_length=20000)
    status: Literal["待看", "已看", "已用"] = "待看"
    inbox: bool = True
    archived: bool = False

    @field_validator("tags")
    @classmethod
    def unique_tags(cls, tags: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(tags))


class Resource(ResourceDraft):
    id: ResourceId
    source: str
    created_at: datetime
    updated_at: datetime


class ShareItem(Model):
    resource_id: ResourceId
    title: str = Field(min_length=1, max_length=300)
    url: WebUrl
    recommendation: str = Field(default="", max_length=4000)
    tags: tuple[Tag, ...] = Field(default=(), max_length=30)


class CollectionDraft(Model):
    title: str = Field(min_length=1, max_length=160)
    show_tags: bool = False
    items: tuple[ShareItem, ...] = Field(min_length=1, max_length=500)


class Collection(CollectionDraft):
    id: CollectionId
    created_at: datetime
    updated_at: datetime


class LibraryState(Model):
    resources: tuple[Resource, ...]
    collections: tuple[Collection, ...]


class LibraryBackup(LibraryState):
    format: Literal["personal-resource-shelf"] = "personal-resource-shelf"
    version: Literal[1] = 1
    exported_at: datetime


class RestoreResult(Model):
    added_resources: int
    added_collections: int
    skipped_resources: int


class AppInfo(Model):
    app: Literal["personal-resource-shelf"] = "personal-resource-shelf"
    version: Literal["1.0.0"] = "1.0.0"
    data_path: str
