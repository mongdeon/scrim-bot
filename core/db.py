import os
import json
import random
import string
import urllib.request
import urllib.error
import re
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


def generate_party_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


PLAN_ORDER = {
    "free": 0,
    "supporter": 1,
    "pro": 2,
    "clan": 3,
}

PLAN_LABELS = {
    "free": "무료",
    "supporter": "서포터",
    "pro": "프로",
    "clan": "클랜",
}

DEFAULT_CLAN_BADGE = "👑 CLAN"
DEFAULT_CLAN_COLOR = "#8b5cf6"

DEFAULT_CLAN_INTRO = "우리 클랜만의 브랜딩과 공지 템플릿이 적용된 서버입니다."

DEFAULT_CLAN_START_TEMPLATE = """{badge} {brand_name} 내전 시작!
게임: {game}
채널: {channel}
진행: {mode_text}
A팀: {team_a}
B팀: {team_b}
차이: {difference}"""

DEFAULT_CLAN_RESULT_TEMPLATE = """{badge} {brand_name} 경기 결과
게임: {game}
승리팀: {winner_team}
A팀 평균: {avg_a}
B팀 평균: {avg_b}
채널: {channel}"""

def normalize_plan_key(plan_key: Optional[str]) -> str:
    key = (plan_key or "free").strip().lower()
    aliases = {
        "무료": "free", "free": "free",
        "서포터": "supporter", "supporter": "supporter",
        "프로": "pro", "pro": "pro",
        "클랜": "clan", "clan": "clan",
    }
    return aliases.get(key, "free")


def get_plan_label(plan_key: Optional[str]) -> str:
    return PLAN_LABELS.get(normalize_plan_key(plan_key), "무료")


def plan_at_least(current_plan_key: Optional[str], required_plan_key: Optional[str]) -> bool:
    current_value = PLAN_ORDER.get(normalize_plan_key(current_plan_key), 0)
    required_value = PLAN_ORDER.get(normalize_plan_key(required_plan_key), 0)
    return current_value >= required_value


def sanitize_brand_color(color: Optional[str]) -> str:
    raw = (color or DEFAULT_CLAN_COLOR).strip()
    if not raw:
        return DEFAULT_CLAN_COLOR
    if not raw.startswith('#'):
        raw = '#' + raw
    if re.fullmatch(r'#[0-9a-fA-F]{6}', raw):
        return raw.lower()
    return DEFAULT_CLAN_COLOR


# -------------------------
# Guild registry
# -------------------------
def init_guild_registry_table():
    with db_cursor() as (_, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS guild_registry (
                guild_id BIGINT PRIMARY KEY,
                guild_name VARCHAR(200),
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def register_guild(guild_id: int, guild_name: Optional[str] = None):
    init_guild_registry_table()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            INSERT INTO guild_registry (guild_id, guild_name, is_active, joined_at, updated_at)
            VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                guild_name = COALESCE(EXCLUDED.guild_name, guild_registry.guild_name),
                is_active = TRUE,
                updated_at = CURRENT_TIMESTAMP
            RETURNING guild_id, guild_name, is_active, joined_at, updated_at
        """, (guild_id, guild_name))
        row = cur.fetchone()
        return dict(row) if row else None


def deactivate_guild(guild_id: int):
    init_guild_registry_table()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE guild_registry
            SET is_active = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = %s
            RETURNING guild_id, guild_name, is_active, joined_at, updated_at
        """, (guild_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_registered_guilds(active_only: bool = False):
    init_guild_registry_table()
    with db_cursor(dict_cursor=True) as (_, cur):
        if active_only:
            cur.execute("""
                SELECT guild_id, guild_name, is_active, joined_at, updated_at
                FROM guild_registry
                WHERE is_active = TRUE
                ORDER BY guild_name ASC NULLS LAST, guild_id ASC
            """)
        else:
            cur.execute("""
                SELECT guild_id, guild_name, is_active, joined_at, updated_at
                FROM guild_registry
                ORDER BY guild_name ASC NULLS LAST, guild_id ASC
            """)
        return [dict(row) for row in cur.fetchall()]


# -------------------------
# Support
# -------------------------
def init_support_inquiry_table():
    with db_cursor() as (_, cur):
        cur.execute("""
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
            )
        """)


def insert_support_inquiry(name, email, category, subject, message, discord_tag=None):
    init_support_inquiry_table()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            INSERT INTO support_inquiries (name, email, category, subject, message, discord_tag)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, email, category, subject, message, discord_tag, status, created_at
        """, (name, email, category, subject, message, discord_tag))
        row = cur.fetchone()
        return dict(row) if row else None


def send_discord_support_webhook(inquiry: dict):
    webhook_url = os.getenv("DISCORD_SUPPORT_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return {"ok": False, "message": "DISCORD_SUPPORT_WEBHOOK_URL 환경변수가 설정되지 않았습니다."}

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
        "embeds": [{
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
        }]
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


# -------------------------
# Premium
# -------------------------
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
                plan_key VARCHAR(30) NOT NULL DEFAULT 'supporter',
                plan_name VARCHAR(50) NOT NULL DEFAULT '서포터',
                status VARCHAR(30) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by VARCHAR(100)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS premium_guilds (
                guild_id BIGINT PRIMARY KEY,
                is_premium BOOLEAN NOT NULL DEFAULT FALSE,
                plan_key VARCHAR(30) NOT NULL DEFAULT 'free',
                plan_name VARCHAR(50) NOT NULL DEFAULT '무료',
                premium_until TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("ALTER TABLE premium_requests ADD COLUMN IF NOT EXISTS plan_key VARCHAR(30) NOT NULL DEFAULT 'supporter'")
        cur.execute("ALTER TABLE premium_requests ADD COLUMN IF NOT EXISTS plan_name VARCHAR(50) NOT NULL DEFAULT '서포터'")
        cur.execute("ALTER TABLE premium_guilds ADD COLUMN IF NOT EXISTS plan_key VARCHAR(30) NOT NULL DEFAULT 'free'")
        cur.execute("ALTER TABLE premium_guilds ADD COLUMN IF NOT EXISTS plan_name VARCHAR(50) NOT NULL DEFAULT '무료'")

        cur.execute("""
            UPDATE premium_requests
            SET plan_key = COALESCE(NULLIF(plan_key, ''), 'supporter'),
                plan_name = COALESCE(NULLIF(plan_name, ''), '서포터')
        """)

        cur.execute("""
            UPDATE premium_guilds
            SET plan_key = CASE
                    WHEN is_premium = TRUE AND (plan_key IS NULL OR plan_key = '' OR plan_key = 'free') THEN 'supporter'
                    ELSE COALESCE(NULLIF(plan_key, ''), 'free')
                END,
                plan_name = CASE
                    WHEN is_premium = TRUE AND (plan_name IS NULL OR plan_name = '' OR plan_name = '무료') THEN '서포터'
                    WHEN COALESCE(NULLIF(plan_key, ''), 'free') = 'clan' THEN '클랜'
                    WHEN COALESCE(NULLIF(plan_key, ''), 'free') = 'pro' THEN '프로'
                    WHEN COALESCE(NULLIF(plan_key, ''), 'free') = 'supporter' THEN '서포터'
                    ELSE '무료'
                END
        """)


def cleanup_expired_premium_guilds():
    init_premium_tables()
    with db_cursor() as (_, cur):
        cur.execute("""
            UPDATE premium_guilds
            SET is_premium = FALSE,
                plan_key = 'free',
                plan_name = '무료',
                updated_at = CURRENT_TIMESTAMP
            WHERE is_premium = TRUE
              AND premium_until IS NOT NULL
              AND premium_until < CURRENT_TIMESTAMP
        """)


def create_premium_request(guild_id: int, applicant_name: str, amount: int, discord_tag: Optional[str] = None, memo: Optional[str] = None, plan_key: Optional[str] = 'supporter'):
    init_premium_tables()
    normalized_plan = normalize_plan_key(plan_key)
    plan_name = get_plan_label(normalized_plan)
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            INSERT INTO premium_requests (guild_id, applicant_name, discord_tag, amount, memo, plan_key, plan_name, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING id, guild_id, applicant_name, discord_tag, amount, memo, plan_key, plan_name, status, created_at
        """, (guild_id, applicant_name, discord_tag, amount, memo, normalized_plan, plan_name))
        row = cur.fetchone()
        return dict(row) if row else None


def get_premium_requests(limit: int = 200):
    init_premium_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, applicant_name, discord_tag, amount, memo,
                   plan_key, plan_name, status, created_at, approved_at, approved_by
            FROM premium_requests
            ORDER BY id DESC
            LIMIT %s
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]


def approve_premium_request(request_id: int, days: int = 30, approved_by: str = 'admin', plan_key: Optional[str] = None):
    init_premium_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("SELECT id, guild_id, status, plan_key FROM premium_requests WHERE id = %s", (request_id,))
        req_row = cur.fetchone()
        if not req_row:
            raise ValueError('신청 내역을 찾을 수 없습니다.')
        if req_row['status'] == 'approved':
            raise ValueError('이미 승인된 신청입니다.')
        normalized_plan = normalize_plan_key(plan_key or req_row.get('plan_key'))
        plan_name = get_plan_label(normalized_plan)

        current = get_premium_info(req_row['guild_id'])
        now = datetime.utcnow()
        base_time = now
        if current and current.get('is_premium') and current.get('premium_until') and current['premium_until'] > now:
            base_time = current['premium_until']
        premium_until = base_time + timedelta(days=days)

        cur.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, plan_key, plan_name, premium_until, updated_at)
            VALUES (%s, TRUE, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                is_premium = TRUE,
                plan_key = EXCLUDED.plan_key,
                plan_name = EXCLUDED.plan_name,
                premium_until = EXCLUDED.premium_until,
                updated_at = CURRENT_TIMESTAMP
            RETURNING guild_id, is_premium, plan_key, plan_name, premium_until, updated_at
        """, (req_row['guild_id'], normalized_plan, plan_name, premium_until))
        premium_row = cur.fetchone()

        cur.execute("""
            UPDATE premium_requests
            SET status = 'approved', plan_key = %s, plan_name = %s, approved_at = CURRENT_TIMESTAMP, approved_by = %s
            WHERE id = %s
        """, (normalized_plan, plan_name, approved_by, request_id))
        return dict(premium_row) if premium_row else None


def reject_premium_request(request_id: int, rejected_by: str = 'rejected'):
    init_premium_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE premium_requests
            SET status = 'rejected', approved_at = CURRENT_TIMESTAMP, approved_by = %s
            WHERE id = %s
            RETURNING id
        """, (rejected_by, request_id))
        row = cur.fetchone()
        return dict(row) if row else None


def is_premium_guild(guild_id: int) -> bool:
    cleanup_expired_premium_guilds()
    info = get_premium_info(guild_id)
    return bool(info and info.get('is_premium'))


def is_guild_premium(guild_id: int) -> bool:
    return is_premium_guild(guild_id)


def has_premium_plan(guild_id: int, required_plan_key: str = 'supporter') -> bool:
    cleanup_expired_premium_guilds()
    info = get_premium_info(guild_id)
    if not info or not info.get('is_premium'):
        return normalize_plan_key(required_plan_key) == 'free'
    return plan_at_least(info.get('plan_key'), required_plan_key)


def get_premium_info(guild_id: int):
    cleanup_expired_premium_guilds()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("SELECT guild_id, is_premium, plan_key, plan_name, premium_until, updated_at FROM premium_guilds WHERE guild_id = %s", (guild_id,))
        row = cur.fetchone()
        if not row:
            return {'guild_id': guild_id, 'is_premium': False, 'plan_key': 'free', 'plan_name': '무료', 'premium_until': None, 'updated_at': None}
        return dict(row)


def set_premium(guild_id: int, enabled: bool):
    init_premium_tables()
    with db_cursor() as (_, cur):
        if enabled:
            cur.execute("""
                INSERT INTO premium_guilds (guild_id, is_premium, plan_key, plan_name, premium_until, updated_at)
                VALUES (%s, TRUE, 'supporter', '서포터', NULL, CURRENT_TIMESTAMP)
                ON CONFLICT (guild_id)
                DO UPDATE SET is_premium = TRUE, plan_key = 'supporter', plan_name = '서포터', updated_at = CURRENT_TIMESTAMP
            """, (guild_id,))
        else:
            cur.execute("""
                INSERT INTO premium_guilds (guild_id, is_premium, plan_key, plan_name, premium_until, updated_at)
                VALUES (%s, FALSE, 'free', '무료', NULL, CURRENT_TIMESTAMP)
                ON CONFLICT (guild_id)
                DO UPDATE SET is_premium = FALSE, plan_key = 'free', plan_name = '무료', premium_until = NULL, updated_at = CURRENT_TIMESTAMP
            """, (guild_id,))
    return get_premium_info(guild_id)


def set_premium_days(guild_id: int, days: int, plan_key: Optional[str] = 'supporter'):
    init_premium_tables()
    current = get_premium_info(guild_id)
    now = datetime.utcnow()
    base_time = now
    if current and current.get('is_premium') and current.get('premium_until') and current['premium_until'] > now:
        base_time = current['premium_until']

    new_until = base_time + timedelta(days=days)
    normalized_plan = normalize_plan_key(plan_key)
    plan_name = get_plan_label(normalized_plan)
    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, plan_key, plan_name, premium_until, updated_at)
            VALUES (%s, TRUE, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET is_premium = TRUE, plan_key = EXCLUDED.plan_key, plan_name = EXCLUDED.plan_name, premium_until = EXCLUDED.premium_until, updated_at = CURRENT_TIMESTAMP
        """, (guild_id, normalized_plan, plan_name, new_until))
    return get_premium_info(guild_id)


def get_active_premium_guilds():
    cleanup_expired_premium_guilds()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("SELECT guild_id, is_premium, plan_key, plan_name, premium_until, updated_at FROM premium_guilds WHERE is_premium = TRUE ORDER BY guild_id ASC")
        return [dict(row) for row in cur.fetchall()]


def count_active_premium_guilds() -> int:
    cleanup_expired_premium_guilds()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("SELECT COUNT(*) AS cnt FROM premium_guilds WHERE is_premium = TRUE")
        row = cur.fetchone()
        return int(row['cnt']) if row else 0

# -------------------------
# Settings
# -------------------------
def init_settings_tables():
    with db_cursor() as (_, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id BIGINT PRIMARY KEY,
                category_id BIGINT,
                recruit_role_id BIGINT,
                log_channel_id BIGINT,
                announcement_channel_id BIGINT,
                result_channel_id BIGINT,
                voice_category_id BIGINT,
                queue_channel_id BIGINT,
                manager_role_id BIGINT,
                premium_role_id BIGINT,
                clan_brand_name VARCHAR(100),
                clan_brand_color VARCHAR(20),
                clan_badge_text VARCHAR(50),
                clan_intro_text TEXT,
                clan_start_template TEXT,
                clan_result_template TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS clan_brand_name VARCHAR(100)")
        cur.execute("ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS clan_brand_color VARCHAR(20)")
        cur.execute("ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS clan_badge_text VARCHAR(50)")
        cur.execute("ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS clan_intro_text TEXT")
        cur.execute("ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS clan_start_template TEXT")
        cur.execute("ALTER TABLE guild_settings ADD COLUMN IF NOT EXISTS clan_result_template TEXT")


def ensure_guild_settings(guild_id: int):
    init_settings_tables()
    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO guild_settings (guild_id)
            VALUES (%s)
            ON CONFLICT (guild_id) DO NOTHING
        """, (guild_id,))


def get_settings(guild_id: int):
    ensure_guild_settings(guild_id)
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                guild_id, category_id, recruit_role_id, log_channel_id,
                announcement_channel_id, result_channel_id, voice_category_id,
                queue_channel_id, manager_role_id, premium_role_id, clan_brand_name, clan_brand_color, clan_badge_text,
                clan_intro_text, clan_start_template, clan_result_template, updated_at
            FROM guild_settings
            WHERE guild_id = %s
        """, (guild_id,))
        row = cur.fetchone()

    if not row:
        return {
            "guild_id": guild_id,
            "category_id": None,
            "recruit_role_id": None,
            "log_channel_id": None,
            "announcement_channel_id": None,
            "result_channel_id": None,
            "voice_category_id": None,
            "queue_channel_id": None,
            "manager_role_id": None,
            "premium_role_id": None,
            "clan_brand_name": None,
            "clan_brand_color": None,
            "clan_badge_text": None,
            "clan_intro_text": None,
            "clan_start_template": None,
            "clan_result_template": None,
            "updated_at": None,
        }
    return dict(row)


def update_settings(guild_id: int, **kwargs):
    ensure_guild_settings(guild_id)

    allowed_keys = {
        "category_id",
        "recruit_role_id",
        "log_channel_id",
        "announcement_channel_id",
        "result_channel_id",
        "voice_category_id",
        "queue_channel_id",
        "manager_role_id",
        "premium_role_id",
        "clan_brand_name",
        "clan_brand_color",
        "clan_badge_text",
        "clan_intro_text",
        "clan_start_template",
        "clan_result_template",
    }

    if not kwargs:
        return get_settings(guild_id)

    for key in kwargs.keys():
        if key not in allowed_keys:
            raise ValueError(f"허용되지 않은 설정 키입니다: {key}")

    set_parts = [f"{key} = %s" for key in kwargs.keys()]
    values = list(kwargs.values())
    values.append(guild_id)

    query = f"""
        UPDATE guild_settings
        SET {', '.join(set_parts)},
            updated_at = CURRENT_TIMESTAMP
        WHERE guild_id = %s
    """

    with db_cursor() as (_, cur):
        cur.execute(query, tuple(values))

    return get_settings(guild_id)


def set_role(guild_id: int, role_id: int):
    return update_settings(guild_id, recruit_role_id=role_id)


def set_category(guild_id: int, category_id: int):
    return update_settings(guild_id, category_id=category_id)


def get_clan_branding(guild_id: int):
    settings = get_settings(guild_id)
    premium = get_premium_info(guild_id)
    is_clan = bool(premium and premium.get('is_premium') and plan_at_least(premium.get('plan_key'), 'clan'))
    guild_name = None
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("SELECT guild_name FROM guild_registry WHERE guild_id = %s", (guild_id,))
        row = cur.fetchone()
        if row:
            guild_name = row.get('guild_name')

    return {
        'guild_id': guild_id,
        'is_clan': is_clan,
        'brand_name': (settings.get('clan_brand_name') or guild_name or f'Guild {guild_id}').strip(),
        'brand_color': sanitize_brand_color(settings.get('clan_brand_color')),
        'badge_text': (settings.get('clan_badge_text') or DEFAULT_CLAN_BADGE).strip(),
        'intro_text': (settings.get('clan_intro_text') or DEFAULT_CLAN_INTRO).strip(),
        'start_template': (settings.get('clan_start_template') or DEFAULT_CLAN_START_TEMPLATE).strip(),
        'result_template': (settings.get('clan_result_template') or DEFAULT_CLAN_RESULT_TEMPLATE).strip(),
        'plan_key': premium.get('plan_key') if premium else 'free',
        'plan_name': premium.get('plan_name') if premium else '무료',
    }


def update_clan_branding(guild_id: int, brand_name: Optional[str] = None, brand_color: Optional[str] = None, badge_text: Optional[str] = None, intro_text: Optional[str] = None, start_template: Optional[str] = None, result_template: Optional[str] = None):
    updates = {}
    if brand_name is not None:
        updates['clan_brand_name'] = (brand_name or '').strip() or None
    if brand_color is not None:
        updates['clan_brand_color'] = sanitize_brand_color(brand_color) if brand_color else None
    if badge_text is not None:
        updates['clan_badge_text'] = (badge_text or '').strip()[:50] or None
    if intro_text is not None:
        updates['clan_intro_text'] = (intro_text or '').strip() or None
    if start_template is not None:
        updates['clan_start_template'] = (start_template or '').strip() or None
    if result_template is not None:
        updates['clan_result_template'] = (result_template or '').strip() or None
    if updates:
        update_settings(guild_id, **updates)
    return get_clan_branding(guild_id)


def clear_clan_branding(guild_id: int):
    update_settings(guild_id, clan_brand_name=None, clan_brand_color=None, clan_badge_text=None, clan_intro_text=None, clan_start_template=None, clan_result_template=None)
    return get_clan_branding(guild_id)



class _SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def render_clan_template(guild_id: int, template_key: str, **kwargs):
    brand = get_clan_branding(guild_id)
    template_map = {
        'intro': brand.get('intro_text') or DEFAULT_CLAN_INTRO,
        'start': brand.get('start_template') or DEFAULT_CLAN_START_TEMPLATE,
        'result': brand.get('result_template') or DEFAULT_CLAN_RESULT_TEMPLATE,
    }
    template = template_map.get(template_key, '')
    values = _SafeDict({
        'brand_name': brand.get('brand_name', ''),
        'brand_color': brand.get('brand_color', ''),
        'badge': brand.get('badge_text', DEFAULT_CLAN_BADGE),
        'plan_name': brand.get('plan_name', '무료'),
        **kwargs,
    })
    return template.format_map(values)

# -------------------------
# Recruit / Lobby / Party
# -------------------------
def init_recruit_tables():
    with db_cursor() as (_, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lobbies (
                channel_id BIGINT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                host_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                team_size INTEGER NOT NULL,
                total_slots INTEGER,
                status VARCHAR(30) NOT NULL DEFAULT 'open',
                message_id BIGINT,
                waiting_voice_id BIGINT,
                team_a_voice_id BIGINT,
                team_b_voice_id BIGINT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""ALTER TABLE lobbies ADD COLUMN IF NOT EXISTS total_slots INTEGER""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lobby_players (
                channel_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                mmr INTEGER NOT NULL,
                position VARCHAR(50) NOT NULL,
                party_id BIGINT,
                joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, user_id)
            )
        """)

        cur.execute("""ALTER TABLE lobby_players ADD COLUMN IF NOT EXISTS party_id BIGINT""")
        cur.execute("""ALTER TABLE lobby_players ADD COLUMN IF NOT EXISTS joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP""")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lobby_teams (
                channel_id BIGINT NOT NULL,
                team VARCHAR(1) NOT NULL,
                user_id BIGINT NOT NULL,
                PRIMARY KEY (channel_id, team, user_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS players (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                display_name VARCHAR(100),
                mmr INTEGER NOT NULL DEFAULT 1000,
                win INTEGER NOT NULL DEFAULT 0,
                lose INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS player_game_stats (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                display_name VARCHAR(100),
                mmr INTEGER NOT NULL DEFAULT 1000,
                win INTEGER NOT NULL DEFAULT 0,
                lose INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, game)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lobby_parties (
                id BIGSERIAL PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                leader_user_id BIGINT NOT NULL,
                party_code VARCHAR(12) NOT NULL,
                mode_size INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(channel_id, party_code)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS lobby_party_members (
                channel_id BIGINT NOT NULL,
                party_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                display_name VARCHAR(100) NOT NULL,
                joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(channel_id, user_id)
            )
        """)


def get_lobby(channel_id: int):
    init_recruit_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                channel_id, guild_id, host_id, game, team_size, total_slots, status,
                message_id, waiting_voice_id, team_a_voice_id, team_b_voice_id, created_at
            FROM lobbies
            WHERE channel_id = %s
        """, (channel_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_lobby(
    channel_id: int,
    guild_id: int,
    host_id: int,
    game: str,
    team_size: int,
    total_slots: Optional[int] = None
):
    init_recruit_tables()
    register_guild(guild_id)

    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO lobbies (
                channel_id, guild_id, host_id, game, team_size, total_slots, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'open')
            ON CONFLICT (channel_id) DO UPDATE SET
                guild_id = EXCLUDED.guild_id,
                host_id = EXCLUDED.host_id,
                game = EXCLUDED.game,
                team_size = EXCLUDED.team_size,
                total_slots = EXCLUDED.total_slots,
                status = 'open',
                message_id = NULL,
                waiting_voice_id = NULL,
                team_a_voice_id = NULL,
                team_b_voice_id = NULL
        """, (channel_id, guild_id, host_id, game, team_size, total_slots))

        cur.execute("DELETE FROM lobby_players WHERE channel_id = %s", (channel_id,))
        cur.execute("DELETE FROM lobby_teams WHERE channel_id = %s", (channel_id,))
        cur.execute("DELETE FROM lobby_party_members WHERE channel_id = %s", (channel_id,))
        cur.execute("DELETE FROM lobby_parties WHERE channel_id = %s", (channel_id,))


def set_lobby_message(channel_id: int, message_id: int):
    with db_cursor() as (_, cur):
        cur.execute("""
            UPDATE lobbies
            SET message_id = %s
            WHERE channel_id = %s
        """, (message_id, channel_id))


def set_lobby_status(channel_id: int, status: str):
    with db_cursor() as (_, cur):
        cur.execute("""
            UPDATE lobbies
            SET status = %s
            WHERE channel_id = %s
        """, (status, channel_id))


def set_voice_channels(channel_id: int, waiting_voice_id: int, team_a_voice_id: int, team_b_voice_id: int):
    with db_cursor() as (_, cur):
        cur.execute("""
            UPDATE lobbies
            SET waiting_voice_id = %s,
                team_a_voice_id = %s,
                team_b_voice_id = %s
            WHERE channel_id = %s
        """, (waiting_voice_id, team_a_voice_id, team_b_voice_id, channel_id))


def get_lobby_players(channel_id: int):
    init_recruit_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT channel_id, user_id, display_name, mmr, position, party_id, joined_at
            FROM lobby_players
            WHERE channel_id = %s
            ORDER BY joined_at ASC
        """, (channel_id,))
        return [dict(row) for row in cur.fetchall()]


def add_lobby_player(
    channel_id: int,
    user_id: int,
    display_name: str,
    mmr: int,
    position: str,
    party_id: Optional[int] = None
):
    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO lobby_players (channel_id, user_id, display_name, mmr, position, party_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (channel_id, user_id)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                mmr = EXCLUDED.mmr,
                position = EXCLUDED.position,
                party_id = EXCLUDED.party_id
        """, (channel_id, user_id, display_name, mmr, position, party_id))


def has_lobby_player(channel_id: int, user_id: int) -> bool:
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT 1
            FROM lobby_players
            WHERE channel_id = %s AND user_id = %s
        """, (channel_id, user_id))
        return cur.fetchone() is not None


def remove_lobby_player(channel_id: int, user_id: int):
    with db_cursor() as (_, cur):
        cur.execute("""
            DELETE FROM lobby_players
            WHERE channel_id = %s AND user_id = %s
        """, (channel_id, user_id))


def clear_teams(channel_id: int):
    with db_cursor() as (_, cur):
        cur.execute("""
            DELETE FROM lobby_teams
            WHERE channel_id = %s
        """, (channel_id,))


def add_team_member(channel_id: int, team: str, user_id: int):
    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO lobby_teams (channel_id, team, user_id)
            VALUES (%s, %s, %s)
            ON CONFLICT (channel_id, team, user_id) DO NOTHING
        """, (channel_id, team, user_id))


def get_team_members(channel_id: int, team: str):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT user_id
            FROM lobby_teams
            WHERE channel_id = %s AND team = %s
            ORDER BY user_id ASC
        """, (channel_id, team))
        return [row["user_id"] for row in cur.fetchall()]


def ensure_player(guild_id: int, user_id: int, mmr: int = 1000, display_name: Optional[str] = None):
    init_recruit_tables()
    register_guild(guild_id)

    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO players (guild_id, user_id, display_name, mmr, win, lose)
            VALUES (%s, %s, %s, %s, 0, 0)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, players.display_name)
        """, (guild_id, user_id, display_name, mmr))


def ensure_player_game(guild_id: int, user_id: int, game: str, mmr: int = 1000, display_name: Optional[str] = None):
    init_recruit_tables()
    register_guild(guild_id)

    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO player_game_stats (guild_id, user_id, game, display_name, mmr, win, lose)
            VALUES (%s, %s, %s, %s, %s, 0, 0)
            ON CONFLICT (guild_id, user_id, game)
            DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, player_game_stats.display_name)
        """, (guild_id, user_id, game, display_name, mmr))


def create_lobby_party(channel_id: int, leader_user_id: int, leader_name: str, mode_size: int):
    init_recruit_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT party_id
            FROM lobby_party_members
            WHERE channel_id = %s AND user_id = %s
        """, (channel_id, leader_user_id))
        if cur.fetchone():
            raise ValueError("이미 파티에 속해 있습니다.")

        party_code = None
        for _ in range(10):
            test_code = generate_party_code()
            cur.execute("""
                SELECT id
                FROM lobby_parties
                WHERE channel_id = %s AND party_code = %s
            """, (channel_id, test_code))
            if cur.fetchone() is None:
                party_code = test_code
                break

        if not party_code:
            raise ValueError("파티 코드 생성에 실패했습니다.")

        cur.execute("""
            INSERT INTO lobby_parties (channel_id, leader_user_id, party_code, mode_size)
            VALUES (%s, %s, %s, %s)
            RETURNING id, channel_id, leader_user_id, party_code, mode_size, created_at
        """, (channel_id, leader_user_id, party_code, mode_size))
        party_row = cur.fetchone()

        cur.execute("""
            INSERT INTO lobby_party_members (channel_id, party_id, user_id, display_name)
            VALUES (%s, %s, %s, %s)
        """, (channel_id, party_row["id"], leader_user_id, leader_name))

        return dict(party_row)


def get_party_by_code(channel_id: int, party_code: str):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, channel_id, leader_user_id, party_code, mode_size, created_at
            FROM lobby_parties
            WHERE channel_id = %s AND party_code = %s
        """, (channel_id, party_code.upper()))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_party(channel_id: int, user_id: int):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                p.id, p.channel_id, p.leader_user_id, p.party_code,
                p.mode_size, p.created_at
            FROM lobby_parties p
            JOIN lobby_party_members m ON p.id = m.party_id
            WHERE m.channel_id = %s AND m.user_id = %s
        """, (channel_id, user_id))
        row = cur.fetchone()
        return dict(row) if row else None


def get_party_members(channel_id: int, party_id: int):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT channel_id, party_id, user_id, display_name, joined_at
            FROM lobby_party_members
            WHERE channel_id = %s AND party_id = %s
            ORDER BY joined_at ASC
        """, (channel_id, party_id))
        return [dict(row) for row in cur.fetchall()]


def join_lobby_party(channel_id: int, party_code: str, user_id: int, display_name: str):
    init_recruit_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT party_id
            FROM lobby_party_members
            WHERE channel_id = %s AND user_id = %s
        """, (channel_id, user_id))
        if cur.fetchone():
            raise ValueError("이미 다른 파티에 속해 있습니다.")

        cur.execute("""
            SELECT id, channel_id, leader_user_id, party_code, mode_size, created_at
            FROM lobby_parties
            WHERE channel_id = %s AND party_code = %s
        """, (channel_id, party_code.upper()))
        party = cur.fetchone()

        if not party:
            raise ValueError("파티 코드를 찾을 수 없습니다.")

        cur.execute("""
            SELECT COUNT(*) AS cnt
            FROM lobby_party_members
            WHERE channel_id = %s AND party_id = %s
        """, (channel_id, party["id"]))
        member_count = cur.fetchone()["cnt"]

        if member_count >= party["mode_size"]:
            raise ValueError("해당 파티는 이미 정원이 찼습니다.")

        cur.execute("""
            INSERT INTO lobby_party_members (channel_id, party_id, user_id, display_name)
            VALUES (%s, %s, %s, %s)
        """, (channel_id, party["id"], user_id, display_name))

        return dict(party)


def leave_lobby_party(channel_id: int, user_id: int):
    init_recruit_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                p.id, p.channel_id, p.leader_user_id, p.party_code, p.mode_size
            FROM lobby_parties p
            JOIN lobby_party_members m ON p.id = m.party_id
            WHERE m.channel_id = %s AND m.user_id = %s
        """, (channel_id, user_id))
        party = cur.fetchone()

        if not party:
            return {"action": "none"}

        if party["leader_user_id"] == user_id:
            cur.execute("""
                SELECT user_id
                FROM lobby_party_members
                WHERE channel_id = %s AND party_id = %s
            """, (channel_id, party["id"]))
            member_ids = [row["user_id"] for row in cur.fetchall()]

            cur.execute("""
                DELETE FROM lobby_players
                WHERE channel_id = %s AND party_id = %s
            """, (channel_id, party["id"]))

            cur.execute("""
                DELETE FROM lobby_party_members
                WHERE channel_id = %s AND party_id = %s
            """, (channel_id, party["id"]))

            cur.execute("""
                DELETE FROM lobby_parties
                WHERE id = %s
            """, (party["id"],))

            return {
                "action": "disbanded",
                "party_code": party["party_code"],
                "member_ids": member_ids,
            }

        cur.execute("""
            DELETE FROM lobby_players
            WHERE channel_id = %s AND user_id = %s
        """, (channel_id, user_id))

        cur.execute("""
            DELETE FROM lobby_party_members
            WHERE channel_id = %s AND user_id = %s
        """, (channel_id, user_id))

        return {"action": "left", "party_code": party["party_code"]}


def get_lobby_parties(channel_id: int):
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, channel_id, leader_user_id, party_code, mode_size, created_at
            FROM lobby_parties
            WHERE channel_id = %s
            ORDER BY id ASC
        """, (channel_id,))
        parties = [dict(row) for row in cur.fetchall()]

    result = []
    for party in parties:
        members = get_party_members(channel_id, party["id"])
        result.append({**party, "members": members})
    return result


# -------------------------
# Season
# -------------------------
def init_season_tables():
    with db_cursor() as (_, cur):
        cur.execute("""
            CREATE TABLE IF NOT EXISTS seasons (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                season_name VARCHAR(100) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                UNIQUE (guild_id, game, season_name)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS season_player_stats (
                guild_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                season_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                display_name VARCHAR(100),
                mmr INTEGER NOT NULL DEFAULT 1000,
                win INTEGER NOT NULL DEFAULT 0,
                lose INTEGER NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, game, season_id, user_id)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS season_matches (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                season_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                winner_team VARCHAR(1) NOT NULL,
                team_a_avg INTEGER NOT NULL,
                team_b_avg INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def create_season(guild_id: int, game: str, season_name: str):
    init_season_tables()
    register_guild(guild_id)

    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE seasons
            SET is_active = FALSE,
                ended_at = CURRENT_TIMESTAMP
            WHERE guild_id = %s AND game = %s AND is_active = TRUE
        """, (guild_id, game))

        cur.execute("""
            INSERT INTO seasons (guild_id, game, season_name, is_active)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id, guild_id, game, season_name, is_active, started_at, ended_at
        """, (guild_id, game, season_name))
        row = cur.fetchone()
        return dict(row) if row else None


def end_active_season(guild_id: int, game: str):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            UPDATE seasons
            SET is_active = FALSE,
                ended_at = CURRENT_TIMESTAMP
            WHERE guild_id = %s AND game = %s AND is_active = TRUE
            RETURNING id, guild_id, game, season_name, is_active, started_at, ended_at
        """, (guild_id, game))
        row = cur.fetchone()
        return dict(row) if row else None


def get_active_season(guild_id: int, game: str):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, game, season_name, is_active, started_at, ended_at
            FROM seasons
            WHERE guild_id = %s AND game = %s AND is_active = TRUE
            ORDER BY id DESC
            LIMIT 1
        """, (guild_id, game))
        row = cur.fetchone()
        return dict(row) if row else None


def get_seasons(guild_id: int, game: Optional[str] = None, limit: int = 50):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        if game:
            cur.execute("""
                SELECT id, guild_id, game, season_name, is_active, started_at, ended_at
                FROM seasons
                WHERE guild_id = %s AND game = %s
                ORDER BY id DESC
                LIMIT %s
            """, (guild_id, game, limit))
        else:
            cur.execute("""
                SELECT id, guild_id, game, season_name, is_active, started_at, ended_at
                FROM seasons
                WHERE guild_id = %s
                ORDER BY id DESC
                LIMIT %s
            """, (guild_id, limit))
        return [dict(row) for row in cur.fetchall()]


def get_season_by_id(season_id: int):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, game, season_name, is_active, started_at, ended_at
            FROM seasons
            WHERE id = %s
        """, (season_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_latest_season_for_game(guild_id: int, game: str):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, game, season_name, is_active, started_at, ended_at
            FROM seasons
            WHERE guild_id = %s AND game = %s
            ORDER BY id DESC
            LIMIT 1
        """, (guild_id, game))
        row = cur.fetchone()
        return dict(row) if row else None


def ensure_season_player(
    guild_id: int,
    game: str,
    season_id: int,
    user_id: int,
    display_name: Optional[str] = None
):
    init_season_tables()
    register_guild(guild_id)

    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO season_player_stats (
                guild_id, game, season_id, user_id, display_name, mmr, win, lose
            )
            VALUES (%s, %s, %s, %s, %s, 1000, 0, 0)
            ON CONFLICT (guild_id, game, season_id, user_id)
            DO UPDATE SET
                display_name = COALESCE(EXCLUDED.display_name, season_player_stats.display_name),
                updated_at = CURRENT_TIMESTAMP
        """, (guild_id, game, season_id, user_id, display_name))


def apply_season_match_result(
    guild_id: int,
    game: str,
    season_id: int,
    winners: list[int],
    losers: list[int],
    winner_delta: int,
    loser_delta: int,
    name_map: dict
):
    init_season_tables()

    for uid in winners:
        display_name = name_map.get(uid)
        ensure_season_player(guild_id, game, season_id, uid, display_name)
        with db_cursor() as (_, cur):
            cur.execute("""
                UPDATE season_player_stats
                SET
                    mmr = GREATEST(0, mmr + %s),
                    win = win + 1,
                    display_name = COALESCE(%s, display_name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s AND game = %s AND season_id = %s AND user_id = %s
            """, (winner_delta, display_name, guild_id, game, season_id, uid))

    for uid in losers:
        display_name = name_map.get(uid)
        ensure_season_player(guild_id, game, season_id, uid, display_name)
        with db_cursor() as (_, cur):
            cur.execute("""
                UPDATE season_player_stats
                SET
                    mmr = GREATEST(0, mmr + %s),
                    lose = lose + 1,
                    display_name = COALESCE(%s, display_name),
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = %s AND game = %s AND season_id = %s AND user_id = %s
            """, (loser_delta, display_name, guild_id, game, season_id, uid))


def add_season_match(
    guild_id: int,
    game: str,
    season_id: int,
    channel_id: int,
    winner_team: str,
    team_a_avg: int,
    team_b_avg: int
):
    init_season_tables()
    with db_cursor() as (_, cur):
        cur.execute("""
            INSERT INTO season_matches (
                guild_id, game, season_id, channel_id, winner_team, team_a_avg, team_b_avg
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (guild_id, game, season_id, channel_id, winner_team, team_a_avg, team_b_avg))


def get_season_ranking(guild_id: int, game: str, season_id: int, limit: int = 50):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                guild_id, game, season_id, user_id, display_name, mmr, win, lose,
                CASE
                    WHEN (win + lose) = 0 THEN 0
                    ELSE ROUND((CAST(win AS NUMERIC) / (win + lose)) * 100, 1)
                END AS winrate
            FROM season_player_stats
            WHERE guild_id = %s AND game = %s AND season_id = %s
            ORDER BY mmr DESC, win DESC, user_id ASC
            LIMIT %s
        """, (guild_id, game, season_id, limit))
        return [dict(row) for row in cur.fetchall()]


def get_season_matches(guild_id: int, game: str, season_id: int, limit: int = 20):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT id, guild_id, game, season_id, channel_id, winner_team,
                   team_a_avg, team_b_avg, created_at
            FROM season_matches
            WHERE guild_id = %s AND game = %s AND season_id = %s
            ORDER BY id DESC
            LIMIT %s
        """, (guild_id, game, season_id, limit))
        return [dict(row) for row in cur.fetchall()]


def get_season_player_detail(guild_id: int, game: str, season_id: int, user_id: int):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                guild_id, game, season_id, user_id, display_name, mmr, win, lose,
                CASE
                    WHEN (win + lose) = 0 THEN 0
                    ELSE ROUND((CAST(win AS NUMERIC) / (win + lose)) * 100, 1)
                END AS winrate,
                updated_at
            FROM season_player_stats
            WHERE guild_id = %s AND game = %s AND season_id = %s AND user_id = %s
        """, (guild_id, game, season_id, user_id))
        row = cur.fetchone()
        return dict(row) if row else None


def get_season_stats_summary(guild_id: int, game: str, season_id: int):
    init_season_tables()
    with db_cursor(dict_cursor=True) as (_, cur):
        cur.execute("""
            SELECT
                COUNT(*) AS player_count,
                COALESCE(AVG(mmr), 0) AS avg_mmr,
                COALESCE(MAX(mmr), 0) AS top_mmr
            FROM season_player_stats
            WHERE guild_id = %s AND game = %s AND season_id = %s
        """, (guild_id, game, season_id))
        player_row = cur.fetchone()

        cur.execute("""
            SELECT COUNT(*) AS match_count
            FROM season_matches
            WHERE guild_id = %s AND game = %s AND season_id = %s
        """, (guild_id, game, season_id))
        match_row = cur.fetchone()

    return {
        "player_count": int(player_row["player_count"]) if player_row else 0,
        "avg_mmr": round(float(player_row["avg_mmr"])) if player_row else 0,
        "top_mmr": int(player_row["top_mmr"]) if player_row else 0,
        "match_count": int(match_row["match_count"]) if match_row else 0,
    }


class DB:
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
        init_guild_registry_table()
        init_settings_tables()
        init_recruit_tables()
        init_premium_tables()
        init_support_inquiry_table()
        init_season_tables()

    @staticmethod
    def init_guild_registry_table():
        return init_guild_registry_table()

    @staticmethod
    def register_guild(guild_id: int, guild_name: Optional[str] = None):
        return register_guild(guild_id, guild_name)

    @staticmethod
    def deactivate_guild(guild_id: int):
        return deactivate_guild(guild_id)

    @staticmethod
    def get_registered_guilds(active_only: bool = False):
        return get_registered_guilds(active_only)

    @staticmethod
    def init_support_inquiry_table():
        return init_support_inquiry_table()

    @staticmethod
    def insert_support_inquiry(name, email, category, subject, message, discord_tag=None):
        return insert_support_inquiry(name, email, category, subject, message, discord_tag)

    @staticmethod
    def send_discord_support_webhook(inquiry: dict):
        return send_discord_support_webhook(inquiry)

    @staticmethod
    def init_premium_tables():
        return init_premium_tables()

    @staticmethod
    def cleanup_expired_premium_guilds():
        return cleanup_expired_premium_guilds()

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

    @staticmethod
    def is_premium_guild(guild_id: int) -> bool:
        return is_premium_guild(guild_id)

    @staticmethod
    def is_guild_premium(guild_id: int) -> bool:
        return is_guild_premium(guild_id)

    @staticmethod
    def has_premium_plan(guild_id: int, required_plan_key: str = 'supporter') -> bool:
        return has_premium_plan(guild_id, required_plan_key)

    @staticmethod
    def get_plan_label(plan_key: Optional[str]) -> str:
        return get_plan_label(plan_key)

    @staticmethod
    def get_premium_info(guild_id: int):
        return get_premium_info(guild_id)

    @staticmethod
    def set_premium(guild_id: int, enabled: bool):
        return set_premium(guild_id, enabled)

    @staticmethod
    def set_premium_days(guild_id: int, days: int, plan_key: Optional[str] = 'supporter'):
        return set_premium_days(guild_id, days, plan_key)

    @staticmethod
    def get_active_premium_guilds():
        return get_active_premium_guilds()

    @staticmethod
    def count_active_premium_guilds():
        return count_active_premium_guilds()

    @staticmethod
    def ensure_guild_settings(guild_id: int):
        return ensure_guild_settings(guild_id)

    @staticmethod
    def get_settings(guild_id: int):
        return get_settings(guild_id)

    @staticmethod
    def update_settings(guild_id: int, **kwargs):
        return update_settings(guild_id, **kwargs)

    @staticmethod
    def set_role(guild_id: int, role_id: int):
        return set_role(guild_id, role_id)

    @staticmethod
    def set_category(guild_id: int, category_id: int):
        return set_category(guild_id, category_id)

    @staticmethod
    def init_recruit_tables():
        return init_recruit_tables()

    @staticmethod
    def get_lobby(channel_id: int):
        return get_lobby(channel_id)

    @staticmethod
    def create_lobby(
        channel_id: int,
        guild_id: int,
        host_id: int,
        game: str,
        team_size: int,
        total_slots: Optional[int] = None
    ):
        return create_lobby(channel_id, guild_id, host_id, game, team_size, total_slots)

    @staticmethod
    def set_lobby_message(channel_id: int, message_id: int):
        return set_lobby_message(channel_id, message_id)

    @staticmethod
    def set_lobby_status(channel_id: int, status: str):
        return set_lobby_status(channel_id, status)

    @staticmethod
    def set_voice_channels(channel_id: int, waiting_voice_id: int, team_a_voice_id: int, team_b_voice_id: int):
        return set_voice_channels(channel_id, waiting_voice_id, team_a_voice_id, team_b_voice_id)

    @staticmethod
    def get_lobby_players(channel_id: int):
        return get_lobby_players(channel_id)

    @staticmethod
    def add_lobby_player(channel_id: int, user_id: int, display_name: str, mmr: int, position: str, party_id: Optional[int] = None):
        return add_lobby_player(channel_id, user_id, display_name, mmr, position, party_id)

    @staticmethod
    def has_lobby_player(channel_id: int, user_id: int) -> bool:
        return has_lobby_player(channel_id, user_id)

    @staticmethod
    def remove_lobby_player(channel_id: int, user_id: int):
        return remove_lobby_player(channel_id, user_id)

    @staticmethod
    def clear_teams(channel_id: int):
        return clear_teams(channel_id)

    @staticmethod
    def add_team_member(channel_id: int, team: str, user_id: int):
        return add_team_member(channel_id, team, user_id)

    @staticmethod
    def get_team_members(channel_id: int, team: str):
        return get_team_members(channel_id, team)

    @staticmethod
    def ensure_player(guild_id: int, user_id: int, mmr: int = 1000, display_name: Optional[str] = None):
        return ensure_player(guild_id, user_id, mmr, display_name)

    @staticmethod
    def ensure_player_game(guild_id: int, user_id: int, game: str, mmr: int = 1000, display_name: Optional[str] = None):
        return ensure_player_game(guild_id, user_id, game, mmr, display_name)

    @staticmethod
    def create_lobby_party(channel_id: int, leader_user_id: int, leader_name: str, mode_size: int):
        return create_lobby_party(channel_id, leader_user_id, leader_name, mode_size)

    @staticmethod
    def get_party_by_code(channel_id: int, party_code: str):
        return get_party_by_code(channel_id, party_code)

    @staticmethod
    def get_user_party(channel_id: int, user_id: int):
        return get_user_party(channel_id, user_id)

    @staticmethod
    def get_party_members(channel_id: int, party_id: int):
        return get_party_members(channel_id, party_id)

    @staticmethod
    def join_lobby_party(channel_id: int, party_code: str, user_id: int, display_name: str):
        return join_lobby_party(channel_id, party_code, user_id, display_name)

    @staticmethod
    def leave_lobby_party(channel_id: int, user_id: int):
        return leave_lobby_party(channel_id, user_id)

    @staticmethod
    def get_lobby_parties(channel_id: int):
        return get_lobby_parties(channel_id)

    @staticmethod
    def init_season_tables():
        return init_season_tables()

    @staticmethod
    def create_season(guild_id: int, game: str, season_name: str):
        return create_season(guild_id, game, season_name)

    @staticmethod
    def end_active_season(guild_id: int, game: str):
        return end_active_season(guild_id, game)

    @staticmethod
    def get_active_season(guild_id: int, game: str):
        return get_active_season(guild_id, game)

    @staticmethod
    def get_seasons(guild_id: int, game: Optional[str] = None, limit: int = 50):
        return get_seasons(guild_id, game, limit)

    @staticmethod
    def get_season_by_id(season_id: int):
        return get_season_by_id(season_id)

    @staticmethod
    def get_latest_season_for_game(guild_id: int, game: str):
        return get_latest_season_for_game(guild_id, game)

    @staticmethod
    def ensure_season_player(guild_id: int, game: str, season_id: int, user_id: int, display_name: Optional[str] = None):
        return ensure_season_player(guild_id, game, season_id, user_id, display_name)

    @staticmethod
    def apply_season_match_result(
        guild_id: int,
        game: str,
        season_id: int,
        winners: list[int],
        losers: list[int],
        winner_delta: int,
        loser_delta: int,
        name_map: dict
    ):
        return apply_season_match_result(
            guild_id, game, season_id, winners, losers, winner_delta, loser_delta, name_map
        )

    @staticmethod
    def add_season_match(
        guild_id: int,
        game: str,
        season_id: int,
        channel_id: int,
        winner_team: str,
        team_a_avg: int,
        team_b_avg: int
    ):
        return add_season_match(guild_id, game, season_id, channel_id, winner_team, team_a_avg, team_b_avg)

    @staticmethod
    def get_season_ranking(guild_id: int, game: str, season_id: int, limit: int = 50):
        return get_season_ranking(guild_id, game, season_id, limit)

    @staticmethod
    def get_season_matches(guild_id: int, game: str, season_id: int, limit: int = 20):
        return get_season_matches(guild_id, game, season_id, limit)

    @staticmethod
    def get_season_player_detail(guild_id: int, game: str, season_id: int, user_id: int):
        return get_season_player_detail(guild_id, game, season_id, user_id)

    @staticmethod
    def get_season_stats_summary(guild_id: int, game: str, season_id: int):
        return get_season_stats_summary(guild_id, game, season_id)

    @staticmethod
    def execute(query: str, params: tuple = ()):
        with db_cursor() as (_, cur):
            cur.execute(query, params)

    @staticmethod
    def fetchone(query: str, params: tuple = ()):
        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def fetchall(query: str, params: tuple = ()):
        with db_cursor(dict_cursor=True) as (_, cur):
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]