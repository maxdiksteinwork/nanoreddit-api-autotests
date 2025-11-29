# tests/test_posts.py
import uuid
import allure
import pytest

from models.requests.posts_requests import PublishPostPayload, AddCommentPayload
from utils.assertions.api_responses import assert_api_error, assert_api_success
from utils.assertions.database_state import get_table_count, assert_count_unchanged
from utils.constants.routes import APIRoutes
from utils.allure_helpers import (
    prepare_step,
    execute_step,
    validate_api_step,
    validate_db_step,
)


# ---------------------- POST /api/v1/posts/publish ----------------------

# ----------- позитивные тесты -----------

@allure.feature("Posts")
@allure.story("Publish post")
@allure.severity(allure.severity_level.CRITICAL)
def test_publish_post(module_create_user_get_token, session_posts_api, session_sql_client):
    with prepare_step():
        token = module_create_user_get_token
        payload = PublishPostPayload.random()

    with execute_step():
        resp = session_posts_api.publish_post(token, payload)
        rd = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        assert rd.id and rd.title and rd.content

    with validate_db_step():
        db_post = session_sql_client.query(
            "SELECT id::text, title, content, author_id, created_at FROM posts WHERE id::text = %s",
            (rd.id,)
        )
        assert len(db_post) == 1, f"Expected exactly 1 post with id {rd.id}, found {len(db_post)}"
        db_post = db_post[0]
        assert db_post["title"] == payload.title
        assert db_post["content"] == payload.content
        assert db_post["author_id"] is not None, "Expected user_id to be set in database"
        assert rd.id == db_post["id"]
        assert rd.title == db_post["title"]
        assert rd.content == db_post["content"]


@allure.feature("Posts")
@allure.story("Publish post | boundary values")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "title,content",
    [
        pytest.param(
            "A", "C",
            id="min title and content",
            marks=pytest.mark.doc_issue
        ),  # минимальная длина title и content = 1 [хотя в документации сказано 0 для title]
        pytest.param(
            "A" * 255, "C",
            id="max title"
        ),  # максимальная длина title = 255
        pytest.param(
            "A", "C" * 32000,
            id="max content",
            marks=pytest.mark.no_validation_for_max_value
        ),
        # верхняя граница для контента не указана, поэтому пробуем экстремальную [баг на отсутствие валидации верхних значений]
    ]
)
def test_publish_post_boundary_valid(module_create_user_get_token, session_posts_api, session_sql_client, title,
                                     content):
    with prepare_step():
        payload = PublishPostPayload(title=title, content=content)

    with execute_step():
        resp = session_posts_api.publish_post(module_create_user_get_token, payload=payload)
        rd = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        assert rd.title == title
        assert rd.content == content

    with validate_db_step():
        db_post = session_sql_client.query(
            "SELECT id::text, title, content FROM posts WHERE id::text = %s",
            (rd.id,)
        )
        assert len(db_post) == 1, f"Expected exactly 1 post with id {rd.id}, found {len(db_post)}"
        db_post = db_post[0]
        assert db_post["title"] == title
        assert db_post["content"] == content
        assert rd.id == db_post["id"]
        assert rd.title == db_post["title"]
        assert rd.content == db_post["content"]


# ----------- негативные тесты -----------

@allure.feature("Posts")
@allure.story("Publish post | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "payload",
    [
        {"content": "Some text"},  # отсутствует title
        {"title": "Some title"},  # отсутствует content
        {},  # отсутствуют оба
    ],
    ids=["no_title", "no_content", "no_title_and_content"]
)
def test_publish_post_missing_fields(module_create_user_get_token, session_posts_api, session_sql_client, payload):
    with prepare_step():
        token = module_create_user_get_token
        count_before = get_table_count(session_sql_client, "posts")

    with execute_step():
        resp = session_posts_api.publish_post(token=token, payload=payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="an error occurred")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with missing fields")


@allure.feature("Posts")
@allure.story("Publish post | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "title,content",
    [
        ("", "Some content"),
        ("Some Title", "")
    ],
    ids=["empty title", "empty content"]
)
def test_publish_post_empty_title_content(module_create_user_get_token, session_posts_api, session_sql_client, title,
                                          content):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "posts")
        payload = PublishPostPayload(title=title, content=content)

    with execute_step():
        resp = session_posts_api.publish_post(token=module_create_user_get_token, payload=payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with empty fields")


@allure.feature("Posts")
@allure.story("Publish post | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_publish_post_boundary_invalid(module_create_user_get_token, session_posts_api, session_sql_client):
    with prepare_step():
        title = "A" * 256
        content = "C"
        count_before = get_table_count(session_sql_client, "posts")

    with execute_step():
        resp = session_posts_api.publish_post(
            module_create_user_get_token,
            PublishPostPayload(title=title, content=content),
        )

    with validate_api_step():
        assert_api_error(resp, expected_message="title must be less than 255 character")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with invalid title length")


@allure.feature("Posts")
@allure.story("Publish post | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "payload",
    [
        {"title": ["List", "instead", "of", "string"], "content": "ok"},  # title — список
        {"title": "Valid title", "content": ["a", "b", "c"]},  # content — список
        {"title": None, "content": "Some text"},  # title — None
        {"title": "Valid title", "content": None},  # content — None
    ],
    ids=[
        "title_list",
        "content_list",
        "title_none",
        "content_none"
    ]
)
def test_publish_post_invalid_types(module_create_user_get_token, session_posts_api, session_sql_client, payload):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "posts")

    with execute_step():
        resp = session_posts_api.publish_post(token=module_create_user_get_token, payload=payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="an error occurred")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with invalid types")


@allure.feature("Posts")
@allure.story("Publish post | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_publish_post_invalid_token(session_posts_api, session_sql_client):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "posts")

    with execute_step():
        resp_invalid_token = session_posts_api.publish_post("invalid.token.value", PublishPostPayload.random())

    with validate_api_step():
        assert_api_error(resp_invalid_token, expected_message="access denied")

    with execute_step():
        resp_no_token = session_posts_api.client.post(
            f"{APIRoutes.POSTS}/publish",
            json={"title": "Test title", "content": "Test content"}
        )
        data = resp_no_token.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with invalid token")


@allure.feature("Posts")
@allure.story("Publish post | security")
@allure.severity(allure.severity_level.CRITICAL)
def test_publish_post_xss(module_create_user_get_token, session_posts_api, session_sql_client, xss_payload):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "posts")
        payload = PublishPostPayload(title="xss test", content=xss_payload)

    with execute_step():
        resp = session_posts_api.publish_post(module_create_user_get_token, payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with XSS payload")


@allure.feature("Posts")
@allure.story("Publish post | security")
@allure.severity(allure.severity_level.CRITICAL)
def test_publish_post_sql_injection(module_create_user_get_token, session_posts_api, session_sql_client,
                                    sql_injection_payload):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "posts")
        payload = PublishPostPayload(title="sql test", content=sql_injection_payload)

    with execute_step():
        resp = session_posts_api.publish_post(module_create_user_get_token, payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "posts", count_before,
                               error_message="Expected no post to be created with SQL injection payload")


@allure.feature("Posts")
@allure.story("Publish post | authorization")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("banned_token", ["session_banned_user_token", "session_banned_admin_token"])
def test_publish_post_banned_user(session_posts_api, request, banned_token, session_sql_client):
    with prepare_step():
        payload = PublishPostPayload.random()
        token = request.getfixturevalue(banned_token)
        count_before = get_table_count(session_sql_client, "posts")

    with execute_step():
        resp = session_posts_api.publish_post(token, payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="user is banned")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            table_name="posts",
            count_before=count_before,
            error_message="Expected no new post to be created for banned user/admin"
        )


# ---------------------- POST /api/v1/posts/{postId}/vote ----------------------

# ----------- позитивные тесты -----------

@allure.feature("Posts")
@allure.story("Vote post")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("vote_value", [1, -1])
def test_vote_post(session_posts_api, create_post_get_post_id_and_token, session_sql_client, vote_value):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token

    with execute_step():
        resp = session_posts_api.vote_post(token, post_id, vote_value)

    with validate_api_step():
        assert_api_success(resp)

    with validate_db_step():
        db_vote = session_sql_client.query("SELECT value FROM votes WHERE post_id::text = %s", (post_id,))
        assert len(db_vote) == 1, f"Expected exactly 1 vote for post {post_id}, found {len(db_vote)}"
        assert db_vote[0]["value"] == vote_value


@allure.feature("Posts")
@allure.story("Vote post")
@allure.severity(allure.severity_level.NORMAL)
def test_vote_post_update_value(session_posts_api, create_post_get_post_id_and_token, session_sql_client):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token

    with execute_step():
        first_vote = session_posts_api.vote_post(token, post_id, 1)

    with validate_api_step():
        assert_api_success(first_vote)

    with validate_db_step():
        db_vote_after_first = session_sql_client.query("SELECT value FROM votes WHERE post_id::text = %s", (post_id,))
        assert len(
            db_vote_after_first) == 1, f"Expected exactly 1 vote for post {post_id}, found {len(db_vote_after_first)}"
        assert db_vote_after_first[0]["value"] == 1

    with execute_step():
        second_vote = session_posts_api.vote_post(token, post_id, -1)

    with validate_api_step():
        assert_api_success(second_vote)

    with validate_db_step():
        db_vote_after_second = session_sql_client.query("SELECT value FROM votes WHERE post_id::text = %s", (post_id,))
        assert len(db_vote_after_second) == 1, (
            f"Expected exactly 1 vote for post {post_id}, found {len(db_vote_after_second)}"
        )
        assert db_vote_after_second[0]["value"] == -1


# ----------- негативные тесты -----------

@allure.feature("Posts")
@allure.story("Vote post | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_vote_post_invalid_token(session_posts_api, create_post_get_post_id_and_token, session_sql_client):
    with prepare_step():
        post_id, _ = create_post_get_post_id_and_token
        # проверяем количество голосов до попытки
        count_before = get_table_count(session_sql_client, "votes", "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp_invalid_token = session_posts_api.vote_post("invalid.token.value", post_id, 1)

    with validate_api_step():
        assert_api_error(resp_invalid_token, expected_message="access denied")

    with execute_step():
        resp_no_token = session_posts_api.client.post(f"{APIRoutes.POSTS}/{post_id}/vote", params={"value": 1})
        data = resp_no_token.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"

    with validate_db_step():
        # проверяем, что голос не был создан
        assert_count_unchanged(session_sql_client, "votes", count_before,
                               "WHERE post_id::text = %s", (post_id,),
                               "Expected no vote to be created with invalid token")


@allure.feature("Posts")
@allure.story("Vote post | validation errors")
@allure.severity(allure.severity_level.NORMAL)
def test_vote_nonexistent_post(session_posts_api, module_create_user_get_token, session_sql_client):
    with prepare_step():
        fake_post_id = str(uuid.uuid4())
        count_before = get_table_count(session_sql_client, "votes", "WHERE post_id::text = %s",
                                       (fake_post_id,))

    with execute_step():
        resp = session_posts_api.vote_post(module_create_user_get_token, fake_post_id, 1)

    with validate_api_step():
        assert_api_error(resp, expected_message="post not found")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "votes", count_before,
                               "WHERE post_id::text = %s", (fake_post_id,),
                               "Expected no vote to be created for nonexistent post")


@allure.feature("Posts")
@allure.story("Vote post | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("invalid_value", [0, 2, -2, "up"])
def test_vote_post_invalid_value(session_posts_api, create_post_get_post_id_and_token, session_sql_client,
                                 invalid_value):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        count_before = get_table_count(session_sql_client, "votes",
                                       "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp = session_posts_api.vote_post(token, post_id, invalid_value)

    with validate_api_step():
        assert_api_error(resp, expected_message=["an error occurred", "must be either 1 or -1"])

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "votes", count_before,
                               "WHERE post_id::text = %s", (post_id,),
                               "Expected no vote to be created with invalid value")


@allure.feature("Posts")
@allure.story("Vote post | authorization")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("banned_token", ["session_banned_user_token", "session_banned_admin_token"])
def test_vote_post_banned_user(session_posts_api, create_post_get_post_id_and_token, request, banned_token,
                               session_sql_client):
    with prepare_step():
        post_id, _ = create_post_get_post_id_and_token
        token = request.getfixturevalue(banned_token)
        count_before = get_table_count(
            session_sql_client,
            table_name="votes",
            where_clause="WHERE post_id::text = %s",
            params=(post_id,)
        )
        
    with execute_step():
        resp = session_posts_api.vote_post(token, post_id, 1)

    with validate_api_step():
        assert_api_error(resp, expected_message="user is banned")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            table_name="votes",
            count_before=count_before,
            where_clause="WHERE post_id::text = %s",
            params=(post_id,),
            error_message="Expected no vote to be created for banned user/admin"
        )


# ---------------------- POST /api/v1/posts/{postId}/addComment ----------------------

# ----------- позитивные тесты -----------

@allure.feature("Posts")
@allure.story("Add comment")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_comment(session_posts_api, create_post_get_post_id_and_token, session_sql_client):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        payload = AddCommentPayload.random()

    with execute_step():
        resp = session_posts_api.add_comment(token=token, post_id=post_id, payload=payload)

    with validate_api_step():
        assert_api_success(resp)

    with validate_db_step():
        db_comment = session_sql_client.query(
            """
            SELECT id::text, text, author_id, post_id::text, parent_id
            FROM comments
            WHERE post_id::text = %s AND text = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (post_id, payload.text)
        )
        assert len(db_comment) == 1, f"Expected exactly 1 comment for post {post_id}, found {len(db_comment)}"
        db_comment = db_comment[0]
        assert db_comment["text"] == payload.text
        assert db_comment["post_id"] == post_id
        assert db_comment["parent_id"] is None, (
            f"Expected parent_id to be None for top-level comment, got {db_comment['parent_id']}"
        )


@allure.feature("Posts")
@allure.story("Add comment | boundary values")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("A",
                     id="min text",
                     marks=pytest.mark.doc_issue
                     ),  # минимальная длина (1 символ) [хотя в документации сказано 0 для text]

        pytest.param("B" * 255,
                     id="max text"
                     )  # максимальная длина (255 символов)
    ]
)
def test_add_comment_boundary_valid(create_post_get_post_id_and_token, session_posts_api, session_sql_client, text):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        payload = AddCommentPayload(text=text)

    with execute_step():
        resp = session_posts_api.add_comment(token, post_id, payload)

    with validate_api_step():
        assert_api_success(resp)

    with validate_db_step():
        db_comment = session_sql_client.query(
            """
            SELECT id::text, text
            FROM comments
            WHERE post_id::text = %s AND text = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (post_id, payload.text)
        )
        assert len(db_comment) == 1, f"Expected exactly 1 comment for post {post_id}, found {len(db_comment)}"
        assert db_comment[0]["text"] == text


# ----------- негативные тесты -----------

@allure.feature("Posts")
@allure.story("Add comment | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "text",
    [
        "",  # меньше минимальной длины (0 символов)
        "C" * 256,  # больше максимальной длины (256 символов)
    ],
    ids=["too_short", "too_long"]
)
def test_add_comment_boundary_invalid(create_post_get_post_id_and_token, session_posts_api, session_sql_client, text):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        count_before = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp = session_posts_api.add_comment(token, post_id, AddCommentPayload(text=text))

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "comments", count_before,
                               "WHERE post_id::text = %s", (post_id,),
                               "Expected no comment to be created with invalid text length")


@allure.feature("Posts")
@allure.story("Add comment | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_add_comment_invalid_token(session_posts_api, create_post_get_post_id_and_token, session_sql_client):
    with prepare_step():
        post_id, _ = create_post_get_post_id_and_token
        count_before = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp_invalid_token = session_posts_api.add_comment(
            token="invalid.token.value",
            post_id=post_id,
            payload=AddCommentPayload.random(),
        )

    with validate_api_step():
        assert_api_error(resp_invalid_token, expected_message="access denied")

    with execute_step():
        resp_no_token = session_posts_api.client.post(
            f"{APIRoutes.POSTS}/{post_id}/addComment", json={"text": "Comment text"}
        )
        data = resp_no_token.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "comments", count_before,
                               "WHERE post_id::text = %s", (post_id,),
                               "Expected no comment to be created with invalid token")


@allure.feature("Posts")
@allure.story("Add comment | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "invalid_post_id",
    [
        str(uuid.uuid4()),  # несуществующий UUID
        "12345",  # невалидный UUID
        "",  # пустая строка
    ],
    ids=["random_uuid", "invalid_format", "empty"]
)
def test_add_comment_invalid_post_id(module_create_user_get_token, session_posts_api, session_sql_client,
                                     invalid_post_id):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (invalid_post_id,))

    with execute_step():
        resp = session_posts_api.add_comment(
            module_create_user_get_token, invalid_post_id, AddCommentPayload.random()
        )

    with validate_api_step():
        assert_api_error(resp, expected_message=["an error occurred", "post not found"])

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "comments", count_before,
                               "WHERE post_id::text = %s", (invalid_post_id,),
                               "Expected no comment to be created for invalid post_id")


@allure.feature("Posts")
@allure.story("Add comment | security")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_comment_xss(create_post_get_post_id_and_token, session_posts_api, session_sql_client, xss_payload):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        count_before = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp = session_posts_api.add_comment(token, post_id, AddCommentPayload(text=xss_payload))

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "comments", count_before,
                               "WHERE post_id::text = %s", (post_id,),
                               "Expected no comment to be created with XSS payload")


@allure.feature("Posts")
@allure.story("Add comment | security")
@allure.severity(allure.severity_level.CRITICAL)
def test_add_comment_sql_injection(create_post_get_post_id_and_token, session_posts_api, session_sql_client,
                                   sql_injection_payload):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        count_before = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp = session_posts_api.add_comment(token, post_id, AddCommentPayload(text=sql_injection_payload))

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        assert_count_unchanged(session_sql_client, "comments", count_before,
                               "WHERE post_id::text = %s", (post_id,),
                               "Expected no comment to be created with SQL injection payload")


@allure.feature("Posts")
@allure.story("Add comment | authorization")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("banned_token", ("session_banned_user_token", "session_banned_admin_token"))
def test_add_comment_banned_user(session_posts_api, create_post_get_post_id_and_token, session_sql_client,
                                 request, banned_token):
    with prepare_step():
        post_id, _ = create_post_get_post_id_and_token
        token = request.getfixturevalue(banned_token)
        payload = AddCommentPayload.random()
        count_before = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))

    with execute_step():
        resp = session_posts_api.add_comment(token=token, post_id=post_id, payload=payload)

    with validate_api_step():
        assert_api_error(resp, expected_message="user is banned")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE post_id::text = %s",
            (post_id,),
            "Expected no comment to be created for banned user/admin"
        )


# ---------------------- GET /api/v1/posts ----------------------

# ----------- позитивные тесты -----------

@allure.feature("Posts")
@allure.story("Get posts")
@allure.severity(allure.severity_level.CRITICAL)
def test_get_posts(session_posts_api, module_create_user_get_token, session_sql_client):
    with prepare_step():
        token = module_create_user_get_token

    with execute_step():
        resp, _ = session_posts_api.get_posts(token)

    with validate_api_step():
        assert_api_success(resp)
        content = resp.responseData.content
        assert content, "Expected API to return at least one post"

    with validate_db_step():
        api_ids = [post.id for post in content]
        placeholders = ", ".join(["%s"] * len(api_ids))
        db_rows = session_sql_client.query(f"""SELECT id::text FROM posts WHERE id IN ({placeholders})""",
                                           tuple(api_ids))
        db_ids = [row["id"] for row in db_rows]
        assert len(db_ids) == len(api_ids), f"API returned IDs not found in DB. api_ids={api_ids}, db_ids={db_ids}"
        assert set(db_ids) == set(api_ids), f"Mismatch between API post IDs and DB IDs. api_ids={api_ids}, db_ids={db_ids}"


@allure.feature("Posts")
@allure.story("Get posts | pagination")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize("page,size", [(0, 1), (1, 5), (2, 10)])
def test_get_posts_pagination(session_posts_api, module_create_user_get_token, session_sql_client, page, size):
    with prepare_step():
        token = module_create_user_get_token

    with execute_step():
        resp, _ = session_posts_api.get_posts(token=token, page=page, size=size)

    with validate_api_step():
        assert_api_success(resp)
        assert resp.responseData.pageNumber == page
        assert resp.responseData.pageSize == size

    with validate_db_step():
        api_ids = [post.id for post in resp.responseData.content]
        placeholders = ", ".join(["%s"] * len(api_ids))
        db_rows = session_sql_client.query(f"""SELECT id::text FROM posts WHERE id IN ({placeholders})""",
                                           tuple(api_ids))
        db_ids = [row["id"] for row in db_rows]
        assert len(db_ids) == len(api_ids), (
            f"Expected DB to return {len(api_ids)} posts for page={page}, size={size}; got {len(db_ids)}"
        )
        assert set(db_ids) == set(api_ids)


@allure.feature("Posts")
@allure.story("Get posts | sorting")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "sort_field,sort_order",
    [
        ("id", "desc"),
        ("createdAt", "asc"),
        ("createdAt", "desc"),
    ],
    ids=["id_desc", "createdAt_asc", "createdAt_desc"]
)
def test_get_posts_sorting(module_create_user_get_token, session_posts_api, session_sql_client, sort_field,
                           sort_order):  # всегда делает DESC CREATED AT
    """
    Создаём несколько постов одним пользователем, забираем ожидаемый порядок из БД
    (ORDER BY created_at ASC) и сравниваем с результатом GET /api/v1/posts?sort=createdAt,asc
    """
    with prepare_step():
        posts_to_create = 5
        # создаем посты
        created_ids = []
        for i in range(posts_to_create):
            title = f"Title for post #{i}"
            content = f"Content for post #{i} - {uuid.uuid4().hex}"
            resp = session_posts_api.publish_post(module_create_user_get_token,
                                                  PublishPostPayload(title=title, content=content))
            assert_api_success(resp)
            post_id = resp.responseData.id
            assert post_id, f"No id in create response: {resp}"
            created_ids.append(post_id)
        allure.attach("\n".join(created_ids), name="Created Post IDs", attachment_type=allure.attachment_type.TEXT)

    with validate_db_step():
        # маппинг имени поля из API на SQL-столбец
        sort_column = {"id": "id", "createdAt": "created_at"}[sort_field]

        # тянем посты из бд
        placeholders = ", ".join(["%s"] * len(created_ids))
        sql = f"""
            SELECT id::text, created_at
            FROM posts
            WHERE id IN ({placeholders})
            ORDER BY {sort_column} {sort_order.upper()}
        """
        rows = session_sql_client.query(sql, tuple(created_ids))
        # rows — список dict с ключами 'id' и 'created_at'
        db_ordered_ids = [r["id"] for r in rows]
        assert set(db_ordered_ids) == set(created_ids), (
            "DB did not return the same set of created post IDs. "
            f"created_ids={created_ids}, db_ids={db_ordered_ids}"
        )

    with execute_step():
        # тянем посты из API
        resp_api, _ = session_posts_api.get_posts(
            token=module_create_user_get_token,
            page=0,
            size=posts_to_create,
            sort=f"{sort_field},{sort_order}"
        )

    with validate_api_step():
        assert_api_success(resp_api)
        content = resp_api.responseData.content
        api_ordered_ids = [p.id for p in content]

    with validate_db_step():
        allure.attach(
            f"DB Ordered IDs:\n{db_ordered_ids}\n\nAPI Ordered IDs:\n{api_ordered_ids}",
            name="Sorting Comparison",
            attachment_type=allure.attachment_type.TEXT
        )
        # сравниваем порядок постов из БД и из API
        assert api_ordered_ids == db_ordered_ids, (
            f"Sorting mismatch for sort={sort_field},{sort_order}.\n"
            f"DB order:  {db_ordered_ids}\n"
            f"API order: {api_ordered_ids}"
        )


@allure.feature("Posts")
@allure.story("Get posts | optional parameters")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.parametrize(
    "missing_param",
    ["page", "size", "sort"]
)
def test_get_posts_missing_params(session_posts_api, module_create_user_get_token, missing_param):
    with prepare_step():
        params = {"page": 0, "size": 20, "sort": "createdAt,asc"}
        params.pop(missing_param, None)

    with execute_step():
        resp_raw = session_posts_api.client.get(
            "/api/v1/posts",
            token=module_create_user_get_token,
            params=params,
        )
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)
        data = resp_raw.json()

    with validate_api_step():
        assert data.get("status") == "ok", f"Unexpected response when missing {missing_param}: {data}"
        assert "content" in data["responseData"], "Missing 'content' in responseData"


# ----------- негативные тесты -----------

@allure.feature("Posts")
@allure.story("Get posts | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "page, size",
    [
        (-1, 10),
        (0, 0),
        (1, -10),
        ("abc", 10),
        (1, "ten"),
    ],
    ids=[
        "negative_page",
        "zero_size",
        "negative_size",
        "page_not_int",
        "size_not_int",
    ]
)
def test_get_posts_invalid_pagination(session_posts_api, module_create_user_get_token, page, size):
    with prepare_step():
        token=module_create_user_get_token

    with execute_step():
        resp, _ = session_posts_api.get_posts(token=token, page=page, size=size)

    with validate_api_step():
        assert_api_success(resp)


@allure.feature("Posts")
@allure.story("Get posts | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "sort_param, expect_error",
    [
        ("unknownField,asc", True),  # несуществующее поле — ошибка
        ("id,invalidDirection", True),  # невалидное направление — ошибка
        ("id", False),  # без указания направления — OK
        ("", False),  # пустая строка — OK
        (None, False),  # null значение — OK
    ],
    ids=[
        "unknown_field",
        "invalid_direction",
        "missing_direction",
        "empty_string",
        "none_value",
    ],
)
def test_get_posts_invalid_sort(session_posts_api, module_create_user_get_token, sort_param, expect_error):
    with prepare_step():
        token = module_create_user_get_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_posts(token=token, sort=sort_param)
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)

    with validate_api_step():
        if expect_error:
            assert_api_error(resp, expected_message="an error occurred")
        else:
            assert_api_success(resp)
            assert resp.responseData.content


@allure.feature("Posts")
@allure.story("Get posts | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_get_posts_invalid_token(session_posts_api):
    with execute_step():
        resp1, _ = session_posts_api.get_posts(token="invalid.token.value")

    with validate_api_step():
        assert_api_error(resp1, expected_message="access denied")

    with execute_step():
        resp2 = session_posts_api.client.get(APIRoutes.POSTS)
        data = resp2.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"


@allure.feature("Posts")
@allure.story("Get posts | optional parameters")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.parametrize(
    "extra_params",
    [
        {"unknown": "123"},
        {"sort": "id,desc", "unexpected_param": "123"}
    ]
)
def test_get_posts_unknown_params(session_posts_api, module_create_user_get_token, extra_params):
    with prepare_step():
        token = module_create_user_get_token

    with execute_step():
        resp = session_posts_api.client.get(
            "/api/v1/posts",
            token=token,
            params=extra_params,
        )
        allure.attach(str(resp.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)
        data = resp.json()

    with validate_api_step():
        assert data.get("status") == "ok", f"Unexpected response for params {extra_params}: {data}"
        assert "content" in data["responseData"], "Response missing 'content' field"


# ---------------------- GET /api/v1/posts/{postId} ----------------------

# ----------- позитивные тесты -----------

@allure.feature("Posts")
@allure.story("Get post by ID")
@allure.severity(allure.severity_level.CRITICAL)
def test_get_post_without_comments(session_posts_api, create_post_get_post_id_and_token, session_sql_client):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_post_by_id(token=token, post_id=post_id)
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)
        rd = resp.responseData
        post = rd.post

    with validate_api_step():
        assert_api_success(resp)
        assert post.id == post_id
        assert post.title and post.content
        assert rd.comments == [], f"Expected no comments, got: {rd.comments}"
        assert rd.hasMoreComments is False

    with validate_db_step():
        db_post = session_sql_client.query("SELECT id::text, title, content FROM posts WHERE id::text = %s", (post_id,))
        assert len(db_post) == 1, f"Expected exactly 1 post with id {post_id}, found {len(db_post)}"
        db_post = db_post[0]
        assert db_post["id"] == post.id
        assert db_post["title"] == post.title
        assert db_post["content"] == post.content
        comments_count = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))
        assert comments_count == 0, f"Expected no comments in DB for post {post_id}, found {comments_count}"


@allure.feature("Posts")
@allure.story("Get post by ID | pagination")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "page,size,expected_count,has_more",
    [
        (0, 1, 1, True),
        (0, 2, 2, True),
        (1, 2, 2, True),
        (2, 2, 1, False),
        (0, 5, 5, False),
        (4, 1, 1, False)
    ]
)
def test_get_post_with_comments_pagination(session_posts_api, create_post_with_comments_get_post_id_and_token,
                                           session_sql_client, page, size, expected_count, has_more):
    with prepare_step():
        post_id, token, _ = create_post_with_comments_get_post_id_and_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_post_by_id(
            token=token,
            post_id=post_id,
            comments_page=page,
            comments_size=size,
        )
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)

    with validate_api_step():
        assert_api_success(resp)
        comments = resp.responseData.comments
        assert len(comments) == expected_count
        assert resp.responseData.hasMoreComments == has_more

    with validate_db_step():
        db_rows = session_sql_client.query(
            """SELECT id::text FROM comments WHERE post_id::text = %s ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            (post_id, size, page * size)
        )
        db_ids = [row["id"] for row in db_rows]
        api_ids = [c.id for c in comments]
        assert api_ids == db_ids, f"Comments pagination mismatch.\nAPI IDs: {api_ids}\nDB IDs: {db_ids}"
        total_comments = get_table_count(session_sql_client, "comments", "WHERE post_id::text = %s", (post_id,))
        expected_has_more = (page + 1) * size < total_comments
        assert expected_has_more == resp.responseData.hasMoreComments, (
            f"hasMoreComments mismatch. DB expects {expected_has_more}, API returned {resp.responseData.hasMoreComments}"
        )


@allure.feature("Posts")
@allure.story("Get post by ID")
@allure.severity(allure.severity_level.NORMAL)
def test_get_post_vote_score_present_with_updated_vote(session_posts_api, create_post_and_vote_get_post_id_and_token,
                                                       session_sql_client):
    with prepare_step():
        post_id, token = create_post_and_vote_get_post_id_and_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_post_by_id(token=token, post_id=post_id)
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)

    with validate_api_step():
        assert_api_success(resp)
        vote_score = resp.responseData.voteScore
        assert vote_score != 0, f"Expected score > 0 after vote, got: {vote_score}"

    with validate_db_step():
        db_vote_score = session_sql_client.query(
            "SELECT COALESCE(SUM(value), 0) AS score FROM votes WHERE post_id::text = %s",
            (post_id,)
        )[0]["score"]
        assert vote_score == db_vote_score


@allure.feature("Posts")
@allure.story("Get post by ID | optional parameters")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.parametrize(
    "missing_param",
    ["page", "size", "sort"],
)
def test_get_post_missing_comment_params(session_posts_api, create_post_get_post_id_and_token, missing_param):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token
        params = {"page": 0, "size": 20, "sort": "createdAt,asc"}
        params.pop(missing_param, None)

    with execute_step():
        resp = session_posts_api.client.get(
            f"/api/v1/posts/{post_id}",
            token=token,
            params=params
        )
        allure.attach(str(resp.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)
        data = resp.json()

    with validate_api_step():
        assert data.get("status") == "ok"
        assert "comments" in data.get("responseData")


@allure.feature("Posts")
@allure.story("Get post by ID | sorting")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "sort_field,sort_order",
    [
        ("id", "desc"),
        ("createdAt", "asc"),
        ("createdAt", "desc"),
    ],
    ids=["id_desc", "createdAt_asc", "createdAt_desc"]
)
def test_get_post_comments_sorting(create_post_with_comments_ids, session_posts_api,
                                   session_sql_client, sort_field, sort_order):
    with prepare_step():
        post_id, token, created_comments_ids = create_post_with_comments_ids
        allure.attach("\n".join(created_comments_ids), name="Created Comment IDs",
                      attachment_type=allure.attachment_type.TEXT)

    with validate_db_step():
        # маппинг имени поля из API на SQL-столбец
        sort_column = {"id": "id", "createdAt": "created_at"}[sort_field]

        # тянем комментарии из БД
        placeholders = ", ".join(["%s"] * len(created_comments_ids))
        sql = f"""
            SELECT id::text, created_at
            FROM comments
            WHERE id IN ({placeholders}) AND post_id = %s
            ORDER BY {sort_column} {sort_order.upper()}
        """
        rows = session_sql_client.query(sql, tuple(created_comments_ids + [post_id]))
        db_ordered_ids = [r["id"] for r in rows]
        assert set(db_ordered_ids) == set(created_comments_ids), (
            "DB did not return the same set of created post IDs. "
            f"created_ids={created_comments_ids}, db_ids={db_ordered_ids}"
        )

    with execute_step():
        # тянем комментарии через API с нужной сортировкой
        resp_api_sorted, _ = session_posts_api.get_post_by_id(
            token=token,
            post_id=post_id,
            comments_page=0,
            comments_size=len(created_comments_ids),
            comments_sort=f"{sort_field},{sort_order}"
        )

    with validate_api_step():
        assert_api_success(resp_api_sorted)
        api_ordered_ids = [c.id for c in resp_api_sorted.responseData.comments]

    with validate_db_step():
        allure.attach(
            f"DB Ordered IDs:\n{db_ordered_ids}\n\nAPI Ordered IDs:\n{api_ordered_ids}",
            name="Comments Sorting Comparison",
            attachment_type=allure.attachment_type.TEXT
        )
        assert api_ordered_ids == db_ordered_ids, (
            f"Sorting mismatch for comments sort={sort_field},{sort_order}\n"
            f"DB:  {db_ordered_ids}\nAPI: {api_ordered_ids}"
        )


# ----------- негативные тесты -----------

@allure.feature("Posts")
@allure.story("Get post by ID | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "post_id",
    [
        # 1. валидный UUID, но его нет в БД
        str(uuid.uuid4()),
        # 2. некорректный формат UUID
        "123",
        "abc",
        "",
        "!@#"
    ]
)
def test_get_post_invalid_or_nonexistent(session_posts_api, module_create_user_get_token, post_id):
    with prepare_step():
        token = module_create_user_get_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_post_by_id(token=token, post_id=post_id)
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)

    with validate_api_step():
        assert_api_error(resp, expected_message=["an error occurred", "post not found"])


@allure.feature("Posts")
@allure.story("Get post by ID | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_get_post_invalid_token(session_posts_api, create_post_get_post_id_and_token):
    with prepare_step():
        post_id, _ = create_post_get_post_id_and_token

    with execute_step():
        resp_invalid_token, _ = session_posts_api.get_post_by_id(token="invalid.token.value", post_id=post_id)

    with validate_api_step():
        assert_api_error(resp_invalid_token, expected_message="access denied")

    with execute_step():
        resp_no_token = session_posts_api.client.get(f"{APIRoutes.POSTS}/{post_id}")
        data = resp_no_token.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"


@allure.feature("Posts")
@allure.story("Get post by ID | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "comments_page, comments_size",
    [
        (-1, 10),
        (0, 0),
        (0, -10),
        ("abc", 10),
        (0, "ten"),
    ],
    ids=[
        "negative_page",
        "zero_size",
        "negative_size",
        "page_not_int",
        "size_not_int",
    ]
)
def test_get_post_invalid_comments_pagination(session_posts_api, create_post_with_comments_get_post_id_and_token,
                                              comments_page, comments_size):
    with prepare_step():
        post_id, token, _ = create_post_with_comments_get_post_id_and_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_post_by_id(
            token=token,
            post_id=post_id,
            comments_page=comments_page,
            comments_size=comments_size,
        )
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)

    with validate_api_step():
        assert_api_success(resp)


@allure.feature("Posts")
@allure.story("Get post by ID | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "comments_sort, expect_error",
    [
        ("unknownField,asc", True),  # несуществующее поле — ошибка
        ("id,invalidDirection", True),  # невалидное направление — ошибка
        ("id", False),  # без указания направления — OK
        ("", False),  # пустая строка — OK
        (None, False),  # null значение — OK
    ],
    ids=[
        "unknown_field",
        "invalid_direction",
        "missing_direction",
        "empty_string",
        "none_value",
    ]
)
def test_get_post_invalid_comments_sort(session_posts_api, create_post_with_comments_get_post_id_and_token,
                                        comments_sort, expect_error):
    with prepare_step():
        post_id, token, _ = create_post_with_comments_get_post_id_and_token

    with execute_step():
        resp, resp_raw = session_posts_api.get_post_by_id(token=token, post_id=post_id, comments_sort=comments_sort)
        allure.attach(str(resp_raw.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)

    with validate_api_step():
        if expect_error:
            assert_api_error(resp, expected_message="an error occurred")
        else:
            assert_api_success(resp)


@allure.feature("Posts")
@allure.story("Get post by ID | optional parameters")
@allure.severity(allure.severity_level.MINOR)
@pytest.mark.parametrize(
    "extra_params",
    [
        {"unknown": "123"},
        {"sort": "id,desc", "unexpected_param": "123"},
    ]
)
def test_get_post_unknown_params(session_posts_api, create_post_get_post_id_and_token, extra_params):
    with prepare_step():
        post_id, token = create_post_get_post_id_and_token

    with execute_step():
        resp = session_posts_api.client.get(
            f"{APIRoutes.POSTS}/{post_id}",
            token=token,
            params=extra_params
        )
        allure.attach(str(resp.request.url), name="Request URL", attachment_type=allure.attachment_type.TEXT)
        data = resp.json()

    with validate_api_step():
        assert data.get("status") == "ok", f"Unexpected response for params {extra_params}: {data}"
        assert "post" in data.get("responseData", {}), "Response missing 'post' field"
