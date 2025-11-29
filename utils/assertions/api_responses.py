# utils/assertions/api_responses.py


from typing import Any


def assert_api_success(resp: Any):
    assert hasattr(resp, "status"), f"Response has no 'status' attribute: {type(resp)}"
    assert resp.status == "ok", f"Expected status 'ok', got: {resp.status}"


def assert_api_error(resp: Any, expected_message: str | list[str] | tuple[str] = None):
    assert hasattr(resp, "status"), f"Response has no 'status' attribute: {type(resp)}"
    assert resp.status == "error", f"Expected status 'error', got: {resp.status}"

    if expected_message:
        assert hasattr(resp, "error"), f"Response has no 'error' field: {type(resp)}"
        messages = (
            expected_message
            if isinstance(expected_message, (list, tuple))
            else [expected_message]
        )
        error_text = resp.error.lower()
        assert any(msg.lower() in error_text for msg in messages), (
            f"Expected one of {messages}, got: {resp.error}"
        )
