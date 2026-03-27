import os
import json
import urllib.request
import urllib.error
from contextlib import contextmanager
from datetime import datetime

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
                    {
                        "name": "문의 유형",
                        "value": str(inquiry.get("category") or "-"),
                        "inline": True
                    },
                    {
                        "name": "상태",
                        "value": str(inquiry.get("status") or "pending"),
                        "inline": True
                    },
                    {
                        "name": "접수 시간",
                        "value": created_at_text,
                        "inline": False
                    },
                    {
                        "name": "이름",
                        "value": str(inquiry.get("name") or "-"),
                        "inline": True
                    },
                    {
                        "name": "이메일",
                        "value": str(inquiry.get("email") or "-"),
                        "inline": True
                    },
                    {
                        "name": "디스코드 아이디",
                        "value": str(discord_tag),
                        "inline": True
                    },
                    {
                        "name": "문의 제목",
                        "value": str(inquiry.get("subject") or "-"),
                        "inline": False
                    },
                    {
                        "name": "문의 내용",
                        "value": message_text,
                        "inline": False
                    }
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