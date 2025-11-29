from typing import Optional, Dict, Any
import allure
import httpx

from utils.allure_helpers import attach_http_request, attach_http_response

MAX_BODY_PREVIEW = 2048


class HTTPClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.client = httpx.Client(base_url=base_url, timeout=timeout)

    def _sanitize_headers(self, headers: dict) -> dict:
        sanitized = dict(headers or {})
        if "Authorization" in sanitized:
            sanitized["Authorization"] = "Bearer ***"
        return sanitized

    def _trim_body(self, body: Any):
        if body is None:
            return None
        if isinstance(body, (dict, list)):
            return body
        body_str = str(body)
        if len(body_str) > MAX_BODY_PREVIEW:
            return f"{body_str[:MAX_BODY_PREVIEW]}...[truncated]"
        return body_str

    def request(self, method: str, path: str, token: Optional[str] = None, **kwargs) -> httpx.Response:
        base_headers = dict(self.client.headers)
        extra_headers = dict(kwargs.pop("headers", {}) or {})

        if token and "Authorization" not in extra_headers:
            extra_headers["Authorization"] = f"Bearer {token}"

        request_headers = {**base_headers, **extra_headers}
        request_payload = kwargs.get("json")
        if request_payload is None:
            request_payload = kwargs.get("data")

        with allure.step(f"{method.upper()} {path}"):
            attach_http_request(
                method=method,
                url=f"{self.client.base_url}{path}",
                headers=self._sanitize_headers(request_headers),
                params=kwargs.get("params"),
                body=self._trim_body(request_payload),
            )

            resp = self.client.request(method, path, headers=request_headers, **kwargs)
            attach_http_response(resp)
            return resp

    def get(self, path: str, params: Optional[Dict[str, Any]] = None, token: Optional[str] = None, **kwargs) -> httpx.Response:
        return self.request("GET", path, params=params, token=token, **kwargs)

    def post(self, path: str, json: Optional[Dict[str, Any]] = None, token: Optional[str] = None, **kwargs) -> httpx.Response:
        return self.request("POST", path, json=json, token=token, **kwargs)

    def close(self):
        self.client.close()
