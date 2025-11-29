# models/requests/auth_requests.py

from pydantic import BaseModel, EmailStr
from utils.data_generators.fake_credentials import fake_email, fake_username, fake_password


class RegisterUser(BaseModel):
    email: EmailStr
    username: str
    password: str
    passwordConfirmation: str

    # ---------- методы-утилиты ----------

    @classmethod
    def random(cls, password: str | None = None) -> "RegisterUser":
        """создаёт случайного валидного пользователя с одинаковыми паролями"""
        pwd = password or fake_password()
        return cls(
            email=fake_email(),
            username=fake_username(),
            password=pwd,
            passwordConfirmation=pwd,
        )

    @classmethod
    def minimal(cls) -> "RegisterUser":
        """минимально валидный пользователь"""
        pwd = "Aa1PPPPP"
        return cls(
            email="a@a.a",
            username="u",
            password=pwd,
            passwordConfirmation=pwd,
        )


class LoginUser(BaseModel):
    email: EmailStr
    password: str

    @classmethod
    def from_register(cls, user: RegisterUser) -> "LoginUser":
        return cls(email=user.email, password=user.password)
