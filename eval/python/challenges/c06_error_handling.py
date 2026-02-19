"""
CHALLENGE: Resilient HTTP Client Wrapper
CATEGORY: error_handling
DIFFICULTY: 2
POINTS: 10
WHY: Models either swallow exceptions or let everything propagate raw. They rarely implement
     proper retry logic, timeout handling, or error classification. Production HTTP clients
     need all three, and models consistently miss at least one.
"""

PROMPT = """
Write a resilient HTTP client wrapper that handles retries, timeouts, and error classification.

```python
from dataclasses import dataclass
from enum import Enum

class ErrorCategory(Enum):
    TRANSIENT = "transient"       # Retry-able: 429, 500, 502, 503, 504, connection errors
    CLIENT = "client"             # Not retry-able: 400, 401, 403, 404, 405, 422
    FATAL = "fatal"               # Should not retry: anything else unexpected

@dataclass
class APIResponse:
    status_code: int
    body: dict | None
    headers: dict
    attempts: int                 # How many attempts were made (1 = no retries)

class APIError(Exception):
    def __init__(self, message: str, category: ErrorCategory, status_code: int | None = None,
                 attempts: int = 1, cause: Exception | None = None):
        super().__init__(message)
        self.category = category
        self.status_code = status_code
        self.attempts = attempts
        self.cause = cause

class ResilientClient:
    def __init__(self, base_url: str, max_retries: int = 3,
                 base_delay: float = 0.1, timeout: float = 5.0):
        \"\"\"
        Args:
            base_url: Base URL for all requests
            max_retries: Max retry attempts for transient errors (total attempts = max_retries + 1)
            base_delay: Base delay in seconds for exponential backoff (delay = base_delay * 2^attempt)
            timeout: Request timeout in seconds
        \"\"\"

    def request(self, method: str, path: str, **kwargs) -> APIResponse:
        \"\"\"
        Make an HTTP request with retries for transient errors.
        - Retries only on TRANSIENT errors (429, 500, 502, 503, 504, connection errors)
        - Uses exponential backoff between retries
        - For 429 responses, respects Retry-After header if present (as seconds)
        - Raises APIError with correct category for non-transient errors
        - Raises APIError with category=TRANSIENT after exhausting all retries
        - kwargs are passed through to the underlying HTTP library
        \"\"\"
```

Requirements:
- Use the `requests` library for HTTP calls
- Classify connection errors (ConnectionError, Timeout) as TRANSIENT
- Include the original exception as `cause` in APIError
- The `attempts` field in both APIResponse and APIError reflects total attempts made
- Never retry CLIENT errors (400-level except 429)
"""

# --- Tests (model never sees below this line) ---

import pytest
import importlib
from unittest.mock import patch, MagicMock
import requests


def load():
    mod = importlib.import_module("solutions.c06_error_handling")
    return mod.ResilientClient, mod.APIError, mod.ErrorCategory, mod.APIResponse


class TestSuccessPath:
    """2 points."""

    def test_successful_request(self):
        """(1 pt) 200 response returns APIResponse with attempts=1."""
        Client, _, _, _ = load()
        client = Client("https://api.example.com", max_retries=2)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True}
        mock_resp.headers = {"content-type": "application/json"}

        with patch("requests.request", return_value=mock_resp):
            result = client.request("GET", "/health")
            assert result.status_code == 200
            assert result.attempts == 1

    def test_passes_kwargs(self):
        """(1 pt) Extra kwargs are forwarded to requests.request."""
        Client, _, _, _ = load()
        client = Client("https://api.example.com")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_resp.headers = {}

        with patch("requests.request", return_value=mock_resp) as mock_req:
            client.request("POST", "/data", json={"key": "value"})
            _, kwargs = mock_req.call_args
            assert kwargs.get("json") == {"key": "value"}


class TestErrorClassification:
    """3 points."""

    def test_client_error_no_retry(self):
        """(1 pt) 404 raises APIError with CLIENT category, no retries."""
        Client, APIError, ErrorCategory, _ = load()
        client = Client("https://api.example.com", max_retries=3)

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"error": "not found"}
        mock_resp.headers = {}

        with patch("requests.request", return_value=mock_resp):
            with pytest.raises(APIError) as exc_info:
                client.request("GET", "/missing")
            assert exc_info.value.category == ErrorCategory.CLIENT
            assert exc_info.value.attempts == 1  # No retries for client errors

    def test_transient_error_retries(self):
        """(1 pt) 503 retries up to max_retries, then raises TRANSIENT APIError."""
        Client, APIError, ErrorCategory, _ = load()
        client = Client("https://api.example.com", max_retries=2, base_delay=0.001)

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {}
        mock_resp.headers = {}

        with patch("requests.request", return_value=mock_resp) as mock_req:
            with pytest.raises(APIError) as exc_info:
                client.request("GET", "/slow")
            assert exc_info.value.category == ErrorCategory.TRANSIENT
            assert exc_info.value.attempts == 3  # 1 original + 2 retries
            assert mock_req.call_count == 3

    def test_connection_error_is_transient(self):
        """(1 pt) ConnectionError is classified as TRANSIENT and retried."""
        Client, APIError, ErrorCategory, _ = load()
        client = Client("https://api.example.com", max_retries=1, base_delay=0.001)

        with patch("requests.request", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(APIError) as exc_info:
                client.request("GET", "/down")
            assert exc_info.value.category == ErrorCategory.TRANSIENT
            assert exc_info.value.cause is not None


class TestRetryBehaviour:
    """3 points."""

    def test_retry_then_succeed(self):
        """(1 pt) Transient failure followed by success returns APIResponse."""
        Client, _, _, _ = load()
        client = Client("https://api.example.com", max_retries=3, base_delay=0.001)

        fail_resp = MagicMock()
        fail_resp.status_code = 500
        fail_resp.json.return_value = {}
        fail_resp.headers = {}

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"ok": True}
        ok_resp.headers = {}

        with patch("requests.request", side_effect=[fail_resp, fail_resp, ok_resp]):
            result = client.request("GET", "/flaky")
            assert result.status_code == 200
            assert result.attempts == 3

    def test_429_respects_retry_after(self):
        """(1 pt) 429 with Retry-After header waits the specified time."""
        Client, _, _, _ = load()
        client = Client("https://api.example.com", max_retries=1, base_delay=0.001)

        rate_resp = MagicMock()
        rate_resp.status_code = 429
        rate_resp.json.return_value = {}
        rate_resp.headers = {"Retry-After": "0.05"}

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"ok": True}
        ok_resp.headers = {}

        import time
        with patch("requests.request", side_effect=[rate_resp, ok_resp]):
            start = time.time()
            result = client.request("GET", "/rate-limited")
            elapsed = time.time() - start
            assert result.status_code == 200
            assert elapsed >= 0.04  # Should have waited ~0.05s

    def test_timeout_is_transient(self):
        """(1 pt) requests.Timeout is classified as TRANSIENT."""
        Client, APIError, ErrorCategory, _ = load()
        client = Client("https://api.example.com", max_retries=0, base_delay=0.001)

        with patch("requests.request", side_effect=requests.Timeout("timed out")):
            with pytest.raises(APIError) as exc_info:
                client.request("GET", "/slow")
            assert exc_info.value.category == ErrorCategory.TRANSIENT


class TestCauseChaining:
    """2 points."""

    def test_cause_preserved(self):
        """(1 pt) Original exception is preserved as cause."""
        Client, APIError, _, _ = load()
        client = Client("https://api.example.com", max_retries=0)
        original = requests.ConnectionError("connection refused")

        with patch("requests.request", side_effect=original):
            with pytest.raises(APIError) as exc_info:
                client.request("GET", "/down")
            assert exc_info.value.cause is not None
            assert isinstance(exc_info.value.cause, requests.ConnectionError)

    def test_http_error_includes_status(self):
        """(1 pt) APIError from HTTP response includes status_code."""
        Client, APIError, _, _ = load()
        client = Client("https://api.example.com", max_retries=0)

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"error": "forbidden"}
        mock_resp.headers = {}

        with patch("requests.request", return_value=mock_resp):
            with pytest.raises(APIError) as exc_info:
                client.request("GET", "/secret")
            assert exc_info.value.status_code == 403
