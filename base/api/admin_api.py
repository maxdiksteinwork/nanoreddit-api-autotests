# base/api/admin_api.py

import allure
from pydantic import TypeAdapter
from utils.constants.routes import APIRoutes
from utils.clients.http_client import HTTPClient
from models.responses.admin_responses import (
    GetUserProfileResponse,
    BanUserResponse,
    UnbanUserResponse, GetUserProfileByEmailResponse,
)


class AdminAPI:
    def __init__(self, client: HTTPClient):
        self.client = client

    @allure.step("AdminAPI | Get user profile by id")
    def get_user_profile_by_id(self, user_id: int, token: str) -> GetUserProfileResponse:
        """POST /api/v1/admin/user/{id}"""
        resp = self.client.post(
            f"{APIRoutes.ADMIN}/user/{user_id}",
            token=token,
        )
        return TypeAdapter(GetUserProfileResponse).validate_python(resp.json())

    @allure.step("AdminAPI | Get user profile by email")
    def get_user_profile_by_email(self, email: str, token: str) -> GetUserProfileByEmailResponse:
        """GET /api/v1/admin/user/{email}"""
        resp = self.client.get(
            f"{APIRoutes.ADMIN}/user/{email}",
            token=token,
        )
        return TypeAdapter(GetUserProfileByEmailResponse).validate_python(resp.json())

    @allure.step("AdminAPI | Ban user by email")
    def ban_user(self, email: str, seconds: int, token: str) -> BanUserResponse:
        """POST /api/v1/admin/management/ban/byEmail/{email}?forSeconds=..."""
        resp = self.client.post(
            f"{APIRoutes.ADMIN}/management/ban/byEmail/{email}",
            token=token,
            params={"forSeconds": seconds},
        )
        return TypeAdapter(BanUserResponse).validate_python(resp.json())

    @allure.step("AdminAPI | Unban user by email")
    def unban_user(self, email: str, token: str) -> UnbanUserResponse:
        """POST /api/v1/admin/management/unban/byEmail/{email}"""
        resp = self.client.post(
            f"{APIRoutes.ADMIN}/management/unban/byEmail/{email}",
            token=token,
        )
        return TypeAdapter(UnbanUserResponse).validate_python(resp.json())
