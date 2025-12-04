# tests/test_auth.py

import allure
import pytest
from faker import Faker

from utils.assertions.api_responses import assert_api_error, assert_api_success
from utils.assertions.database_state import (
    assert_user_not_created,
    fetch_single_user,
)
from utils.data_generators.fake_credentials import fake_email, fake_username, fake_password
from utils.fixtures.auth import create_invalid_email_list
from models.requests.auth_requests import RegisterUser, LoginUser
from utils.allure_helpers import (
    prepare_step,
    execute_step,
    validate_api_step,
    validate_db_step,
    cleanup_step,
)

faker = Faker()


def cleanup_security_payload_user(sql_client, *, email: str | None = None, username: str | None = None) -> None:
    """
    удаляет тестовые записи, созданные при проверках XSS/SQL-injection payloads
    """
    queries = {
        "email": "DELETE FROM users WHERE email = %s",
        "username": "DELETE FROM users WHERE username = %s",
    }
    for field, value in (("email", email), ("username", username)):
        if value:
            try:
                sql_client.execute(queries[field], (value,))
            except Exception as exc:
                print(f"[cleanup] Failed to delete user by {field}={value}: {exc}")


# ----------- позитивные тесты -----------

@allure.feature("Auth")
@allure.story("Register user")
@allure.severity(allure.severity_level.CRITICAL)
def test_register_user(create_user, session_sql_client):
    with prepare_step():
        user, resp = create_user()

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            user.email,
            columns="id, username, email, password, role, banned_until",
            error_message=f"Expected exactly 1 user in database with email {user.email}",
        )
        assert db_user[
                   "username"] == user.username, f"Username mismatch: expected {user.username}, got {db_user['username']}"
        assert db_user["email"] == user.email, f"Email mismatch: expected {user.email}, got {db_user['email']}"
        assert db_user["id"] is not None, "User ID should not be null"
        assert db_user["password"], "Password should be stored in database"

    with validate_api_step():
        assert_api_success(resp)
        assert f"User {db_user['username']}" in resp.responseData


@allure.feature("Auth")
@allure.story("Register and login")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.password_special_symbol_issue
def test_register_and_login(session_auth_api, create_user, session_sql_client):
    with prepare_step():
        user, _ = create_user()

    with validate_db_step():
        db_user = fetch_single_user(session_sql_client, user.email, columns="id, username, email")

    with execute_step():
        login_user = LoginUser.from_register(user)
        token = session_auth_api.login_and_get_token(login_user)

    with validate_api_step():
        assert token, f"No token received for user {login_user.email}"
        assert login_user.email == db_user["email"]


@allure.feature("Auth")
@allure.story("Register user | boundary values")
@allure.severity(allure.severity_level.NORMAL)
def test_register_with_min_values(session_auth_api, minimal_user, session_sql_client):
    with prepare_step():
        username = minimal_user.username

    with execute_step():
        resp = session_auth_api.register_user(minimal_user)

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            minimal_user.email,
            columns="id, username, email",
        )
        assert db_user["username"] == username
        assert db_user["email"] == minimal_user.email

    with validate_api_step():
        assert_api_success(resp)
        assert f"User {db_user['username']}" in resp.responseData, f"Unexpected responseData: {resp.responseData}"


@allure.feature("Auth")
@allure.story("Register user | boundary values")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.doc_issue
def test_register_with_max_values(session_auth_api, session_valid_password, session_sql_client):
    with prepare_step():
        local_part = faker.unique.pystr(min_chars=64, max_chars=64)
        domain_before_dot = faker.unique.pystr(min_chars=63, max_chars=63)
        domain_after_dot = faker.unique.pystr(min_chars=63, max_chars=63)
        email = f"{local_part}@{domain_before_dot}.{domain_after_dot}"
        # email хранится в базе по стандарту в таком виде
        expected_email = f"{local_part}@{domain_before_dot.lower()}.{domain_after_dot.lower()}"
        username = faker.unique.pystr(min_chars=255, max_chars=255)
        password = session_valid_password + "0" * (72 - len(session_valid_password))
        user = RegisterUser(
            email=email,
            username=username,
            password=password,
            passwordConfirmation=password,
        )
        allure.attach(email, name="Generated email", attachment_type=allure.attachment_type.TEXT)

    with execute_step():
        resp = session_auth_api.register_user(user)

    with validate_db_step():
        db_user = fetch_single_user(
            session_sql_client,
            expected_email,
            columns="id, username, email",
        )
        assert db_user["username"] == username
        assert db_user["email"] == expected_email

    with validate_api_step():
        assert_api_success(resp)
        assert f"User {db_user['username']}" in resp.responseData, f"Unexpected responseData: {resp.responseData}"


# ----------- негативные тесты register -----------

@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.doc_issue
@pytest.mark.parametrize(
    "email_len_local,email_len_domain_before,email_len_domain_after,username_len,password_len",
    [
        # превышение длины локальной части email
        (65, 63, 63, 255, 72),
        # превышение длины домена до точки
        (64, 64, 63, 255, 72),
        # превышение длины домена после точки
        (64, 63, 64, 255, 72),
        # превышение длины username
        (64, 63, 63, 256, 72),
        # превышение длины пароля
        (64, 63, 63, 255, 73),
    ],
    ids=[
        "email_local_part_too_long",
        "email_domain_before_dot_too_long",
        "email_domain_after_dot_too_long",
        "username_too_long",
        "password_too_long",
    ]
)
def test_register_with_exceeding_max_values(
        session_auth_api, session_valid_password, session_sql_client,
        email_len_local, email_len_domain_before, email_len_domain_after,
        username_len, password_len
):
    with prepare_step():
        local_part = faker.unique.pystr(min_chars=email_len_local, max_chars=email_len_local)
        domain_before_dot = faker.unique.pystr(min_chars=email_len_domain_before, max_chars=email_len_domain_before)
        domain_after_dot = faker.unique.pystr(min_chars=email_len_domain_after, max_chars=email_len_domain_after)
        email = f"{local_part}@{domain_before_dot}.{domain_after_dot}"
        username = faker.unique.pystr(min_chars=username_len, max_chars=username_len)
        password = session_valid_password + "0" * (password_len - len(session_valid_password))
        payload = {
            "email": email,
            "username": username,
            "password": password,
            "passwordConfirmation": password,
        }

    with execute_step():
        resp = session_auth_api.register_user(payload)

    with validate_db_step():
        assert_user_not_created(session_sql_client, email=email, username=username)

    with validate_api_step():
        assert_api_error(resp, expected_message=("validation error", "an error occurred"))


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_register_missing_required_fields(session_auth_api, register_missing_field_payload, session_sql_client):
    with prepare_step():
        payload = register_missing_field_payload

    with execute_step():
        resp = session_auth_api.register_user(payload)

    with validate_db_step():
        if payload.get("email") or payload.get("username"):
            assert_user_not_created(
                session_sql_client,
                email=payload.get("email"),
                username=payload.get("username")
            )

    with validate_api_step():
        assert_api_error(resp, expected_message="an error occurred")


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_register_with_empty_fields(session_auth_api, register_empty_payload, session_sql_client):
    with prepare_step():
        payload = register_empty_payload

    with execute_step():
        resp = session_auth_api.register_user(payload)

    with validate_db_step():
        if payload.get("email") or payload.get("username"):
            assert_user_not_created(
                session_sql_client,
                email=payload.get("email"),
                username=payload.get("username")
            )

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("field", ["email", "username"])
def test_register_with_existing_email_or_username(session_auth_api, create_user, field, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        # делаем payload, где уникальное поле совпадает
        original_email = user.email
        original_username = user.username

        if field == "email":
            user.username = fake_username()
        elif field == "username":
            user.email = fake_email()

    with execute_step():
        resp = session_auth_api.register_user(user)

    with validate_api_step():
        assert_api_error(resp, expected_message="already in use")

    with validate_db_step():
        if field == "email":
            # по исходному email должна быть одна запись, по новому username — ни одной
            fetch_single_user(
                session_sql_client,
                original_email,
                columns="id",
                error_message=f"Expected 1 user with email {original_email}",
            )
            assert_user_not_created(session_sql_client, username=user.username)
        elif field == "username":
            db_username = session_sql_client.query("SELECT id FROM users WHERE username = %s", (original_username,))
            assert len(db_username) == 1, f"Expected 1 user with username {original_username}, found {len(db_username)}"
            assert_user_not_created(session_sql_client, email=user.email)


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "invalid_email",
    create_invalid_email_list()
)
def test_register_with_invalid_email(session_auth_api, invalid_email, session_valid_password, session_sql_client):
    with prepare_step():
        payload = {
            "email": invalid_email,
            "username": fake_username(),
            "password": session_valid_password,
            "passwordConfirmation": session_valid_password,
        }

    with execute_step():
        resp = session_auth_api.register_user(payload)

    with validate_db_step():
        assert_user_not_created(session_sql_client, email=invalid_email, username=payload["username"])

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_register_email_case_insensitive(session_auth_api, create_user, session_valid_password, session_sql_client):
    with prepare_step():
        user, _ = create_user()
        upper_email_user = RegisterUser(
            email=user.email.upper(),
            username=fake_username(),
            password=session_valid_password,
            passwordConfirmation=session_valid_password,
        )

    with execute_step():
        resp = session_auth_api.register_user(upper_email_user)

    with validate_db_step():
        db = session_sql_client.query("SELECT id FROM users WHERE lower(email) = lower(%s)", (user.email,))
        assert len(db) == 1, "Expected exactly 1 user by case-insensitive email"

    with validate_api_step():
        assert_api_error(resp, expected_message="already in use")


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_register_with_mismatched_passwords(session_auth_api, session_sql_client):
    with prepare_step():
        user = RegisterUser(
            email=fake_email(),
            username=fake_username(),
            password=fake_password(),
            passwordConfirmation=fake_password(),
        )

    with execute_step():
        resp = session_auth_api.register_user(user)

    with validate_db_step():
        assert_user_not_created(session_sql_client, email=user.email, username=user.username)

    with validate_api_step():
        assert_api_error(resp, expected_message="password is not equal")


@allure.feature("Auth")
@allure.story("Register user | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "invalid_password",
    [
        "short",  # меньше 8 символов
        "alllowercase",  # нет цифр и заглавных
        "ALLUPPERCASE",  # нет цифр и строчных
        "12345678",  # только цифры
        "Password",  # нет цифр
        "Pass word1",  # есть пробел
    ]
)
def test_register_with_invalid_passwords(session_auth_api, invalid_password, session_sql_client):
    with prepare_step():
        user = RegisterUser(
            email=fake_email(),
            username=fake_username(),
            password=invalid_password,
            passwordConfirmation=invalid_password,
        )

    with execute_step():
        resp = session_auth_api.register_user(user)

    with validate_db_step():
        assert_user_not_created(session_sql_client, email=user.email, username=user.username)

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")


@allure.feature("Auth")
@allure.story("Register user | security")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("field", ["username", "email"])
def test_register_xss(session_auth_api, xss_payload, field, session_valid_password, session_sql_client):
    # помещаем xss в username или в email в зависимости от параметра `field`
    with prepare_step():
        email = fake_email() if field == "username" else xss_payload
        username = xss_payload if field == "username" else "safe_username"
        pwd = session_valid_password
        payload = {
            "email": email,
            "username": username,
            "password": pwd,
            "passwordConfirmation": pwd,
        }

    with execute_step():
        resp = session_auth_api.register_user(payload)

    try:
        with validate_db_step():
            if payload.get("email") or payload.get("username"):
                assert_user_not_created(session_sql_client, email=payload.get("email"),
                                        username=payload.get("username"))

        with validate_api_step():
            assert_api_error(resp, expected_message="validation error")
    finally:
        with cleanup_step():
            cleanup_security_payload_user(
                session_sql_client,
                email=payload.get("email"),
                username=payload.get("username"),
            )


@allure.feature("Auth")
@allure.story("Register user | security")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("field", ["username", "email"])
def test_register_sql_injection(session_auth_api, sql_injection_payload, field, session_valid_password,
                                session_sql_client):
    with prepare_step():
        email = fake_email() if field == "username" else sql_injection_payload
        username = sql_injection_payload if field == "username" else "safe_username"
        pwd = session_valid_password
        payload = {
            "email": email,
            "username": username,
            "password": pwd,
            "passwordConfirmation": pwd,
        }

    with execute_step():
        resp = session_auth_api.register_user(payload)

    try:
        with validate_db_step():
            if payload.get("email") or payload.get("username"):
                assert_user_not_created(session_sql_client, email=payload.get("email"),
                                        username=payload.get("username"))

        with validate_api_step():
            assert_api_error(resp, expected_message="validation error")
    finally:
        with cleanup_step():
            cleanup_security_payload_user(
                session_sql_client,
                email=payload.get("email"),
                username=payload.get("username"),
            )


# ----------- негативные тесты login -----------

@allure.feature("Auth")
@allure.story("Login | authentication errors")
@allure.severity(allure.severity_level.CRITICAL)
def test_login_with_wrong_password(session_auth_api, create_user):
    with prepare_step():
        user, _ = create_user()
        user_with_wrong_password = LoginUser(email=user.email, password=fake_password())

    with execute_step():
        resp = session_auth_api.login_user(user_with_wrong_password)

    with validate_api_step():
        assert_api_error(resp, expected_message="bad credentials")


@allure.feature("Auth")
@allure.story("Login | authentication errors")
@allure.severity(allure.severity_level.NORMAL)
def test_login_with_nonexistent_email(session_auth_api, session_valid_password):
    with prepare_step():
        non_existent_user = LoginUser(email=fake_email(), password=session_valid_password)

    with execute_step():
        resp = session_auth_api.login_user(non_existent_user)

    with validate_api_step():
        assert_api_error(resp, expected_message="bad credentials")


@allure.feature("Auth")
@allure.story("Login | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_login_missing_required_fields(session_auth_api, login_missing_field_payload):
    with prepare_step():
        payload = login_missing_field_payload

    with execute_step():
        resp = session_auth_api.login_user(payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="an error occurred")


@allure.feature("Auth")
@allure.story("Login | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_login_with_empty_fields(session_auth_api, login_empty_field_payload):
    with prepare_step():
        payload = login_empty_field_payload

    with execute_step():
        resp = session_auth_api.login_user(payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")
