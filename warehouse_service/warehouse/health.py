from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """
    Service health check verifying database connectivity.
    """
    db_ok = True
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return JsonResponse(
        {
            "status": "ok" if db_ok else "error",
            "service": "warehouse_service",
            "database": "connected" if db_ok else "disconnected",
        },
        status=status_code,
    )
