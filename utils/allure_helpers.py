import json
import allure
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, List, Optional


_attachment_stage: ContextVar[Optional[str]] = ContextVar("attachment_stage", default=None)
DEFAULT_STAGE_NAME = "Context"


def format_attachment_name(label: str, stage_override: Optional[str] = None) -> str:
    stage = stage_override or _attachment_stage.get() or DEFAULT_STAGE_NAME
    return f"[{stage}] {label}"


@contextmanager
def allure_stage(name: str):
    token = _attachment_stage.set(name)
    with allure.step(name):
        yield
    _attachment_stage.reset(token)


def prepare_step():
    return allure_stage("Prepare test data")

def execute_step():
    return allure_stage("Execute request")

def validate_api_step():
    return allure_stage("Validate API response")

def validate_db_step():
    return allure_stage("Validate database state")

def cleanup_step():
    return allure_stage("Cleanup")


def attach_http_request(
    method: str,
    url: str,
    headers: Dict[str, Any],
    params: Optional[Dict[str, Any]],
    body: Any,
    name: str = "HTTP request",
) -> None:
    data = {
        "method": method.upper(),
        "url": url,
        "headers": headers,
        "params": params,
        "body": body,
    }
    allure.attach(
        json.dumps(data, ensure_ascii=False, indent=2),
        name=format_attachment_name(name),
        attachment_type=allure.attachment_type.JSON,
    )


def attach_http_response(resp: Any, name: str = "HTTP response") -> None:
    content_type = (resp.headers.get("content-type", "") or "").lower()

    if "application/json" in content_type:
        attachment_type = allure.attachment_type.JSON
        try:
            body = json.dumps(resp.json(), ensure_ascii=False, indent=2)
        except Exception:
            body = resp.text
    else:
        attachment_type = allure.attachment_type.TEXT
        body = resp.text

    allure.attach(
        body,
        name=format_attachment_name(f"{name} {resp.status_code}"),
        attachment_type=attachment_type,
    )


def attach_db_query(
    sql: str,
    params: Optional[tuple],
    rows: List[Dict[str, Any]],
    name: str = "SQL query",
    limit: int = 5,
) -> None:
    info: Dict[str, Any] = {
        "sql": sql,
        "params": params,
        "row_count": len(rows),
    }

    if rows:
        subset = rows[:limit]
        if len(rows) > limit:
            info["note"] = f"Showing first {limit} of {len(rows)} rows"
        info["results"] = subset

    allure.attach(
        json.dumps(info, default=str, ensure_ascii=False, indent=2),
        name=format_attachment_name(name),
        attachment_type=allure.attachment_type.JSON,
    )


