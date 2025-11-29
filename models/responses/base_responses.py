from typing import Literal
from pydantic import BaseModel


class BaseResponse(BaseModel):
    status: Literal["ok", "error"]


class ErrorResponse(BaseResponse):
    status: Literal["error"]
    error: str

