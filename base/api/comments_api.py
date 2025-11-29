# base/api/comments_api.py

import allure
from typing import Union
from pydantic import TypeAdapter
from utils.constants.routes import APIRoutes
from utils.clients.http_client import HTTPClient
from models.requests.comments_requests import ReplyCommentPayload
from models.responses.comments_responses import ReplyCommentResponse


class CommentsAPI:
    def __init__(self, client: HTTPClient):
        self.client = client

    @allure.step("CommentsAPI | Reply to comment")
    def reply_comment(
            self,
            token: str,
            parent_comment_id: str,
            payload: Union[ReplyCommentPayload, dict]
    ) -> ReplyCommentResponse:
        """POST /api/v1/comments/{parentCommentId}/reply"""
        if isinstance(payload, ReplyCommentPayload):
            payload = payload.model_dump()

        resp = self.client.post(
            f"{APIRoutes.COMMENTS}/{parent_comment_id}/reply",
            token=token,
            json=payload,
        )
        return TypeAdapter(ReplyCommentResponse).validate_python(resp.json())
