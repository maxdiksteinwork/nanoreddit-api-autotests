# models/responses/auth_responses.py

from pydantic import BaseModel
from typing import Literal, Union
from models.responses.base_responses import BaseResponse, ErrorResponse


# ---------- /api/v1/auth/register ----------

class RegisterResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: str


RegisterResponse = Union[RegisterResponseOK, ErrorResponse]


# ---------- /api/v1/auth/login ----------

class LoginResponseData(BaseModel):
    jwt: str


class LoginResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: LoginResponseData


LoginResponse = Union[LoginResponseOK, ErrorResponse]
