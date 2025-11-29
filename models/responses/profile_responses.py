# models/responses/profile_responses.py

from typing import Literal, Union, List, Optional
from pydantic import BaseModel, EmailStr
from models.responses.base_responses import BaseResponse, ErrorResponse


# ---------- /api/v1/profile/info ----------

class ProfileData(BaseModel):
    id: int
    email: EmailStr
    username: str
    bannedUntil: Optional[str]
    authorities: List[str]


class ProfileResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: ProfileData


ProfileResponse = Union[ProfileResponseOK, ErrorResponse]
