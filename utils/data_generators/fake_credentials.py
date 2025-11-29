# utils/data_generators/fake_credentials.py

from faker import Faker

faker = Faker()


# вспомогательные функции для генерации валидных данных
def fake_email() -> str:
    return faker.email()


def fake_username() -> str:
    return faker.user_name() + "_" + faker.pystr(min_chars=4, max_chars=6)


def fake_password(length: int = 12) -> str:
    return faker.password(length=length, digits=True, upper_case=True, lower_case=True) + "@"
