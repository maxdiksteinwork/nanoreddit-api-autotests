# models/responses/posts_responses.py

from typing import Literal, Union, List
from pydantic import BaseModel, Field
from models.responses.base_responses import BaseResponse, ErrorResponse


class PostData(BaseModel):
    id: str
    title: str
    content: str
    author: str
    createdAt: str


class CommentReply(BaseModel):
    id: str
    text: str
    author: str
    createdAt: str
    replies: List["CommentReply"] = Field(default_factory=list)  # рекурсивные ответы


class CommentData(BaseModel):
    id: str
    text: str
    author: str
    createdAt: str
    replies: List[CommentReply] = Field(default_factory=list)


# ---------- /api/v1/posts/publish ----------

class PublishPostResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: PostData


PublishPostResponse = Union[PublishPostResponseOK, ErrorResponse]


# ---------- /api/v1/posts/{postId}/vote ----------

class VotePostResponseOK(BaseResponse):
    status: Literal["ok"]


VotePostResponse = Union[VotePostResponseOK, ErrorResponse]


# ---------- /api/v1/posts/{postId}/addComment ----------

class AddCommentResponseOK(BaseResponse):
    status: Literal["ok"]


AddCommentResponse = Union[AddCommentResponseOK, ErrorResponse]


# ---------- /api/v1/posts ----------

class PostsListData(BaseModel):
    content: List[PostData]
    pageNumber: int
    pageSize: int
    totalElements: int
    totalPages: int


class GetPostsResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: PostsListData


GetPostsResponse = Union[GetPostsResponseOK, ErrorResponse]


# ---------- /api/v1/posts/{postId} ----------
class GetPostByIdData(BaseModel):
    post: PostData
    comments: List[CommentData] = Field(default_factory=list)
    voteScore: int
    hasMoreComments: bool


class GetPostByIdResponseOK(BaseResponse):
    status: Literal["ok"]
    responseData: GetPostByIdData


GetPostByIdResponse = Union[GetPostByIdResponseOK, ErrorResponse]
