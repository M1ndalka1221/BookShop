import time
import logging

logger = logging.getLogger('performance')


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        logger.info(
            f"[{request.method}] {request.path} | Status: {response.status_code} | Time: {duration:.2f}ms"
        )
        return response