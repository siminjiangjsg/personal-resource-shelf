"""Local request boundary and typed validation messages."""

from typing import ClassVar

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, TypeAdapter
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware

from toolbox.storage import LibraryError


class ValidationIssue(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    loc: tuple[str | int, ...]
    msg: str


def install_boundary(app: FastAPI) -> None:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])

    @app.middleware("http")
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        origin = request.headers.get("origin")
        expected = "http://" + request.headers.get("host", "")
        if origin and origin != expected:
            return JSONResponse({"detail": "只接受本机应用页面的请求。"}, status_code=403)
        if request.method in {"POST", "PUT"}:
            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                return JSONResponse({"detail": "请求需要使用 JSON。"}, status_code=415)
            if len(await request.body()) > 16 * 1024 * 1024:
                return JSONResponse({"detail": "文件过大，最多支持 16 MB。"}, status_code=413)
        response = await call_next(request)
        if response.headers.get("content-type") == "application/json":
            response.headers["Content-Type"] = "application/json; charset=utf-8"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if not request.url.path.startswith("/share/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
        return response

    @app.exception_handler(LibraryError)
    def library_error(_request: Request, error: LibraryError) -> JSONResponse:
        return JSONResponse({"detail": str(error)}, status_code=error.status)

    @app.exception_handler(RequestValidationError)
    def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        issues = TypeAdapter(tuple[ValidationIssue, ...]).validate_python(error.errors())
        messages = [
            ".".join(str(part) for part in item.loc[1:]) + ": " + item.msg for item in issues
        ]
        return JSONResponse({"detail": "请检查输入：" + "；".join(messages)}, status_code=422)
