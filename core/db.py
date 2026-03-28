import os
import json
import urllib.request
import urllib.error
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


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


def init_support_inquiry_table():
    query = """
    CREATE TABLE IF NOT EXISTS support_inquiries (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        email VARCHAR(255) NOT NULL,
        category VARCHAR(100) NOT NULL DEFAULT '일반 문의',
        subject VARCHAR(200) NOT NULL,
        message TEXT NOT NULL,
        discord_tag VARCHAR(100),
        status VARCHAR(30) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """

    with db_cursor() as (_, cur):
        cur.execute(query)


def insert_support_inquiry(name, email, category, subject, message, discord_tag=None):
    query = """
    INSERT INTO support_inquiries (name, email, category, subject, message, discord_tag)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id, name, email, category, subject, message, discord_tag, status, created_at;
    """

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute(
            query,
            (name, email, category, subject, message, discord_tag),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def send_discord_support_webhook(inquiry: dict):
    webhook_url = os.getenv("DISCORD_SUPPORT_WEBHOOK_URL", "").strip()

    if not webhook_url:
        return {
            "ok": False,
            "message": "DISCORD_SUPPORT_WEBHOOK_URL 환경변수가 설정되지 않았습니다."
        }

    created_at = inquiry.get("created_at")
    if hasattr(created_at, "strftime"):
        created_at_text = created_at.strftime("%Y-%m-%d %H:%M:%S")
    else:
        created_at_text = str(created_at)

    discord_tag = inquiry.get("discord_tag") or "-"
    message_text = inquiry.get("message") or ""

    if len(message_text) > 1000:
        message_text = message_text[:1000] + "\n...(생략)"

    payload = {
        "username": "SCRIM BOT SUPPORT",
        "embeds": [
            {
                "title": "새 문의가 접수되었습니다",
                "description": f"문의번호: **#{inquiry.get('id')}**",
                "color": 5793266,
                "fields": [
                    {"name": "문의 유형", "value": str(inquiry.get("category") or "-"), "inline": True},
                    {"name": "상태", "value": str(inquiry.get("status") or "pending"), "inline": True},
                    {"name": "접수 시간", "value": created_at_text, "inline": False},
                    {"name": "이름", "value": str(inquiry.get("name") or "-"), "inline": True},
                    {"name": "이메일", "value": str(inquiry.get("email") or "-"), "inline": True},
                    {"name": "디스코드 아이디", "value": str(discord_tag), "inline": True},
                    {"name": "문의 제목", "value": str(inquiry.get("subject") or "-"), "inline": False},
                    {"name": "문의 내용", "value": message_text, "inline": False},
                ]
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = getattr(resp, "status", 200)
            if 200 <= status_code < 300:
                return {"ok": True, "message": "디스코드 웹훅 전송 성공"}
            return {"ok": False, "message": f"디스코드 웹훅 응답 코드: {status_code}"}
    except urllib.error.HTTPError as e:
        return {"ok": False, "message": f"디스코드 웹훅 HTTP 오류: {e.code}"}
    except urllib.error.URLError as e:
        return {"ok": False, "message": f"디스코드 웹훅 URL 오류: {e.reason}"}
    except Exception as e:
        return {"ok": False, "message": f"디스코드 웹훅 전송 실패: {str(e)}"}


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


def create_premium_request(guild_id: int, applicant_name: str, amount: int, discord_tag: Optional[str] = None, memo: Optional[str] = None):
    init_premium_tables()

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            INSERT INTO premium_requests (
                guild_id, applicant_name, discord_tag, amount, memo, status
            )
            VALUES (%s, %s, %s, %s, %s, 'pending')
            RETURNING id, guild_id, applicant_name, discord_tag, amount, memo, status, created_at;
        """, (guild_id, applicant_name, discord_tag, amount, memo))
        row = cur.fetchone()
        return dict(row) if row else None


def get_premium_requests(limit: int = 200):
    init_premium_tables()

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


def approve_premium_request(request_id: int, days: int = 30, approved_by: str = "admin"):
    init_premium_tables()
    premium_until = datetime.utcnow() + timedelta(days=days)

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, status
            FROM premium_requests
            WHERE id = %s
        """, (request_id,))
        req_row = cur.fetchone()

        if not req_row:
            raise ValueError("신청 내역을 찾을 수 없습니다.")

        if req_row["status"] == "approved":
            raise ValueError("이미 승인된 신청입니다.")

        cur.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, premium_until, updated_at)
            VALUES (%s, TRUE, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                is_premium = TRUE,
                premium_until = EXCLUDED.premium_until,
                updated_at = CURRENT_TIMESTAMP
            RETURNING guild_id, is_premium, premium_until
        """, (req_row["guild_id"], premium_until))
        premium_row = cur.fetchone()

        cur.execute("""
            UPDATE premium_requests
            SET status = 'approved',
                approved_at = CURRENT_TIMESTAMP,
                approved_by = %s
            WHERE id = %s
        """, (approved_by, request_id))

        return dict(premium_row) if premium_row else None


def reject_premium_request(request_id: int, rejected_by: str = "rejected"):
    init_premium_tables()

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE premium_requests
            SET status = 'rejected',
                approved_at = CURRENT_TIMESTAMP,
                approved_by = %s
            WHERE id = %s
            RETURNING id
        """, (rejected_by, request_id))
        row = cur.fetchone()
        return dict(row) if row else None


class DB:
    DEFAULT_SETTINGS = {
        "guild_id": 0,
        "category_id": None,
        "log_channel_id": None,
        "announcement_channel_id": None,
        "result_channel_id": None,
        "voice_category_id": None,
        "queue_channel_id": None,
        "recruit_role_id": None,
        "manager_role_id": None,
        "premium_role_id": None,
        "updated_at": None,
    }

    def __init__(self):
        self.init_tables()

    @staticmethod
    def get_connection():
        return get_db_connection()

    @staticmethod
    def connect():
        return get_db_connection()

    @staticmethod
    @contextmanager
    def cursor(dict_cursor: bool = False):
        with db_cursor(dict_cursor=dict_cursor) as data:
            yield data

    @classmethod
    def init_tables(cls):
        with db_cursor() as (_, cur):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id BIGINT PRIMARY KEY,
                    category_id BIGINT,
                    log_channel_id BIGINT,
                    announcement_channel_id BIGINT,
                    result_channel_id BIGINT,
                    voice_category_id BIGINT,
                    queue_channel_id BIGINT,
                    recruit_role_id BIGINT,
                    manager_role_id BIGINT,
                    premium_role_id BIGINT,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
        init_premium_tables()

    @classmethod
    def ensure_guild_settings(cls, guild_id: int):
        cls.init_tables()

        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute("""
                INSERT INTO guild_settings (guild_id)
                VALUES (%s)
                ON CONFLICT (guild_id) DO NOTHING
                RETURNING guild_id;
            """, (guild_id,))
            cur.fetchone()

        return cls.get_settings(guild_id)

    @classmethod
    def get_settings(cls, guild_id: int) -> dict:
        cls.init_tables()

        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute("""
                SELECT
                    guild_id,
                    category_id,
                    log_channel_id,
                    announcement_channel_id,
                    result_channel_id,
                    voice_category_id,
                    queue_channel_id,
                    recruit_role_id,
                    manager_role_id,
                    premium_role_id,
                    updated_at
                FROM guild_settings
                WHERE guild_id = %s
            """, (guild_id,))
            row = cur.fetchone()

        if not row:
            cls.ensure_guild_settings(guild_id)
            with db_cursor(dict_cursor=True) as (_, cur):
                cur.execute("""
                    SELECT
                        guild_id,
                        category_id,
                        log_channel_id,
                        announcement_channel_id,
                        result_channel_id,
                        voice_category_id,
                        queue_channel_id,
                        recruit_role_id,
                        manager_role_id,
                        premium_role_id,
                        updated_at
                    FROM guild_settings
                    WHERE guild_id = %s
                """, (guild_id,))
                row = cur.fetchone()

        data = dict(cls.DEFAULT_SETTINGS)
        data["guild_id"] = guild_id

        if row:
            data.update(dict(row))

        return data

    @classmethod
    def set_setting(cls, guild_id: int, key: str, value):
        allowed_keys = {
            "category_id",
            "log_channel_id",
            "announcement_channel_id",
            "result_channel_id",
            "voice_category_id",
            "queue_channel_id",
            "recruit_role_id",
            "manager_role_id",
            "premium_role_id",
        }

        if key not in allowed_keys:
            raise ValueError(f"허용되지 않은 설정 키입니다: {key}")

        cls.ensure_guild_settings(guild_id)

        with db_cursor() as (_, cur):
            cur.execute(
                f"""
                UPDATE guild_settings
                SET {key} = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s
                """,
                (value, guild_id)
            )

    @classmethod
    def update_settings(cls, guild_id: int, **kwargs):
        if not kwargs:
            return cls.get_settings(guild_id)

        for key, value in kwargs.items():
            cls.set_setting(guild_id, key, value)

        return cls.get_settings(guild_id)

    @classmethod
    def is_premium_guild(cls, guild_id: int) -> bool:
        init_premium_tables()

        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute("""
                SELECT is_premium, premium_until
                FROM premium_guilds
                WHERE guild_id = %s
            """, (guild_id,))
            row = cur.fetchone()

        if not row:
            return False

        if not row["is_premium"]:
            return False

        premium_until = row["premium_until"]
        if premium_until is not None and premium_until < datetime.utcnow():
            return False

        return True

    @classmethod
    def execute(cls, query: str, params: tuple = ()):
        with db_cursor() as (_, cur):
            cur.execute(query, params)

    @classmethod
    def fetchone(cls, query: str, params: tuple = ()):
        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

    @classmethod
    def fetchall(cls, query: str, params: tuple = ()):
        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def init_support_inquiry_table():
        return init_support_inquiry_table()

    @staticmethod
    def insert_support_inquiry(name, email, category, subject, message, discord_tag=None):
        return insert_support_inquiry(
            name=name,
            email=email,
            category=category,
            subject=subject,
            message=message,
            discord_tag=discord_tag,
        )

    @staticmethod
    def send_discord_support_webhook(inquiry: dict):
        return send_discord_support_webhook(inquiry)

    @staticmethod
    def init_premium_tables():
        return init_premium_tables()

    @staticmethod
    def create_premium_request(guild_id: int, applicant_name: str, amount: int, discord_tag: Optional[str] = None, memo: Optional[str] = None):
        return create_premium_request(guild_id, applicant_name, amount, discord_tag, memo)

    @staticmethod
    def get_premium_requests(limit: int = 200):
        return get_premium_requests(limit)

    @staticmethod
    def approve_premium_request(request_id: int, days: int = 30, approved_by: str = "admin"):
        return approve_premium_request(request_id, days, approved_by)

    @staticmethod
    def reject_premium_request(request_id: int, rejected_by: str = "rejected"):
        return reject_premium_request(request_id, rejected_by)