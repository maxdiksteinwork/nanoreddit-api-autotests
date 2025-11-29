# utils/assertions/database_state.py

from typing import Optional, Dict, Any
import allure

from utils.allure_helpers import format_attachment_name

def fetch_single_user(
    sql_client,
    email: str,
    *,
    columns: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Возвращает ровно одну запись пользователя по email или падает с понятным сообщением.
    """
    rows = get_user_by_email(sql_client, email, columns=columns)
    if len(rows) != 1:
        expected = error_message or f"Expected exactly 1 user with email {email}"
        raise AssertionError(f"{expected}; found {len(rows)}")
    return rows[0]


def get_table_count(
    sql_client,
    table_name: str,
    where_clause: Optional[str] = None,
    params: Optional[tuple] = None,
) -> int:
    if where_clause:
        sql = f"SELECT COUNT(*) as count FROM {table_name} {where_clause}"
    else:
        sql = f"SELECT COUNT(*) as count FROM {table_name}"

    result = sql_client.query(sql, params or ())
    count = result[0]["count"] if result else 0

    allure.attach(
        f"Table: {table_name}\nWhere: {where_clause or 'N/A'}\nCount: {count}",
        name=format_attachment_name(f"DB count: {table_name}"),
        attachment_type=allure.attachment_type.TEXT,
    )
    
    return count


def assert_count_unchanged(sql_client, table_name: str, count_before: int,
                           where_clause: Optional[str] = None, params: Optional[tuple] = None,
                           error_message: Optional[str] = None) -> None:
    count_after = get_table_count(sql_client, table_name, where_clause, params)

    if error_message:
        assert count_after == count_before, error_message
    else:
        assert count_after == count_before, (
            f"Expected {table_name} count to remain {count_before}, but got {count_after}"
        )


def get_user_by_email(sql_client, email: str, columns: Optional[str] = None):
    columns = columns or "id, username, email, banned_until, role"
    rows = sql_client.query(
        f"SELECT {columns} FROM users WHERE email = %s",
        (email,)
    )

    return rows


def assert_user_not_created(sql_client, email: Optional[str] = None, username: Optional[str] = None,
                            error_message: Optional[str] = None) -> None:
    if email:
        db_email = sql_client.query("SELECT id FROM users WHERE email = %s", (email,))
        assert len(db_email) == 0, error_message or f"Unexpected user created with email {email}"
    if username:
        db_username = sql_client.query("SELECT id FROM users WHERE username = %s", (username,))
        assert len(db_username) == 0, error_message or f"Unexpected user created with username {username}"
