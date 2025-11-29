# utils/clients/sql_client.py

import json
from typing import Optional, List, Dict, Any
import allure
import psycopg2
from psycopg2.extras import RealDictCursor
from utils.allure_helpers import attach_db_query, format_attachment_name


class SQLClient:
    SENSITIVE_FIELDS = {"password", "password_hash", "token", "secret", "api_key", "jwt"}

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        self._connection_params = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
        }
        self.conn = psycopg2.connect(**self._connection_params)
        self.conn.autocommit = True

    def _ensure_connection(self):
        """восстанавливает соединение, если оно закрыто или отсутствует"""
        try:
            if self.conn is None or getattr(self.conn, "closed", True):
                self.conn = psycopg2.connect(**self._connection_params)
                self.conn.autocommit = True
        except Exception as e:
            raise RuntimeError(f"Failed to (re)establish DB connection: {e}") from e

    def _sanitize_result(self, result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sanitized = []
        for row in result:
            sanitized_row = {}
            for key, value in row.items():
                if any(sensitive in key.lower() for sensitive in self.SENSITIVE_FIELDS):
                    sanitized_row[key] = "***"
                else:
                    sanitized_row[key] = value
            sanitized.append(sanitized_row)
        return sanitized

    def query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """SELECT"""
        self._ensure_connection()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                try:
                    rows = cur.fetchall()
                    # приводим к обычным dict для совместимости
                    result = [dict(r) for r in rows]
                    sanitized_result = self._sanitize_result(result)

                    attach_db_query(
                        sql=sql,
                        params=params,
                        rows=sanitized_result,
                        name=f"SQL Query ({len(result)} rows)",
                    )

                    return result
                except psycopg2.ProgrammingError:
                    attach_db_query(sql=sql, params=params, rows=[], name="SQL query (0 rows)")
                    return []
        except psycopg2.Error as e:
            error_info = {
                "sql": sql,
                "params": params,
                "error": str(e),
                "error_type": type(e).__name__
            }
            allure.attach(
                json.dumps(error_info, indent=2),
                name=format_attachment_name("SQL query error"),
                attachment_type=allure.attachment_type.JSON,
            )
            raise RuntimeError(f"SQL query failed: {e}") from e

    def execute(self, sql: str, params: Optional[tuple] = None) -> int:
        """INSERT/UPDATE/DELETE"""
        self._ensure_connection()
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params or ())
                rowcount = cur.rowcount

                execute_info = {
                    "sql": sql,
                    "params": params,
                    "affected_rows": rowcount
                }
                allure.attach(
                    json.dumps(execute_info, indent=2),
                    name=format_attachment_name(f"SQL execute ({rowcount} rows affected)"),
                    attachment_type=allure.attachment_type.JSON,
                )

                return rowcount
        except psycopg2.Error as e:
            error_info = {
                "sql": sql,
                "params": params,
                "error": str(e),
                "error_type": type(e).__name__
            }
            allure.attach(
                json.dumps(error_info, indent=2),
                name=format_attachment_name("SQL execute error"),
                attachment_type=allure.attachment_type.JSON,
            )
            raise RuntimeError(f"SQL execution failed: {e}") from e

    def close(self):
        try:
            if hasattr(self, "conn") and self.conn and not getattr(self.conn, "closed", True):
                self.conn.close()
        except Exception as e:
            error_info = {
                "action": "close_connection",
                "error": str(e),
                "error_type": type(e).__name__,
            }
            try:
                allure.attach(
                    json.dumps(error_info, indent=2),
                    name=format_attachment_name("SQL connection close error"),
                    attachment_type=allure.attachment_type.JSON,
                )
            except Exception:
                pass
