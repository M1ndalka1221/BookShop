from unittest.mock import patch, MagicMock
import requests
import pytest
from django.core.cache import cache
from catalog.warehouse_client import (
    WarehouseClient,
    WarehouseConnectionError,
    WarehouseConflictError,
    WarehouseAPIError,
)


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client():
    return WarehouseClient(
        base_url="http://mock-warehouse:8001",
        username="test_svc",
        password="test_password",
        timeout=(0.1, 0.1),
        max_retries=1,
    )


def test_get_access_token_and_cache(client):
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"access": "token_abc_123", "refresh": "ref_456"}
        mock_post.return_value = mock_resp

        token = client.get_access_token()
        assert token == "token_abc_123"
        assert mock_post.call_count == 1

        # Second call should read from cache without hitting requests.post
        token_cached = client.get_access_token()
        assert token_cached == "token_abc_123"
        assert mock_post.call_count == 1


def test_check_stock_success(client):
    with patch("catalog.warehouse_client.WarehouseClient.get_access_token", return_value="mock_jwt"):
        with patch("requests.request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b'{"available_stock": 25}'
            mock_resp.json.return_value = {"available_stock": 25}
            mock_req.return_value = mock_resp

            data = client.check_stock(book_id=42)
            assert data["available_stock"] == 25
            mock_req.assert_called_once()
            args, kwargs = mock_req.call_args
            assert kwargs["headers"]["Authorization"] == "Bearer mock_jwt"


def test_reserve_stock_conflict_raises_exception(client):
    with patch("catalog.warehouse_client.WarehouseClient.get_access_token", return_value="mock_jwt"):
        with patch("requests.request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 409
            mock_resp.content = b'{"error": true, "code": "INSUFFICIENT_STOCK"}'
            mock_resp.json.return_value = {"error": True, "code": "INSUFFICIENT_STOCK"}
            mock_req.return_value = mock_resp

            with pytest.raises(WarehouseConflictError) as exc_info:
                client.reserve_stock(order_id=5, items=[{"book_id": 42, "quantity": 100}])

            assert exc_info.value.details["code"] == "INSUFFICIENT_STOCK"


def test_request_token_expired_retries_with_new_token(client):
    token_counter = [0]

    def mock_get_token(force_refresh=False):
        token_counter[0] += 1
        return f"token_v{token_counter[0]}"

    with patch.object(client, "get_access_token", side_effect=mock_get_token):
        with patch("requests.request") as mock_req:
            # First request returns 401 Unauthorized, second returns 200 OK
            resp_401 = MagicMock(status_code=401, content=b'{"detail": "token expired"}')
            resp_200 = MagicMock(status_code=200, content=b'{"status": "CONFIRMED"}', json=lambda: {"status": "CONFIRMED"})
            mock_req.side_effect = [resp_401, resp_200]

            res = client.confirm_sale(order_id=10)
            assert res["status"] == "CONFIRMED"
            assert mock_req.call_count == 2


def test_connection_error_and_retry(client):
    with patch("catalog.warehouse_client.WarehouseClient.get_access_token", return_value="mock_jwt"):
        with patch("requests.request", side_effect=requests.ConnectionError("Connection refused")):
            with pytest.raises(WarehouseConnectionError):
                client.release_stock(order_id=12)


def test_server_error_raises_api_error(client):
    with patch("catalog.warehouse_client.WarehouseClient.get_access_token", return_value="mock_jwt"):
        with patch("requests.request") as mock_req:
            mock_resp = MagicMock(status_code=500, content=b'{"detail": "Server error"}', json=lambda: {"detail": "Server error"})
            mock_req.return_value = mock_resp

            with pytest.raises(WarehouseAPIError) as exc_info:
                client.check_stock(1)
            assert exc_info.value.status_code == 500
