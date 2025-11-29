# utils/constants/routes.py

from enum import StrEnum

class APIRoutes(StrEnum):
    AUTH = "/api/v1/auth"
    POSTS = "/api/v1/posts"
    PROFILE = "/api/v1/profile"
    ADMIN = "/api/v1/admin"
    COMMENTS = "/api/v1/comments"

