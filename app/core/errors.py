"""Consistent API error helpers (PRD §10.9)."""

from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def error_body(
    code: str,
    message: str,
    fields: dict[str, list[str]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or {},
            "request_id": request_id or str(uuid4()),
        }
    }


class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: dict[str, list[str]] | None = None,
    ):
        self.code = code
        self.fields = fields or {}
        self.request_id = str(uuid4())
        super().__init__(
            status_code=status_code,
            detail=error_body(code, message, self.fields, self.request_id),
        )


async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.detail)
