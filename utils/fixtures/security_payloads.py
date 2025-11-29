# utils/fixtures/security_payloads.py

import pytest

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(2)>",
    "<svg><script>alert(3)</script></svg>",
]

SQL_INJECTION_PAYLOADS = [
    "1; DROP TABLE users;",
    "' OR '1'='1",
    "\" OR \"\" = \"",
    "admin' --",
]


@pytest.fixture(params=XSS_PAYLOADS)
def xss_payload(request):
    return request.param


@pytest.fixture(params=SQL_INJECTION_PAYLOADS)
def sql_injection_payload(request):
    return request.param
