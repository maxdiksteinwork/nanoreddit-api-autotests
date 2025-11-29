# utils/fixtures/auth.py

import allure
import pytest
from faker import Faker
from models.requests.auth_requests import RegisterUser, LoginUser
from utils.data_generators.fake_credentials import fake_email, fake_username, fake_password

faker = Faker()


@pytest.fixture(scope="session")
def session_valid_password():
    return fake_password()


@pytest.fixture
def create_user(session_auth_api, session_valid_password):
    def _create():
        with allure.step("Register user via Auth API"):
            user = RegisterUser.random(password=session_valid_password)
            resp = session_auth_api.register_user(user)
            return user, resp

    return _create


@pytest.fixture(scope="module")
def module_create_user_get_token(session_auth_api, session_valid_password):
    with allure.step("Register user and obtain JWT token"):
        user = RegisterUser.random(password=session_valid_password)
        session_auth_api.register_user(user)
        login_user = LoginUser.from_register(user)
        token = session_auth_api.login_and_get_token(login_user)
        return token


@pytest.fixture
def created_user_with_id(create_user, session_sql_client):
    def _create():
        user, _ = create_user()

        # получаем id пользователя из базы
        result = session_sql_client.query(
            "SELECT id FROM users WHERE email = %s", (user.email,)
        )
        user_id = result[0]["id"]
        return user, user_id

    return _create


def create_invalid_email_list():
    # функция, возвращающая список уникальных невалидных email
    email = fake_email()
    local, domain = email.split("@", 1)
    domain_root = domain.split(".", 1)[0]
    faker_letters1 = faker.pystr(3, 3).lower()
    faker_letters2 = faker.pystr(3, 3).lower()
    variants = [
        local,  # plainaddress
        f"{local}.com",  # missingatsign.com
        f"@{domain_root}{faker_letters1}.{faker_letters2}",  # @missinglocal.com
        f"{local}@.com",  # missingdomainroot@.com
        f"{local}@com",  # missingdomainrootanddot@com
        f"{local}@{domain_root}..com",  # doubledot@domain..com
    ]
    return variants


@pytest.fixture(params=[
    "missing_email",
    "missing_username",
    "missing_password",
    "missing_passwordConfirmation",
    "missing_all"
])
def register_missing_field_payload(request, session_valid_password):
    # фикстура для генерации payload с отсутствующими обязательными полями.
    payload = {
        "email": fake_email(),
        "username": fake_username(),
        "password": session_valid_password,
        "passwordConfirmation": session_valid_password,
    }
    if request.param == "missing_email":
        payload.pop("email")
    elif request.param == "missing_username":
        payload.pop("username")
    elif request.param == "missing_password":
        payload.pop("password")
    elif request.param == "missing_passwordConfirmation":
        payload.pop("passwordConfirmation")
    elif request.param == "missing_all":
        payload = {}
    return payload


@pytest.fixture(params=[
    "empty_email",
    "empty_username",
    "empty_password",
    "empty_passwordConfirmation",
    "empty_all"
])
def register_empty_payload(request, session_valid_password):
    payload = {
        "email": fake_email(),
        "username": fake_username(),
        "password": session_valid_password,
        "passwordConfirmation": session_valid_password,
    }
    if request.param == "empty_email":
        payload["email"] = ""
    elif request.param == "empty_username":
        payload["username"] = ""
    elif request.param == "empty_password":
        payload["password"] = ""
    elif request.param == "empty_passwordConfirmation":
        payload["passwordConfirmation"] = ""
    elif request.param == "empty_all":
        for key in payload:
            payload[key] = ""
    return payload


@pytest.fixture(params=[
    "missing_email",
    "missing_password",
    "missing_all"
])
def login_missing_field_payload(request, session_valid_password):
    payload = {"email": fake_email(), "password": session_valid_password}
    if request.param == "missing_email":
        payload.pop("email")
    elif request.param == "missing_password":
        payload.pop("password")
    elif request.param == "missing_all":
        payload = {}
    return payload


@pytest.fixture(params=[
    "empty_email",
    "empty_password",
    "empty_all"
])
def login_empty_field_payload(request, session_valid_password):
    payload = {"email": fake_email(), "password": session_valid_password}
    if request.param == "empty_email":
        payload["email"] = ""
    elif request.param == "empty_password":
        payload["password"] = ""
    elif request.param == "empty_all":
        payload["email"] = ""
        payload["password"] = ""
    return payload


@pytest.fixture
def minimal_user(session_sql_client):
    # подготавливаем payload с минимальными значениями и в teardown удаляем юзера из базы во избежание коллизий
    user = RegisterUser.minimal()
    yield user
    session_sql_client.execute("DELETE FROM users WHERE email = %s", (user.email,))
