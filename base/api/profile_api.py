# base/api/profile_api.py

import allure
from pydantic import TypeAdapter
from utils.clients.http_client import HTTPClient
from utils.constants.routes import APIRoutes
from models.responses.profile_responses import ProfileResponse


class ProfileAPI:
    def __init__(self, client: HTTPClient):
        self.client = client

    @allure.step("ProfileAPI | Get profile")
    def get_profile(self, token) -> ProfileResponse:
        """POST /api/v1/profile/info"""
        resp = self.client.post(
            f"{APIRoutes.PROFILE}/info",
            token=token,
        )
        return TypeAdapter(ProfileResponse).validate_python(resp.json())
