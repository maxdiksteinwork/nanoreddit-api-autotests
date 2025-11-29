# base/api/posts_api.py

import allure
from typing import Union

import httpx
from pydantic import TypeAdapter
from utils.constants.routes import APIRoutes
from utils.clients.http_client import HTTPClient
from models.requests.posts_requests import PublishPostPayload, AddCommentPayload
from models.responses.posts_responses import (
    PublishPostResponse,
    VotePostResponse,
    AddCommentResponse,
    GetPostsResponse,
    GetPostByIdResponse,
)


class PostsAPI:
    def __init__(self, client: HTTPClient):
        self.client = client

    @allure.step("PostsAPI | Publish post")
    def publish_post(self, token: str, payload: Union[PublishPostPayload, dict]) -> PublishPostResponse:
        """POST /api/v1/posts/publish"""
        if isinstance(payload, PublishPostPayload):
            payload = payload.model_dump()

        resp = self.client.post(
            f"{APIRoutes.POSTS}/publish",
            token=token,
            json=payload,
        )
        return TypeAdapter(PublishPostResponse).validate_python(resp.json())

    @allure.step("PostsAPI | Vote post")
    def vote_post(self, token: str, post_id: str, value: int) -> VotePostResponse:
        """POST /api/v1/posts/{postId}/vote"""
        resp = self.client.post(
            f"{APIRoutes.POSTS}/{post_id}/vote",
            token=token,
            params={"value": value},
        )
        return TypeAdapter(VotePostResponse).validate_python(resp.json())

    @allure.step("PostsAPI | Add comment")
    def add_comment(self, token: str, post_id: str, payload: Union[AddCommentPayload, dict]) -> AddCommentResponse:
        """POST /api/v1/posts/{postId}/addComment"""
        if isinstance(payload, AddCommentPayload):
            payload = payload.model_dump()

        resp = self.client.post(
            f"{APIRoutes.POSTS}/{post_id}/addComment",
            token=token,
            json=payload,
        )
        return TypeAdapter(AddCommentResponse).validate_python(resp.json())

    @allure.step("PostsAPI | Get posts")
    def get_posts(self, token: str, page: int = 0, size: int = 20, sort: str = "createdAt,asc") -> tuple[
        GetPostsResponse, httpx.Response]:
        """GET /api/v1/posts"""
        resp_raw = self.client.get(
            APIRoutes.POSTS,
            params={"page": page, "size": size, "sort": sort},
            token=token,
        )
        return TypeAdapter(GetPostsResponse).validate_python(resp_raw.json()), resp_raw

    @allure.step("PostsAPI | Get post by id")
    def get_post_by_id(
            self,
            token: str,
            post_id: str,
            comments_page: int = 0,
            comments_size: int = 20,
            comments_sort: str = "createdAt,asc",
    ) -> tuple[GetPostByIdResponse, httpx.Response]:
        """GET /api/v1/posts/{postId}"""
        resp = self.client.get(
            f"{APIRoutes.POSTS}/{post_id}",
            params={"page": comments_page, "size": comments_size, "sort": comments_sort},
            token=token,
        )
        return TypeAdapter(GetPostByIdResponse).validate_python(resp.json()), resp
