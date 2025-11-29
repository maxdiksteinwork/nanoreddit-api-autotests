# models/responses/admin_responses.py

from typing import Literal, Union, Optional, List
from pydantic import BaseModel
from models.responses.base_responses import BaseResponse, ErrorResponse


# ---------- /api/v1/admin/user/{id} ----------

class AdminUserProfileData(BaseModel):
    id: int
    email: str
    username: str
    bannedUntil: Optional[str] = None  # null, если не забанен
    authorities: List[str]  # ["ROLE_USER"], ["ROLE_ADMIN"], ...


class GetUserProfileResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: AdminUserProfileData


GetUserProfileResponse = Union[GetUserProfileResponseOK, ErrorResponse]


# ---------- /api/v1/admin/user/{email} ----------

class GetUserProfileByEmailResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: AdminUserProfileData


GetUserProfileByEmailResponse = Union[GetUserProfileByEmailResponseOK, ErrorResponse]


# ---------- /api/v1/admin/management/ban/byEmail/{email} ----------

class BanUserData(BaseModel):
    bannedUntil: str


class BanUserResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: BanUserData
    message: str  # "User banned"


BanUserResponse = Union[BanUserResponseOK, ErrorResponse]


# ---------- /api/v1/admin/management/unban/byEmail/{email} ----------

class UnbanUserData(BaseModel):
    bannedUntil: Optional[str] = None  # null после разбанa


class UnbanUserResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: UnbanUserData
    message: str  # "User unbanned"


UnbanUserResponse = Union[UnbanUserResponseOK, ErrorResponse]
