import uuid
import allure
import pytest

from models.requests.comments_requests import ReplyCommentPayload
from utils.assertions.api_responses import assert_api_error, assert_api_success
from utils.assertions.database_state import get_table_count, assert_count_unchanged
from utils.constants.routes import APIRoutes
from utils.allure_helpers import (
    prepare_step,
    execute_step,
    validate_api_step,
    validate_db_step,
)


# ---------------------- POST /api/v1/comments/{parentCommentId}/reply ----------------------

# ----------- позитивные тесты -----------

@allure.feature("Comments")
@allure.story("Reply comment")
@allure.severity(allure.severity_level.CRITICAL)
def test_reply_comment(session_comments_api, session_posts_api, create_comment_with_comment_id, session_sql_client):
    with prepare_step():
        post_id, token, parent_comment_id = create_comment_with_comment_id
        reply_payload = ReplyCommentPayload.random()

    with execute_step():
        resp = session_comments_api.reply_comment(
            token=token,
            parent_comment_id=parent_comment_id,
            payload=reply_payload,
        )
        reply_data = resp.responseData

    with validate_api_step():
        assert_api_success(resp)
        # проверка, что ответ действительно сохранился у родителя
        resp_post, _ = session_posts_api.get_post_by_id(
            token=token,
            post_id=post_id,
            comments_page=0,
            comments_size=1,
        )
        parent_comment = next(c for c in resp_post.responseData.comments if c.id == parent_comment_id)
        assert any(r.id == reply_data.id for r in parent_comment.replies), \
            "Reply is not attached to parent comment in API response"

    with validate_db_step():
        db_reply = session_sql_client.query(
            """
            SELECT id::text, text, parent_id::text, post_id::text
            FROM comments
            WHERE id::text = %s
            """,
            (reply_data.id,)
        )
        assert len(db_reply) == 1, f"Expected exactly 1 reply with id {reply_data.id}, found {len(db_reply)}"
        db_reply = db_reply[0]
        assert db_reply["text"] == reply_payload.text
        assert db_reply["parent_id"] == parent_comment_id
        assert db_reply["post_id"] == post_id
        assert reply_data.id == db_reply["id"]
        assert reply_data.text == db_reply["text"]


@allure.feature("Comments")
@allure.story("Reply comment | nested replies")
@allure.severity(allure.severity_level.NORMAL)
def test_reply_to_reply_nested(session_comments_api, session_posts_api, create_comment_with_comment_id,
                               session_sql_client):
    with prepare_step():
        post_id, token, parent_comment_id = create_comment_with_comment_id

    with execute_step():
        reply_lvl1_id = session_comments_api.reply_comment(
            token, parent_comment_id, ReplyCommentPayload(text="First level reply")
        ).responseData.id
        reply_lvl2_id = session_comments_api.reply_comment(
            token, reply_lvl1_id, ReplyCommentPayload(text="Second level reply")
        ).responseData.id
        reply_lvl3_id = session_comments_api.reply_comment(
            token, reply_lvl2_id, ReplyCommentPayload(text="Third level reply")
        ).responseData.id

    with validate_api_step():
        resp_post, _ = session_posts_api.get_post_by_id(post_id=post_id, token=token)
        comments = resp_post.responseData.comments
        # находим исходный комментарий
        parent_comment = next(c for c in comments if c.id == parent_comment_id)
        lvl1 = next(r for r in parent_comment.replies if r.id == reply_lvl1_id)
        lvl2 = next(r for r in lvl1.replies if r.id == reply_lvl2_id)
        lvl3 = next(r for r in lvl2.replies if r.id == reply_lvl3_id)
        # проверяем, что структура вложенности реально сохраняется
        assert lvl1.id == reply_lvl1_id, "First-level reply not found under parent comment"
        assert lvl2.id == reply_lvl2_id, "Second-level reply not found under first-level reply"
        assert lvl3.id == reply_lvl3_id, "Third-level reply not found under second-level reply"

    with validate_db_step():
        for child_id, expected_parent in (
                (reply_lvl1_id, parent_comment_id),
                (reply_lvl2_id, reply_lvl1_id),
                (reply_lvl3_id, reply_lvl2_id),
        ):
            db_comment = session_sql_client.query(
                "SELECT parent_id::text FROM comments WHERE id::text = %s",
                (child_id,)
            )
            assert len(db_comment) == 1, f"Expected exactly 1 DB row for reply {child_id}, found {len(db_comment)}"
            assert db_comment[0]["parent_id"] == expected_parent, (
                f"Expected parent_id {expected_parent} for reply {child_id}, got {db_comment[0]['parent_id']}"
            )


@allure.feature("Comments")
@allure.story("Reply comment")
@allure.severity(allure.severity_level.NORMAL)
def test_reply_comment_special_symbols(session_comments_api, create_comment_with_comment_id, session_sql_client):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        text = "🔥 Привет <b>друг</b> & welcome!"

    with execute_step():
        resp = session_comments_api.reply_comment(token, parent_comment_id, ReplyCommentPayload(text=text))
        reply_data = resp.responseData

    with validate_api_step():
        assert_api_success(resp)

    with validate_db_step():
        db_comment = session_sql_client.query(
            """
            SELECT id::text, text
            FROM comments
            WHERE id::text = %s
            """,
            (reply_data.id,)
        )
        assert len(db_comment) == 1, f"Expected reply {reply_data.id} to be persisted in DB, found {len(db_comment)}"
        db_comment = db_comment[0]
        assert db_comment["text"] == text
        assert reply_data.id == db_comment["id"]
        assert reply_data.text == db_comment["text"]


@allure.feature("Comments")
@allure.story("Reply comment")
@allure.severity(allure.severity_level.NORMAL)
def test_reply_comment_multiple_replies(session_comments_api, session_posts_api, create_comment_with_comment_id,
                                        session_sql_client):
    with prepare_step():
        post_id, token, parent_comment_id = create_comment_with_comment_id
        reply_texts = ["Первый ответ", "Второй ответ", "Третий ответ"]

    with execute_step():
        reply_ids = []
        for text in reply_texts:
            resp = session_comments_api.reply_comment(token, parent_comment_id, ReplyCommentPayload(text=text))
            assert_api_success(resp)
            reply_ids.append(resp.responseData.id)

    with validate_api_step():
        resp_post, _ = session_posts_api.get_post_by_id(token=token, post_id=post_id)
        parent_comment = next(c for c in resp_post.responseData.comments if c.id == parent_comment_id)
        replies_in_verification_response = parent_comment.replies
        assert len(replies_in_verification_response) == len(reply_texts)
        reply_ids_in_verification_response = [r.id for r in replies_in_verification_response]
        for rid in reply_ids:
            assert rid in reply_ids_in_verification_response, f"Reply ID {rid} not found in parent comment replies"

    with validate_db_step():
        db_replies = session_sql_client.query(
            """
            SELECT id::text, text
            FROM comments
            WHERE parent_id::text = %s
            """,
            (parent_comment_id,)
        )
        db_ids = [row["id"] for row in db_replies]
        for rid in reply_ids:
            assert rid in db_ids, f"Reply {rid} not found in DB under parent {parent_comment_id}"


@allure.feature("Comments")
@allure.story("Reply comment | boundary values")
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
def test_reply_comment_text_boundary_valid(session_comments_api, create_comment_with_comment_id, session_sql_client,
                                           text):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id

    with execute_step():
        resp = session_comments_api.reply_comment(token, parent_comment_id, ReplyCommentPayload(text=text))

    with validate_api_step():
        assert_api_success(resp)

    with validate_db_step():
        db_comment = session_sql_client.query("SELECT text FROM comments WHERE id::text = %s", (resp.responseData.id,))
        assert len(db_comment) == 1, (
            f"Expected exactly 1 reply with id {resp.responseData.id}, found {len(db_comment)}"
        )
        db_text = db_comment[0]["text"]
        assert db_text == text
        assert resp.responseData.text == db_text


# ----------- негативные тесты -----------

@allure.feature("Comments")
@allure.story("Reply comment | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "text",
    [
        "",  # меньше минимальной длины (0 символов)
        "C" * 256,  # больше максимальной длины (256 символов)
    ],
    ids=["too_short", "too_long"]
)
def test_reply_comment_boundary_invalid(session_comments_api, create_comment_with_comment_id, session_sql_client, text):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        count_before = get_table_count(session_sql_client, "comments", "WHERE parent_id::text = %s",
                                       (parent_comment_id,))

    with execute_step():
        resp = session_comments_api.reply_comment(token, parent_comment_id, ReplyCommentPayload(text=text))

    with validate_api_step():
        assert_api_error(resp, expected_message="validation error")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE parent_id::text = %s",
            (parent_comment_id,),
            "Expected no reply to be created with invalid text length"
        )


@allure.feature("Comments")
@allure.story("Reply comment | authorization")
@allure.severity(allure.severity_level.NORMAL)
def test_reply_comment_invalid_token(session_comments_api, create_comment_with_comment_id, session_sql_client):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        count_before = get_table_count(session_sql_client, "comments", "WHERE parent_id::text = %s",
                                       (parent_comment_id,))

    with execute_step():
        resp_invalid_token = session_comments_api.reply_comment(
            "invalid.token.value",
            parent_comment_id,
            ReplyCommentPayload(text="Test text"),
        )

    with validate_api_step():
        assert_api_error(resp_invalid_token, expected_message="access denied")

    with execute_step():
        resp_no_token = session_comments_api.client.post(
            f"{APIRoutes.COMMENTS}/{parent_comment_id}/reply",
            json={"text": "Reply text"}
        )
        data = resp_no_token.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "Access denied"

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE parent_id::text = %s",
            (parent_comment_id,),
            "Expected no reply to be created with invalid token"
        )


@allure.feature("Comments")
@allure.story("Reply comment | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "parent_comment_id",
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
def test_reply_comment_invalid_or_nonexistent_parent_id(session_comments_api, module_create_user_get_token,
                                                        session_sql_client, parent_comment_id):
    with prepare_step():
        count_before = get_table_count(session_sql_client, "comments")

    with execute_step():
        resp = session_comments_api.reply_comment(
            token=module_create_user_get_token,
            parent_comment_id=parent_comment_id,
            payload=ReplyCommentPayload(text="Trying to reply to invalid parentCommentId")
        )

    with validate_api_step():
        assert_api_error(resp, expected_message=["parent comment not found", "an error occurred"])

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            table_name="comments", count_before=count_before,
            error_message="Expected no reply to be created for invalid parentCommentId"
        )


@allure.feature("Comments")
@allure.story("Reply comment | validation errors")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": None},
        {"text": {}},
        {"text": []}
    ],
    ids=[
        "missing_text",
        "text_none",
        "text_dict",
        "text_list",
    ]
)
def test_reply_comment_invalid_body(session_comments_api, create_comment_with_comment_id, session_sql_client, payload):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        count_before = get_table_count(session_sql_client, "comments", "WHERE parent_id::text = %s",
                                       (parent_comment_id,))

    with execute_step():
        resp = session_comments_api.client.post(
            f"{APIRoutes.COMMENTS}/{parent_comment_id}/reply",
            token=token,
            json=payload
        )
        data = resp.json()

    with validate_api_step():
        assert data.get("status") == "error"
        assert data.get("error") == "an error occurred"

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE parent_id::text = %s",
            (parent_comment_id,),
            "Expected no reply to be created with invalid body"
        )


@allure.feature("Comments")
@allure.story("Reply comment | security")
@allure.severity(allure.severity_level.CRITICAL)
def test_reply_comment_xss(session_comments_api, create_comment_with_comment_id, session_sql_client, xss_payload):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        count_before = get_table_count(session_sql_client, "comments", "WHERE parent_id::text = %s",
                                       (parent_comment_id,))

    with execute_step():
        resp = session_comments_api.reply_comment(token, parent_comment_id, ReplyCommentPayload(text=xss_payload))

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE parent_id::text = %s",
            (parent_comment_id,),
            "Expected no reply to be created with XSS payload"
        )


@allure.feature("Comments")
@allure.story("Reply comment | security")
@allure.severity(allure.severity_level.CRITICAL)
def test_reply_comment_sql_injection(session_comments_api, create_comment_with_comment_id, session_sql_client,
                                     sql_injection_payload):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        count_before = get_table_count(session_sql_client, "comments", "WHERE parent_id::text = %s",
                                       (parent_comment_id,))

    with execute_step():
        resp = session_comments_api.reply_comment(
            token, parent_comment_id, ReplyCommentPayload(text=sql_injection_payload)
        )

    with validate_api_step():
        assert_api_error(resp, expected_message="access denied")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE parent_id::text = %s",
            (parent_comment_id,),
            "Expected no reply to be created with SQL injection payload"
        )


@allure.feature("Comments")
@allure.story("Reply comment | validation")
@allure.severity(allure.severity_level.MINOR)
def test_reply_comment_with_unexpected_fields(session_comments_api, session_posts_api, create_comment_with_comment_id,
                                              session_sql_client):
    with prepare_step():
        _, token, parent_comment_id = create_comment_with_comment_id
        payload = {
            "text": "Reply with extra fields",
            "foo": "bar",
            "id": 123,
            "extra": {"a": 1, "b": [1, 2, 3]},
        }

    with execute_step():
        resp = session_comments_api.reply_comment(token, parent_comment_id, payload)
        reply_data = resp.responseData

    with validate_api_step():
        assert_api_success(resp)

    with validate_db_step():
        db_reply = session_sql_client.query(
            """
            SELECT id::text, text
            FROM comments
            WHERE id::text = %s
            """,
            (reply_data.id,)
        )
        assert len(db_reply) == 1, f"Expected exactly 1 reply with id {reply_data.id}, found {len(db_reply)}"
        db_reply = db_reply[0]
        assert db_reply["text"] == payload["text"]
        assert reply_data.text == db_reply["text"]


@allure.feature("Comments")
@allure.story("Reply comment | authorization")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.parametrize("banned_token", ("session_banned_user_token", "session_banned_admin_token"))
def test_reply_comment_banned_user(session_comments_api, create_comment_with_comment_id, session_sql_client,
                                   request, banned_token):
    with prepare_step():
        _, _, parent_comment_id = create_comment_with_comment_id
        token = request.getfixturevalue(banned_token)
        count_before = get_table_count(session_sql_client, "comments", "WHERE parent_id::text = %s",
                                       (parent_comment_id,))

    with execute_step():
        resp = session_comments_api.reply_comment(
            token=token,
            parent_comment_id=parent_comment_id,
            payload=ReplyCommentPayload.random()
        )

    with validate_api_step():
        assert_api_error(resp, expected_message="user is banned")

    with validate_db_step():
        assert_count_unchanged(
            session_sql_client,
            "comments",
            count_before,
            "WHERE parent_id::text = %s",
            (parent_comment_id,),
            "Expected no reply to be created for banned user/admin"
        )
