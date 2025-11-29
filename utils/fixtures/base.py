# utils/fixtures/base.py

import pytest

from settings import get_settings
from utils.clients.http_client import HTTPClient
from utils.clients.sql_client import SQLClient


@pytest.fixture(scope="session")
def session_http_client():
    settings = get_settings()
    client = HTTPClient(base_url=settings.base_url)
    yield client
    client.close()


@pytest.fixture(scope="session")
def session_sql_client():
    settings = get_settings()
    client = SQLClient(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password.get_secret_value(),
    )
    yield client
    client.close()
