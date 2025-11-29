# utils/fixtures/comments.py

import pytest
import allure
from models.requests.posts_requests import AddCommentPayload



@pytest.fixture
def create_comment_with_comment_id(session_posts_api, create_post_get_post_id_and_token):
    post_id, token = create_post_get_post_id_and_token
    with allure.step("Prepare parent comment for replies"):
        session_posts_api.add_comment(token=token, post_id=post_id, payload=AddCommentPayload.random())
        resp, _ = session_posts_api.get_post_by_id(token=token, post_id=post_id, comments_page=0, comments_size=1)
        comment_id = resp.responseData.comments[0].id
        return post_id, token, comment_id
