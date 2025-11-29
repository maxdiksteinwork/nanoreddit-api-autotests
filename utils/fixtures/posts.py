# utils/fixtures/posts.py

import allure
import pytest
from models.requests.posts_requests import PublishPostPayload, AddCommentPayload

DEFAULT_COMMENTS_TO_CREATE = 5

@pytest.fixture
def create_post_get_post_id_and_token(session_posts_api, module_create_user_get_token):
    with allure.step("Prepare post"):
        token = module_create_user_get_token
        resp = session_posts_api.publish_post(token, PublishPostPayload.random())
        return resp.responseData.id, token


@pytest.fixture
def create_post_with_comments_get_post_id_and_token(session_posts_api, create_post_get_post_id_and_token):
    with allure.step("Prepare post populated with comments"):
        post_id, token = create_post_get_post_id_and_token
        comments_to_create = DEFAULT_COMMENTS_TO_CREATE
        for i in range(comments_to_create):
            session_posts_api.add_comment(
                token=token,
                post_id=post_id,
                payload=AddCommentPayload.random()
            )
        return post_id, token, comments_to_create


@pytest.fixture
def create_post_and_vote_get_post_id_and_token(session_posts_api, create_post_get_post_id_and_token):
    with allure.step("Prepare post with existing vote"):
        post_id, token = create_post_get_post_id_and_token
        session_posts_api.vote_post(token=token, post_id=post_id, value=1)
        return post_id, token


@pytest.fixture
def create_post_with_comments_ids(session_posts_api, create_post_with_comments_get_post_id_and_token):
    with allure.step("Prepare post and collect comment ids"):
        post_id, token, created_comments_amount = create_post_with_comments_get_post_id_and_token
        resp, _ = session_posts_api.get_post_by_id(
            token=token,
            post_id=post_id,
            comments_page=0,
            comments_size=created_comments_amount
        )
        comments_ids = [c.id for c in resp.responseData.comments]
        return post_id, token, comments_ids
