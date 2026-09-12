import logging
import time
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("warehouse.interservice")


class WarehouseClientError(Exception):
    """Base exception for Warehouse Client errors."""


class WarehouseConnectionError(WarehouseClientError):
    """Raised when the Warehouse microservice cannot be reached."""


class WarehouseConflictError(WarehouseClientError):
    """Raised on 409 Conflict (e.g. insufficient inventory stock)."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}


class WarehouseAPIError(WarehouseClientError):
    """Raised when Warehouse API responds with non-2xx status code."""

    def __init__(self, message, status_code=None, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class WarehouseClient:
    """
    HTTP REST Client used by Project A (BookShop) to communicate with
    Project B (Warehouse Service) using SimpleJWT authentication.
    """

    CACHE_TOKEN_KEY = "bookshop:warehouse_jwt_access_token"

    def __init__(
        self,
        base_url: str = None,
        username: str = None,
        password: str = None,
        timeout: tuple = (2.0, 5.0),
        max_retries: int = 2,
    ):
        self.base_url = (
            base_url
            or getattr(settings, "WAREHOUSE_SERVICE_URL", "http://127.0.0.1:8001")
        ).rstrip("/")
        self.username = username or getattr(
            settings, "WAREHOUSE_SERVICE_USER", "bookshop_service"
        )
        self.password = password or getattr(
            settings, "WAREHOUSE_SERVICE_PASSWORD", "warehouse_secret_pass_2026"
        )
        self.timeout = timeout
        self.max_retries = max_retries

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieves JWT access token from Redis cache or requests a new one from /api/token/.
        """
        if not force_refresh:
            cached = cache.get(self.CACHE_TOKEN_KEY)
            if cached:
                return cached

        token_url = f"{self.base_url}/api/token/"
        payload = {"username": self.username, "password": self.password}

        try:
            res = requests.post(token_url, json=payload, timeout=self.timeout)
        except requests.RequestException as e:
            logger.error("Failed to connect to Warehouse token endpoint: %s", str(e))
            raise WarehouseConnectionError(
                f"Could not connect to Warehouse at {token_url}: {e}"
            ) from e

        if res.status_code != 200:
            logger.error("Warehouse auth failed (%s): %s", res.status_code, res.text)
            raise WarehouseAPIError(
                f"Failed to obtain JWT token: {res.status_code}",
                status_code=res.status_code,
                details=res.text,
            )

        token_data = res.json()
        access_token = token_data["access"]
        # Cache token for 50 minutes (valid for 60m)
        cache.set(self.CACHE_TOKEN_KEY, access_token, timeout=3000)
        return access_token

    def _request(
        self, method: str, endpoint: str, json_data: dict = None, params: dict = None
    ) -> dict:
        """
        Executes authenticated HTTP request with JWT token, retry on 401, and exponential backoff.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        token = self.get_access_token()

        for attempt in range(1, self.max_retries + 2):
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            try:
                start_time = time.perf_counter()
                res = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params,
                    timeout=self.timeout,
                )
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "Warehouse Client: %s %s -> %s (%.2fms)",
                    method,
                    url,
                    res.status_code,
                    duration_ms,
                )

                # Token expired: refresh and retry once
                if res.status_code == 401 and attempt == 1:
                    logger.info("Warehouse JWT token expired, refreshing...")
                    token = self.get_access_token(force_refresh=True)
                    continue

                if res.status_code == 409:
                    error_data = res.json() if res.content else {}
                    logger.warning("Warehouse conflict: %s", error_data)
                    raise WarehouseConflictError(
                        "Stock conflict detected in warehouse",
                        details=error_data,
                    )

                if res.status_code >= 400:
                    error_data = res.json() if res.content else {}
                    logger.error(
                        "Warehouse API error (%s): %s", res.status_code, error_data
                    )
                    raise WarehouseAPIError(
                        f"Warehouse request failed with status {res.status_code}",
                        status_code=res.status_code,
                        details=error_data,
                    )

                return res.json() if res.content else {}

            except requests.RequestException as e:
                if attempt <= self.max_retries:
                    backoff = 0.2 * (2 ** (attempt - 1))
                    logger.warning(
                        "Warehouse request error (attempt %s/%s). Retrying in %.2fs: %s",
                        attempt,
                        self.max_retries,
                        backoff,
                        str(e),
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "Warehouse connection failed permanently after %s retries: %s",
                        self.max_retries,
                        str(e),
                    )
                    raise WarehouseConnectionError(
                        f"Connection to Warehouse failed: {e}"
                    ) from e

    def check_stock(self, book_id: int) -> dict:
        """
        Queries stock level for a specific book ID.
        """
        return self._request("GET", f"/api/inventory/items/{book_id}/stock/")

    def reserve_stock(
        self, order_id: int, items: list, expires_in_minutes: int = 15
    ) -> dict:
        """
        Reserves warehouse stock for an order during checkout.
        """
        payload = {
            "order_id": order_id,
            "items": items,
            "expires_in_minutes": expires_in_minutes,
        }
        return self._request("POST", "/api/inventory/reserve/", json_data=payload)

    def confirm_sale(self, order_id: int = None, reservation_ids: list = None) -> dict:
        """
        Confirms stock reservation when order payment succeeds.
        """
        payload = {}
        if order_id:
            payload["order_id"] = order_id
        if reservation_ids:
            payload["reservation_ids"] = reservation_ids
        return self._request("POST", "/api/inventory/confirm-sale/", json_data=payload)

    def release_stock(self, order_id: int = None, reservation_ids: list = None) -> dict:
        """
        Releases reserved stock when checkout fails or is abandoned.
        """
        payload = {}
        if order_id:
            payload["order_id"] = order_id
        if reservation_ids:
            payload["reservation_ids"] = reservation_ids
        return self._request("POST", "/api/inventory/release/", json_data=payload)
