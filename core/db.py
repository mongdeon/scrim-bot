import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import RealDictCursor


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_db_connection():
    database_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("PGDATABASE_URL")
    )

    if not database_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

    database_url = _normalize_database_url(database_url)
    return psycopg2.connect(database_url)


@contextmanager
def db_cursor(dict_cursor: bool = False):
    conn = get_db_connection()
    cur = None

    try:
        if dict_cursor:
            cur = conn.cursor(cursor_factory=RealDictCursor)
        else:
            cur = conn.cursor()

        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()


def init_premium_tables():
    with db_cursor() as (_, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS premium_requests (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                applicant_name VARCHAR(100) NOT NULL,
                discord_tag VARCHAR(100),
                amount INTEGER NOT NULL,
                memo TEXT,
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by VARCHAR(100)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS premium_guilds (
                guild_id BIGINT PRIMARY KEY,
                is_premium BOOLEAN NOT NULL DEFAULT FALSE,
                premium_until TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)


def create_premium_request(
    guild_id: int,
    applicant_name: str,
    discord_tag: str | None,
    amount: int,
    memo: str | None,
):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            INSERT INTO premium_requests (
                guild_id, applicant_name, discord_tag, amount, memo, status
            )
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING id;
        """, (
            guild_id,
            applicant_name,
            discord_tag,
            amount,
            memo,
        ))
        row = cur.fetchone()
        return dict(row) if row else None


def get_premium_requests(limit: int = 200):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                id,
                guild_id,
                applicant_name,
                discord_tag,
                amount,
                memo,
                status,
                created_at,
                approved_at,
                approved_by
            FROM premium_requests
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def upsert_premium_guild(guild_id: int, days: int):
    premium_until = utc_now_naive() + timedelta(days=days)

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, premium_until, updated_at)
            VALUES (%s, TRUE, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                is_premium = TRUE,
                premium_until = EXCLUDED.premium_until,
                updated_at = CURRENT_TIMESTAMP
            RETURNING guild_id, is_premium, premium_until, updated_at;
        """, (guild_id, premium_until))
        row = cur.fetchone()
        return dict(row) if row else None


def approve_premium_request(request_id: int, days: int, approved_by: str = "admin"):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, status
            FROM premium_requests
            WHERE id = %s
        """, (request_id,))
        req_row = cur.fetchone()

        if not req_row:
            return {
                "ok": False,
                "message": "신청 내역을 찾을 수 없습니다.",
                "status_code": 404,
            }

        if req_row["status"] == "approved":
            return {
                "ok": False,
                "message": "이미 승인된 신청입니다.",
                "status_code": 400,
            }

        premium_until = utc_now_naive() + timedelta(days=days)

        cur.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, premium_until, updated_at)
            VALUES (%s, TRUE, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                is_premium = TRUE,
                premium_until = EXCLUDED.premium_until,
                updated_at = CURRENT_TIMESTAMP
            RETURNING guild_id, is_premium, premium_until, updated_at;
        """, (req_row["guild_id"], premium_until))
        premium_row = cur.fetchone()

        cur.execute("""
            UPDATE premium_requests
            SET status = 'approved',
                approved_at = CURRENT_TIMESTAMP,
                approved_by = %s
            WHERE id = %s
        """, (approved_by, request_id))

        return {
            "ok": True,
            "message": "프리미엄이 활성화되었습니다.",
            "data": dict(premium_row) if premium_row else None,
            "status_code": 200,
        }


def reject_premium_request(request_id: int):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE premium_requests
            SET status = 'rejected',
                approved_at = CURRENT_TIMESTAMP,
                approved_by = 'rejected'
            WHERE id = %s
            RETURNING id;
        """, (request_id,))
        row = cur.fetchone()

        if not row:
            return {
                "ok": False,
                "message": "신청 내역을 찾을 수 없습니다.",
                "status_code": 404,
            }

        return {
            "ok": True,
            "message": "프리미엄 신청이 거절 처리되었습니다.",
            "data": dict(row),
            "status_code": 200,
        }


def cleanup_expired_premium_guilds():
    now_dt = utc_now_naive()

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE premium_guilds
            SET is_premium = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE is_premium = TRUE
              AND premium_until IS NOT NULL
              AND premium_until < %s
            RETURNING guild_id;
        """, (now_dt,))
        rows = cur.fetchall()

    return [row["guild_id"] for row in rows]


def get_active_premium_guilds(limit: int = 200):
    cleanup_expired_premium_guilds()

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT guild_id, is_premium, premium_until, updated_at
            FROM premium_guilds
            WHERE is_premium = TRUE
            ORDER BY premium_until ASC NULLS LAST
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    return [dict(row) for row in rows]


def count_active_premium_guilds() -> int:
    cleanup_expired_premium_guilds()

    with db_cursor() as (_, cur):
        cur.execute("""
            SELECT COUNT(*)
            FROM premium_guilds
            WHERE is_premium = TRUE
        """)
        row = cur.fetchone()
        return int(row[0]) if row else 0


def is_guild_premium(guild_id: int):
    cleanup_expired_premium_guilds()

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT is_premium, premium_until
            FROM premium_guilds
            WHERE guild_id = %s
        """, (guild_id,))
        row = cur.fetchone()

    if not row:
        return False, None

    if not row["is_premium"]:
        return False, row["premium_until"]

    premium_until = row["premium_until"]
    if premium_until is not None and premium_until < utc_now_naive():
        with db_cursor() as (_, cur):
            cur.execute("""
                UPDATE premium_guilds
                SET is_premium = FALSE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s
            """, (guild_id,))
        return False, premium_until

    return True, premium_until


class DB:
    @staticmethod
    def get_connection():
        return get_db_connection()

    @staticmethod
    def connect():
        return get_db_connection()

    @staticmethod
    def cursor(dict_cursor: bool = False):
        return db_cursor(dict_cursor=dict_cursor)

    @staticmethod
    def execute(query: str, params=None, dict_cursor: bool = False):
        with db_cursor(dict_cursor=dict_cursor) as (_, cur):
            cur.execute(query, params or ())
            return cur

    @staticmethod
    def fetchone(query: str, params=None, dict_cursor: bool = True):
        with db_cursor(dict_cursor=dict_cursor) as (_, cur):
            cur.execute(query, params or ())
            row = cur.fetchone()
            if dict_cursor and row is not None:
                return dict(row)
            return row

    @staticmethod
    def fetchall(query: str, params=None, dict_cursor: bool = True):
        with db_cursor(dict_cursor=dict_cursor) as (_, cur):
            cur.execute(query, params or ())
            rows = cur.fetchall()
            if dict_cursor:
                return [dict(row) for row in rows]
            return rows