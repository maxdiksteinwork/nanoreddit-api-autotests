# base/api/auth_api.py

import allure
from typing import Union
from pydantic import TypeAdapter
from utils.clients.http_client import HTTPClient
from utils.constants.routes import APIRoutes
from models.requests.auth_requests import RegisterUser, LoginUser
from models.responses.auth_responses import RegisterResponse, LoginResponse


class AuthAPI:
    def __init__(self, http_client: HTTPClient):
        self.client = http_client

    @allure.step("AuthAPI | Register user")
    def register_user(self, payload: Union[RegisterUser, dict]) -> RegisterResponse:
        """POST /api/v1/auth/register"""
        if isinstance(payload, RegisterUser):
            payload = payload.model_dump()

        resp = self.client.post(f"{APIRoutes.AUTH}/register", json=payload)
        # валидация и возврат правильной модели (OK/Error)
        return TypeAdapter(RegisterResponse).validate_python(resp.json())

    @allure.step("AuthAPI | Login user")
    def login_user(self, payload: Union[LoginUser, dict]) -> LoginResponse:
        """POST /api/v1/auth/login"""
        if isinstance(payload, LoginUser):
            payload = payload.model_dump()

        resp = self.client.post(f"{APIRoutes.AUTH}/login", json=payload)
        return TypeAdapter(LoginResponse).validate_python(resp.json())

    @allure.step("AuthAPI | Login and get JWT token")
    def login_and_get_token(self, payload: LoginUser) -> str | None:
        login_response = self.login_user(payload)
        if login_response.status == "ok":
            return login_response.responseData.jwt
        return None
