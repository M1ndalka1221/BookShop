from typing import Any
from django.http import JsonResponse, HttpRequest
from django.db import connection
from django.core.cache import cache


def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint to inspect PostgreSQL and Redis/cache health.
    Returns HTTP 200 if all components are healthy, or HTTP 503 if any check fails.
    """
    components: dict[str, str] = {}
    is_healthy = True

    # 1. Database connectivity check
    try:
        connection.ensure_connection()
        components["database"] = "ok"
    except Exception as e:
        components["database"] = f"error: {str(e)}"
        is_healthy = False

    # 2. Redis / Cache connectivity check
    try:
        cache.set("_health_check", "1", timeout=5)
        val = cache.get("_health_check")
        if val is not None:
            components["cache"] = "ok"
        else:
            components["cache"] = "error: cache read failed"
            is_healthy = False
    except Exception as e:
        components["cache"] = f"error: {str(e)}"
        is_healthy = False

    status_code = 200 if is_healthy else 503
    payload: dict[str, Any] = {
        "status": "healthy" if is_healthy else "unhealthy",
        "components": components,
    }

    return JsonResponse(payload, status=status_code)
