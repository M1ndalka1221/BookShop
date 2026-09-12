import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger("warehouse")


def custom_exception_handler(exc, context):
    """
    Standardized JSON exception handler for Warehouse API.
    """
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "error": True,
            "status_code": response.status_code,
            "detail": response.data,
        }
        response.data = custom_data
    else:
        logger.exception("Unhandled server exception: %s", str(exc))
        response = Response(
            {
                "error": True,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "detail": "Internal server error occurred.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return response
