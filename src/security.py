from __future__ import annotations

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from src.config import get_settings


_PUBLIC_PATHS = {"/health", "/health/ready"}


async def api_auth_middleware(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    settings = get_settings()
    if not settings.is_production:
        return await call_next(request)

    expected = settings.api_auth_token
    if not expected:
        return JSONResponse(
            status_code=503,
            content={"detail": "API authentication is not configured"},
        )

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentication required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(token, expected):
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid authentication credentials"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await call_next(request)


__all__ = ["api_auth_middleware"]
