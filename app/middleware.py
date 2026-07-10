import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.config import APP_VERSION

_CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "frame-ancestors 'none';"
)

# When set, only requests forwarded by this specific Front Door instance are accepted.
# Prevents bypassing WAF by hitting the Container App URL directly.
_FRONT_DOOR_ID = os.getenv("AZURE_FRONT_DOOR_ID", "")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.app_version = APP_VERSION

        if _FRONT_DOOR_ID and request.headers.get("X-Azure-FDID") != _FRONT_DOOR_ID:
            return Response("Forbidden", status_code=403)

        response = await call_next(request)
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
