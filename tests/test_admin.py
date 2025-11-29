# tests/test_admin.py
import allure
from datetime import datetime

import pytest
from utils.assertions.api_responses import assert_api_error, assert_api_success
from utils.assertions.database_state import (
    assert_user_not_created,
    fetch_single_user,
)
from utils.allure_helpers import (
    prepare_step,
    execute_step,
    validate_api_step,
    validate_db_step,
)


def call_admin_method(api, method: str, *, user_id=None, email=None, token=None, seconds: int | None = None):
    if method == "get_profile":
        return api.get_user_profile_by_id(user_id=user_id, token=token)
    if method == "get_profile_email":
        return api.get_user_profile_by_email(email=email, token=token)
    if method == "ban":
        return api.ban_user(email=email, seconds=seconds or 60, token=token)
    if method == "unban":
        return api.unban_user(email=email, token=token)
    raise pytest.fail(f"Unknown method: {method}")


# ----------- позитивные тесты -----------

@allure.feature("Admin")
@allure.story("Get user profile by ID")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_get_user_profile_by_id(session_admin_token, created_user_with_id, session_admin_api, session_sql_client):
    with prepare_step():
        user, user_id = created_user_with_id()

    with execute_step():
        resp = session_admin_api.get_user_profile_by_id(user_id, session_admin_token)
        profile = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        assert profile.id == user_id
        assert profile.username == user.username
        assert profile.email == user.email

    with validate_db_step():
        db_user = session_sql_client.query(
            "SELECT id, username, email, banned_until, role FROM users WHERE id = %s",
            (user_id,)
        )
        assert len(db_user) == 1, f"Expected exactly 1 user with id {user_id}, found {len(db_user)}"
        db_user = db_user[0]
        assert db_user["id"] == profile.id
        assert db_user["username"] == profile.username
        assert db_user["email"] == profile.email


@allure.feature("Admin")
@allure.story("Get user profile by email")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_get_user_profile_by_email(session_admin_token, create_user, session_admin_api, session_sql_client):
    with prepare_step():
        user, _ = create_user()

    with execute_step():
        resp = session_admin_api.get_user_profile_by_email(user.email, session_admin_token)
        profile = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        assert profile.email == user.email
        assert profile.username == user.username

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            user.email,
            columns="email, username",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        assert db_user["email"] == profile.email
        assert db_user["username"] == profile.username


@allure.feature("Admin")
@allure.story("Ban user")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_ban_user(session_admin_token, create_user, session_admin_api, session_sql_client):
    with prepare_step():
        user, _ = create_user()

    with execute_step():
        resp = session_admin_api.ban_user(user.email, 60, session_admin_token)

    with validate_api_step():
        assert_api_success(resp)
        assert resp.message == "User banned"
        assert resp.responseData.bannedUntil, f"'bannedUntil' missing or empty in responseData: {resp}"

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            user.email,
            columns="id, email, banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        db_banned_until = db_user["banned_until"]
        assert db_banned_until is not None
        api_dt = datetime.fromisoformat(resp.responseData.bannedUntil.replace("Z", "+00:00"))
        assert api_dt == db_banned_until, "API bannedUntil must match DB"


@allure.feature("Admin")
@allure.story("Ban user")
@allure.severity(allure.severity_level.NORMAL)
def test_admin_ban_already_banned_user(session_admin_token, create_user, session_admin_api, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        first_resp = session_admin_api.ban_user(user.email, 600, session_admin_token)
        assert_api_success(first_resp)
        db_user_first = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        first_banned_until = db_user_first["banned_until"]
        assert first_banned_until is not None

    with execute_step():
        second_resp = session_admin_api.ban_user(user.email, 60, session_admin_token)

    with validate_api_step():
        assert_api_success(second_resp)
        assert second_resp.responseData.bannedUntil != first_resp.responseData.bannedUntil, (
            f"'bannedUntil' hasn't changed: {first_resp.responseData.bannedUntil}"
        )

    with validate_db_step():
        db_user_second = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        second_banned_until = db_user_second["banned_until"]
        assert second_banned_until is not None
        assert second_banned_until != first_banned_until, "Expected banned_until to change after second ban"


@allure.feature("Admin")
@allure.story("Ban user")
@allure.severity(allure.severity_level.NORMAL)
def test_admin_ban_another_admin(session_admin_api, create_admin_user, session_admin_token, session_sql_client):
    with prepare_step():
        first_admin_token = session_admin_token
        another_admin, _ = create_admin_user()

    with execute_step():
        resp = session_admin_api.ban_user(another_admin.email, 60, first_admin_token)

    with validate_api_step():
        assert_api_success(resp)
        assert resp.responseData.bannedUntil is not None

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            another_admin.email,
            columns="id, email, banned_until",
            error_message=f"Expected exactly 1 user with email {another_admin.email}",
        )
        assert db_user["banned_until"] is not None, "Expected another admin to be banned in database"


@allure.feature("Admin")
@allure.story("Unban user")
@allure.severity(allure.severity_level.CRITICAL)
def test_admin_unban_user(session_admin_token, create_user, session_admin_api, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        resp_ban = session_admin_api.ban_user(user.email, 60, session_admin_token)
        assert resp_ban.message == "User banned"

    with execute_step():
        resp_unban = session_admin_api.unban_user(user.email, session_admin_token)

    with validate_api_step():
        assert_api_success(resp_unban)
        assert resp_unban.message == "User unbanned"
        assert resp_unban.responseData.bannedUntil is None

    with validate_db_step():
        db_user_unbanned = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        assert db_user_unbanned["banned_until"] is None, "Expected banned_until to be null after unban"


# ----------- негативные тесты -----------

@allure.feature("Admin")
@allure.story("Authorization")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("method", ["get_profile", "get_profile_email", "ban", "unban"])
def test_admin_methods_without_token(method, session_admin_api, created_user_with_id, session_sql_client):
    with prepare_step():
        user, user_id = created_user_with_id()
        # сохраняем исходное состояние banned_until для проверки
        db_user_before = session_sql_client.query("SELECT banned_until FROM users WHERE id = %s", (user_id,))
        assert len(db_user_before) == 1, f"Expected exactly 1 user with id {user_id}, found {len(db_user_before)}"
        original_banned_until = db_user_before[0]["banned_until"]

    with execute_step():
        resp = call_admin_method(
            session_admin_api,
            method,
            user_id=user_id,
            email=user.email,
            token=None,
            seconds=60,
        )

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        # проверяем, что состояние не изменилось
        db_user_after = session_sql_client.query("SELECT banned_until FROM users WHERE id = %s", (user_id,))
        assert len(db_user_after) == 1, f"Expected exactly 1 user with id {user_id}, found {len(db_user_after)}"
        assert db_user_after[0]["banned_until"] == original_banned_until, "Expected banned_until to remain unchanged"


@allure.feature("Admin")
@allure.story("Authorization")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("method", ["get_profile", "get_profile_email", "ban", "unban"])
def test_admin_methods_with_user_token(method, session_admin_api, create_user, module_create_user_get_token,
                                       created_user_with_id, session_sql_client):
    with prepare_step():
        user_token = module_create_user_get_token
        target_user, target_user_id = created_user_with_id()
        db_user_before = session_sql_client.query("SELECT banned_until FROM users WHERE id = %s", (target_user_id,))
        assert len(
            db_user_before) == 1, f"Expected exactly 1 user with id {target_user_id}, found {len(db_user_before)}"
        original_banned_until = db_user_before[0]["banned_until"]

    with execute_step():
        resp = call_admin_method(
            session_admin_api,
            method,
            user_id=target_user_id,
            email=target_user.email,
            token=user_token,
            seconds=60,
        )

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        db_user_after = session_sql_client.query("SELECT banned_until FROM users WHERE id = %s", (target_user_id,))
        assert len(db_user_after) == 1, f"Expected exactly 1 user with id {target_user_id}, found {len(db_user_after)}"
        assert db_user_after[0]["banned_until"] == original_banned_until, "Expected banned_until to remain unchanged"


@allure.feature("Admin")
@allure.story("Get user profile | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_admin_get_user_profile_with_invalid_id(session_admin_token, session_admin_api, session_sql_client):
    with execute_step():
        resp1 = session_admin_api.get_user_profile_by_id(user_id=999999, token=session_admin_token)

    with validate_api_step():
        # несуществующий ID
        assert_api_error(resp1, expected_message="user not found")

    with validate_db_step():
        db_user1 = session_sql_client.query("SELECT id FROM users WHERE id = %s", (999999,))
        assert len(db_user1) == 0, "Expected no user with id 999999"

    with execute_step():
        # некорректный тип ID
        resp2 = session_admin_api.get_user_profile_by_id(user_id="abc", token=session_admin_token)

    with validate_api_step():
        assert_api_error(resp2, expected_message="an error occurred")


@allure.feature("Admin")
@allure.story("Get user profile | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("invalid_email", (
        "nonexistent_email_1337_1488_666_228@example.com",  # несуществующий email
        "invalid-email"  # некорректный формат email
))
def test_admin_get_user_profile_by_invalid_email(session_admin_token, session_admin_api, invalid_email,
                                                 session_sql_client):
    with prepare_step():
        assert_user_not_created(session_sql_client, email=invalid_email,
                                error_message=f"Unexpected user with email {invalid_email} before request")

    with execute_step():
        resp = session_admin_api.get_user_profile_by_email(invalid_email, session_admin_token)

    with validate_db_step():
        assert_user_not_created(session_sql_client, email=invalid_email,
                                error_message=f"Unexpected user with email {invalid_email} after request")

    with validate_api_step():
        assert_api_error(resp, expected_message="user not found")


@allure.feature("Admin")
@allure.story("Ban/Unban user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("invalid_email", (
        "nonexistent_email_1337_1488_666_228@example.com",
        "invalid-email"
))
def test_admin_ban_unban_invalid_email(session_admin_token, session_admin_api, invalid_email, session_sql_client):
    with prepare_step():
        assert_user_not_created(session_sql_client, email=invalid_email,
                                error_message=f"Expected no user with email {invalid_email} before ban attempt")

    with execute_step():
        resp_ban_nonexistent = session_admin_api.ban_user(invalid_email, 60, session_admin_token)

    with validate_db_step():
        assert_user_not_created(session_sql_client, email=invalid_email,
                                error_message=f"Expected no user with email {invalid_email}")

    with validate_api_step():
        assert_api_error(resp_ban_nonexistent, expected_message="user not found")

    with execute_step():
        resp_unban_nonexistent = session_admin_api.unban_user(invalid_email, session_admin_token)

    with validate_db_step():
        assert_user_not_created(
            session_sql_client,
            email=invalid_email,
            error_message=f"Expected no user with email {invalid_email} after unban attempt"
        )

    with validate_api_step():
        assert_api_error(resp_unban_nonexistent, expected_message="user not found")


@allure.feature("Admin")
@allure.story("Ban user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_admin_ban_invalid_for_seconds(session_admin_token, session_admin_api, create_user, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        db_user_before = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        original_banned_until = db_user_before["banned_until"]

    with execute_step():
        # отрицательное значение
        resp_negative = session_admin_api.ban_user(user.email, -10, session_admin_token)
        resp_zero = session_admin_api.ban_user(user.email, 0, session_admin_token)
        # ноль
        resp_string = session_admin_api.ban_user(user.email, "sixty", session_admin_token)
        # некорректный тип (строка)

    with validate_db_step():
        db_user_after = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        assert db_user_after["banned_until"] == original_banned_until, "Expected banned_until to remain unchanged"

    with validate_api_step():
        for resp in (resp_negative, resp_zero, resp_string):
            assert_api_error(resp, expected_message="an error occurred")


@allure.feature("Admin")
@allure.story("Unban user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_admin_unban_not_banned_user(session_admin_token, session_admin_api, create_user, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        db_user_before = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        # проверяем, что пользователь не забанен изначально в БД
        assert db_user_before["banned_until"] is None

    with execute_step():
        resp = session_admin_api.unban_user(user.email, session_admin_token)

    with validate_db_step():
        db_user_after = fetch_single_user(
            session_sql_client,
            user.email,
            columns="banned_until",
            error_message=f"Expected exactly 1 user with email {user.email}",
        )
        # проверяем, что banned_until остался null
        assert db_user_after["banned_until"] is None

    with validate_api_step():
        assert_api_error(resp, expected_message="user is not banned")


@allure.feature("Admin")
@allure.story("Ban user")
@allure.severity(allure.severity_level.NORMAL)
def test_admin_ban_self(session_admin_api, create_admin_user, session_sql_client):
    with prepare_step():
        admin_user, token = create_admin_user()

    with execute_step():
        resp = session_admin_api.ban_user(admin_user.email, 60, token)

    with validate_api_step():
        assert_api_success(resp)
        assert resp.responseData.bannedUntil is not None

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            admin_user.email,
            columns="id, email, banned_until",
            error_message=f"Expected exactly 1 user with email {admin_user.email}",
        )
        assert db_user["banned_until"] is not None, "Expected admin to be banned in database"
