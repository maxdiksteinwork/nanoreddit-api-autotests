# models/responses/comments_responses.py

from typing import Literal, Union
from models.responses.posts_responses import CommentData
from models.responses.base_responses import BaseResponse, ErrorResponse


# ---------- /api/v1/comments/{parentCommentId}/reply ----------

class ReplyCommentResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: CommentData


ReplyCommentResponse = Union[ReplyCommentResponseOK, ErrorResponse]
