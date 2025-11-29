# utils/fixtures/apis.py

import pytest

from base.api.admin_api import AdminAPI
from base.api.comments_api import CommentsAPI
from base.api.posts_api import PostsAPI
from base.api.profile_api import ProfileAPI
from base.api.auth_api import AuthAPI


@pytest.fixture(scope="session")
def session_auth_api(session_http_client):
    return AuthAPI(session_http_client)


@pytest.fixture(scope="session")
def session_profile_api(session_http_client):
    return ProfileAPI(session_http_client)


@pytest.fixture(scope="session")
def session_admin_api(session_http_client):
    return AdminAPI(session_http_client)


@pytest.fixture(scope="session")
def session_posts_api(session_http_client):
    return PostsAPI(session_http_client)


@pytest.fixture(scope="session")
def session_comments_api(session_http_client):
    return CommentsAPI(session_http_client)
