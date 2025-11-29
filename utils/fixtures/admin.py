# utils/fixtures/admin.py

import allure
import pytest
from models.requests.auth_requests import LoginUser, RegisterUser

DEFAULT_BAN_SECONDS = 99999

@pytest.fixture
def create_admin_user(session_sql_client, session_auth_api, create_user):
    def _create_admin():
        with allure.step("Create admin user"):
            # создаем обычного пользователя
            user, _ = create_user()

            # делаем его админом через SQL
            session_sql_client.execute(
                "UPDATE users SET role = 'ADMIN' WHERE email = %s;",
                (user.email,)
            )

            # логиним и получаем токен
            login_user = LoginUser.from_register(user)
            token = session_auth_api.login_and_get_token(login_user)
            return user, token

    return _create_admin


@pytest.fixture(scope="session")
def session_admin_token(session_auth_api, session_sql_client, session_valid_password):
    with allure.step("Prepare reusable admin token"):
        user = RegisterUser.random(password=session_valid_password)
        session_auth_api.register_user(user)
        session_sql_client.execute("UPDATE users SET role = 'ADMIN' WHERE email = %s;", (user.email,))
        token = session_auth_api.login_and_get_token(LoginUser.from_register(user))
        return token


@pytest.fixture(scope="session")
def session_banned_user_token(session_auth_api, session_admin_api, session_admin_token, session_valid_password):
    with allure.step("Prepare banned user token"):
        user = RegisterUser.random(password=session_valid_password)
        session_auth_api.register_user(user)
        session_admin_api.ban_user(email=user.email, seconds=DEFAULT_BAN_SECONDS, token=session_admin_token)
    login_user = LoginUser.from_register(user)
    token = session_auth_api.login_and_get_token(login_user)
    return token


@pytest.fixture(scope="session")
def session_banned_admin_token(session_admin_api, session_auth_api, session_admin_token, session_valid_password,
                               session_sql_client):
    with allure.step("Prepare banned admin token"):
        admin_user = RegisterUser.random(password=session_valid_password)
        session_auth_api.register_user(admin_user)
        session_sql_client.execute("UPDATE users SET role = 'ADMIN' WHERE email = %s;", (admin_user.email,))
        session_admin_api.ban_user(email=admin_user.email, seconds=DEFAULT_BAN_SECONDS, token=session_admin_token)
    login_user = LoginUser.from_register(admin_user)
    token = session_auth_api.login_and_get_token(login_user)
    return token
