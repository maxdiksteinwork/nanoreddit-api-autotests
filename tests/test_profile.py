# tests/test_profile.py

import allure
from models.requests.auth_requests import LoginUser
from utils.assertions.api_responses import assert_api_error, assert_api_success
from utils.assertions.database_state import get_user_by_email
from utils.constants.routes import APIRoutes
from utils.allure_helpers import (
    prepare_step,
    execute_step,
    validate_api_step,
    validate_db_step,
)


# ----------- позитивные тесты -----------

@allure.feature("Profile")
@allure.story("Get profile")
@allure.severity(allure.severity_level.CRITICAL)
def test_get_profile(create_user, session_profile_api, session_auth_api, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        login_user = LoginUser.from_register(user)
        token = session_auth_api.login_and_get_token(login_user)

    with execute_step():
        resp = session_profile_api.get_profile(token)
        profile = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        assert profile, f"No responseData in profile: {resp}"
        assert profile.id, "Profile ID should be present"

    with validate_db_step():
        db_user = get_user_by_email(session_sql_client, user.email)
        assert len(db_user) == 1, f"Expected exactly 1 user with email {user.email}, found {len(db_user)}"
        db_user = db_user[0]
        assert db_user["id"] == profile.id
        assert db_user["username"] == profile.username
        assert db_user["email"] == profile.email


@allure.feature("Profile")
@allure.story("Get admin profile")
@allure.severity(allure.severity_level.NORMAL)
def test_get_admin_profile(session_profile_api, session_admin_token, session_sql_client):
    with prepare_step():
        admin_token = session_admin_token

    with execute_step():
        resp = session_profile_api.get_profile(admin_token)
        profile = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        assert profile, f"No responseData in profile: {resp}"
        assert "ROLE_ADMIN" in profile.authorities, f"Expected ROLE_ADMIN in authorities: {profile}"

    with validate_db_step():
        db_user = get_user_by_email(session_sql_client, profile.email)
        assert len(db_user) == 1, f"Expected exactly 1 user with email {profile.email}, found {len(db_user)}"
        assert db_user[0]["role"] == "ADMIN"


# ----------- негативные тесты -----------

@allure.feature("Profile")
@allure.story("Get profile | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_get_profile_invalid_token(session_profile_api):
    with prepare_step():
        invalid_token = "invalid.token.value"

    with execute_step():
        resp_invalid_token = session_profile_api.get_profile(invalid_token)

    with validate_api_step():
        assert_api_error(resp_invalid_token, expected_message="access denied")

    with execute_step():
        resp_no_token = session_profile_api.client.post(f"{APIRoutes.PROFILE}/info")
        data = resp_no_token.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"
