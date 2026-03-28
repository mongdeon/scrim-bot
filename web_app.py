import os

from flask import Flask, render_template_string, request, jsonify, abort
from psycopg2.extras import RealDictCursor
import psycopg2

from core.db import (
    init_premium_tables,
    create_premium_request,
    get_premium_requests,
    approve_premium_request,
    reject_premium_request,
    cleanup_expired_premium_guilds,
    get_active_premium_guilds,
    count_active_premium_guilds,
    is_guild_premium,
    get_active_season,
    get_season_ranking,
    get_season_matches,
    get_season_stats_summary,
)

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_SECRET = os.environ.get("PREMIUM_ADMIN_SECRET", "").strip()

BANK_NAME = "토스뱅크"
ACCOUNT_NUMBER = "1000-0103-2111"
ACCOUNT_HOLDER = "김태용"
PREMIUM_PRICE = 5000
PREMIUM_DAYS = 30

init_premium_tables()
cleanup_expired_premium_guilds()


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


INDEX_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>내전봇 전적 사이트</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 1200px;
            margin: 40px auto;
            padding: 20px;
        }
        .action-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .action-btn {
            display: inline-block;
            padding: 12px 18px;
            border-radius: 12px;
            color: #fff;
            text-decoration: none;
            font-weight: bold;
        }
        .btn-guide { background: #16a34a; }
        .btn-support { background: #ec4899; }
        .btn-admin { background: #7c3aed; }
        .btn-season { background: #2563eb; }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
        }
        .filters {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        select, input, button {
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #e2e8f0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #334155;
            text-align: left;
        }
        th { background: #334155; }
        .pill {
            display: inline-block;
            padding: 8px 12px;
            border-radius: 999px;
            background: #334155;
            margin-right: 8px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        .top3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }
        .top-card {
            background: #334155;
            border-radius: 16px;
            padding: 16px;
        }
        .muted { color: #94a3b8; }
        @media (max-width: 768px) {
            .top3 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 내전봇 전적 사이트</h1>

        <div class="action-row">
            <a href="/guide" class="action-btn btn-guide">🛟 명령어 / 프리미엄 소개</a>
            <a href="/support" class="action-btn btn-support">💖 후원 / 프리미엄 신청</a>
            <a href="/admin/premium" class="action-btn btn-admin">🔐 관리자 페이지</a>
            <a href="/season" class="action-btn btn-season">🏆 시즌 페이지</a>
        </div>

        <div class="card">
            <div class="pill">프리미엄 가격: {{ premium_price }}원</div>
            <div class="pill">프리미엄 기간: {{ premium_days }}일</div>
            <div class="pill">활성 프리미엄 서버 수: {{ active_premium_count }}</div>
        </div>

        <div class="card">
            <form method="get" class="filters">
                <select name="guild_id">
                    <option value="">전체 서버</option>
                    {% for gid in guild_ids %}
                        <option value="{{ gid }}" {% if selected_guild_id == gid|string %}selected{% endif %}>Guild {{ gid }}</option>
                    {% endfor %}
                </select>

                <select name="game">
                    <option value="">전체 게임</option>
                    {% for g in games %}
                        <option value="{{ g }}" {% if selected_game == g %}selected{% endif %}>{{ g }}</option>
                    {% endfor %}
                </select>

                <input type="text" name="q" placeholder="닉네임 또는 유저 ID 검색" value="{{ q or '' }}">
                <button type="submit">적용</button>
            </form>
        </div>

        {% if ranking|length >= 1 %}
        <div class="top3">
            {% for row in ranking[:3] %}
            <div class="top-card">
                <h3>#{{ loop.index }} {{ row.display_name or row.user_id }}</h3>
                <p>MMR {{ row.mmr }}</p>
                <p>{{ row.win }}승 {{ row.lose }}패 | 승률 {{ row.winrate }}%</p>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="card">
            <h2>🏆 랭킹 TOP 50</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>닉네임</th>
                        <th>유저 ID</th>
                        <th>MMR</th>
                        <th>승</th>
                        <th>패</th>
                        <th>승률</th>
                        <th>상세</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in ranking %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ row.display_name or "-" }}</td>
                        <td>{{ row.user_id }}</td>
                        <td>{{ row.mmr }}</td>
                        <td>{{ row.win }}</td>
                        <td>{{ row.lose }}</td>
                        <td>{{ row.winrate }}%</td>
                        <td><a href="/player/{{ row.guild_id }}/{{ row.user_id }}">보기</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>📝 최근 경기</h2>
            {% for match in matches %}
                <div style="margin-bottom: 12px;">
                    <span class="pill">Guild {{ match.guild_id }}</span>
                    <span class="pill">{{ match.game }}</span>
                    <span class="pill">승리팀 {{ match.winner_team }}</span>
                    <span class="pill">A평균 {{ match.team_a_avg }}</span>
                    <span class="pill">B평균 {{ match.team_b_avg }}</span>
                    <span class="pill">{{ match.created_at }}</span>
                </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

SEASON_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>시즌 페이지</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 1100px;
            margin: 40px auto;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
        }
        .filters {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
        }
        select, input, button {
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #e2e8f0;
        }
        .pill {
            display: inline-block;
            padding: 8px 12px;
            border-radius: 999px;
            background: #334155;
            margin-right: 8px;
            margin-bottom: 8px;
            font-size: 13px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            border-bottom: 1px solid #334155;
            text-align: left;
        }
        th { background: #334155; }
        a { color: #60a5fa; text-decoration: none; }
        .muted { color: #94a3b8; }
    </style>
</head>
<body>
<div class="container">
    <h1>🏆 시즌 페이지</h1>
    <p><a href="/">← 홈으로</a></p>

    <div class="card">
        <form method="get" class="filters">
            <input type="number" name="guild_id" placeholder="Guild ID 입력" value="{{ guild_id or '' }}">
            <select name="game">
                <option value="">게임 선택</option>
                {% for g in games %}
                    <option value="{{ g }}" {% if selected_game == g %}selected{% endif %}>{{ g }}</option>
                {% endfor %}
            </select>
            <button type="submit">조회</button>
        </form>
    </div>

    {% if error_message %}
    <div class="card">
        <p>{{ error_message }}</p>
    </div>
    {% endif %}

    {% if season %}
    <div class="card">
        <h2>현재 시즌</h2>
        <div class="pill">서버: {{ season.guild_id }}</div>
        <div class="pill">게임: {{ season.game }}</div>
        <div class="pill">시즌명: {{ season.season_name }}</div>
        <div class="pill">시작일: {{ season.started_at }}</div>
        <div class="pill">상태: {% if season.is_active %}진행 중{% else %}종료{% endif %}</div>
    </div>

    <div class="card">
        <h2>시즌 요약</h2>
        <div class="pill">참가자 수: {{ summary.player_count }}</div>
        <div class="pill">평균 MMR: {{ summary.avg_mmr }}</div>
        <div class="pill">최고 MMR: {{ summary.top_mmr }}</div>
        <div class="pill">경기 수: {{ summary.match_count }}</div>
    </div>

    <div class="card">
        <h2>시즌 랭킹</h2>
        {% if ranking %}
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>닉네임</th>
                    <th>유저 ID</th>
                    <th>MMR</th>
                    <th>승</th>
                    <th>패</th>
                    <th>승률</th>
                </tr>
            </thead>
            <tbody>
                {% for row in ranking %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ row.display_name or "-" }}</td>
                    <td>{{ row.user_id }}</td>
                    <td>{{ row.mmr }}</td>
                    <td>{{ row.win }}</td>
                    <td>{{ row.lose }}</td>
                    <td>{{ row.winrate }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p class="muted">시즌 전적이 아직 없습니다.</p>
        {% endif %}
    </div>

    <div class="card">
        <h2>시즌 최근 경기</h2>
        {% if matches %}
            {% for match in matches %}
            <div style="margin-bottom: 12px;">
                <span class="pill">승리팀 {{ match.winner_team }}</span>
                <span class="pill">A평균 {{ match.team_a_avg }}</span>
                <span class="pill">B평균 {{ match.team_b_avg }}</span>
                <span class="pill">{{ match.created_at }}</span>
            </div>
            {% endfor %}
        {% else %}
        <p class="muted">시즌 경기 기록이 아직 없습니다.</p>
        {% endif %}
    </div>
    {% endif %}
</div>
</body>
</html>
"""

GUIDE_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>명령어 / 프리미엄 소개</title>
</head>
<body style="font-family:Arial; background:#0f172a; color:#e2e8f0; padding:30px;">
<h1>🛟 명령어 / 프리미엄 소개</h1>
<p><a href="/" style="color:#60a5fa;">← 홈으로</a></p>

<h2>기본 명령어</h2>
<p>
/설정역할<br>
/설정카테고리<br>
/내전생성<br>
/밸런스팀<br>
/내전상태<br>
/내전종료
</p>

<h2>프리미엄 기능</h2>
<p>
- 결과기록 / ELO 반영<br>
- 상세 전적<br>
- 게임별 시즌<br>
- 시즌 랭킹 / 시즌 경기 기록<br>
- 추후 맵밴 / 드래프트 / 고급통계 추가 예정
</p>
</body>
</html>
"""

SUPPORT_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>후원 / 프리미엄 신청</title>
</head>
<body style="font-family:Arial; background:#0f172a; color:#e2e8f0; padding:30px;">
<h1>💖 후원 / 프리미엄 신청</h1>
<p><a href="/" style="color:#60a5fa;">← 홈으로</a></p>

<h2>프리미엄 안내</h2>
<p>프리미엄 가격: {{ premium_price }}원 / {{ premium_days }}일</p>

<h2>후원 계좌</h2>
<p>은행: {{ bank_name }}</p>
<p>계좌번호: {{ account_number }}</p>
<p>예금주: {{ account_holder }}</p>

<h2>프리미엄 신청</h2>
<div>
    <p>서버 ID</p>
    <input type="number" id="guildId">
    <p>입금자명</p>
    <input type="text" id="applicantName">
    <p>디스코드 아이디</p>
    <input type="text" id="discordTag">
    <p>입금 금액</p>
    <input type="number" id="amount">
    <p>메모</p>
    <textarea id="memo"></textarea>
    <br><br>
    <button onclick="submitPremiumRequest()">프리미엄 신청하기</button>
    <div id="statusText"></div>
</div>

<script>
async function submitPremiumRequest() {
    const guildId = document.getElementById("guildId").value.trim();
    const applicantName = document.getElementById("applicantName").value.trim();
    const discordTag = document.getElementById("discordTag").value.trim();
    const amount = document.getElementById("amount").value.trim();
    const memo = document.getElementById("memo").value.trim();
    const statusText = document.getElementById("statusText");

    try {
        const response = await fetch("/api/premium/request", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                guild_id: guildId,
                applicant_name: applicantName,
                discord_tag: discordTag,
                amount: amount,
                memo: memo
            })
        });
        const result = await response.json();
        statusText.innerText = result.ok ? ("신청 접수 완료: #" + result.request_id) : result.message;
    } catch (e) {
        statusText.innerText = "오류 발생";
    }
}
</script>
</body>
</html>
"""

PLAYER_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>유저 전적</title>
</head>
<body style="font-family:Arial; background:#0f172a; color:#e2e8f0; padding:30px;">
<p><a href="/" style="color:#60a5fa;">← 홈으로</a></p>

<h1>👤 유저 전적</h1>
<p>닉네임: {{ player.display_name or "-" }}</p>
<p>Guild ID: {{ player.guild_id }}</p>
<p>User ID: {{ player.user_id }}</p>
<p>전체 MMR: {{ player.mmr }}</p>
<p>전체 승: {{ player.win }}</p>
<p>전체 패: {{ player.lose }}</p>
<p>전체 승률: {{ winrate }}%</p>

<h2>게임별 전적</h2>
<table border="1" cellpadding="8" cellspacing="0" style="border-collapse:collapse; color:#e2e8f0;">
    <thead>
        <tr>
            <th>게임</th>
            <th>MMR</th>
            <th>승</th>
            <th>패</th>
            <th>승률</th>
        </tr>
    </thead>
    <tbody>
        {% for row in game_rows %}
        <tr>
            <td>{{ row.game }}</td>
            <td>{{ row.mmr }}</td>
            <td>{{ row.win }}</td>
            <td>{{ row.lose }}</td>
            <td>{{ row.winrate }}%</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
</body>
</html>
"""

LOCKED_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>프리미엄 전용</title>
</head>
<body style="font-family:Arial; background:#0f172a; color:#e2e8f0; padding:30px;">
<h1>🔒 프리미엄 전용</h1>
<p>상세 전적 페이지는 프리미엄 서버 전용입니다.</p>
<p><a href="/support" style="color:#60a5fa;">→ 프리미엄 신청하러 가기</a></p>
</body>
</html>
"""

ADMIN_PREMIUM_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>프리미엄 관리자</title>
</head>
<body style="font-family:Arial; background:#0f172a; color:#e2e8f0; padding:30px;">
<h1>🔐 프리미엄 관리자 페이지</h1>
<p><a href="/" style="color:#60a5fa;">← 홈으로</a></p>

<p>관리자 시크릿 입력</p>
<input type="password" id="adminSecret">
<button onclick="loadRequests()">불러오기</button>

<div id="loginStatus" style="margin-top:12px;"></div>
<hr>
<div id="requestList"></div>

<script>
async function loadRequests() {
    const secret = document.getElementById("adminSecret").value.trim();
    const loginStatus = document.getElementById("loginStatus");
    const requestList = document.getElementById("requestList");

    requestList.innerHTML = "";
    loginStatus.innerText = "";

    try {
        const response = await fetch("/api/admin/premium/requests", {
            method: "GET",
            headers: { "X-Admin-Secret": secret }
        });
        const result = await response.json();

        if (!result.ok) {
            loginStatus.innerText = result.message;
            return;
        }

        loginStatus.innerText = "불러오기 완료";

        if (!result.requests || result.requests.length === 0) {
            requestList.innerHTML = "<p>신청 내역이 없습니다.</p>";
            return;
        }

        requestList.innerHTML = result.requests.map((item) => `
            <div style="border:1px solid #334155; padding:16px; margin-bottom:12px;">
                <div>신청번호: #${item.id}</div>
                <div>서버 ID: ${item.guild_id}</div>
                <div>입금자명: ${item.applicant_name}</div>
                <div>디스코드: ${item.discord_tag || "-"}</div>
                <div>입금 금액: ${item.amount}원</div>
                <div>메모: ${item.memo || "-"}</div>
                <div>상태: ${item.status}</div>
                <div>신청일: ${item.created_at}</div>
                <br>
                <input type="number" id="days-${item.id}" value="30" min="1">
                <button onclick="approveRequest(${item.id})">승인</button>
                <button onclick="rejectRequest(${item.id})">거절</button>
                <div id="status-${item.id}" style="margin-top:10px;"></div>
            </div>
        `).join("");
    } catch (e) {
        loginStatus.innerText = "오류 발생";
    }
}

async function approveRequest(requestId) {
    const secret = document.getElementById("adminSecret").value.trim();
    const days = document.getElementById(`days-${requestId}`).value.trim();
    const statusBox = document.getElementById(`status-${requestId}`);

    try {
        const response = await fetch("/api/admin/premium/approve", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Secret": secret
            },
            body: JSON.stringify({
                request_id: requestId,
                days: days,
                approved_by: "admin_page"
            })
        });
        const result = await response.json();
        statusBox.innerText = result.ok ? ("승인 완료 / premium_until: " + result.premium_until) : result.message;
    } catch (e) {
        statusBox.innerText = "오류 발생";
    }
}

async function rejectRequest(requestId) {
    const secret = document.getElementById("adminSecret").value.trim();
    const statusBox = document.getElementById(`status-${requestId}`);

    try {
        const response = await fetch("/api/admin/premium/reject", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Secret": secret
            },
            body: JSON.stringify({ request_id: requestId })
        });
        const result = await response.json();
        statusBox.innerText = result.ok ? "거절 완료" : result.message;
    } catch (e) {
        statusBox.innerText = "오류 발생";
    }
}
</script>
</body>
</html>
"""


@app.route("/")
def index():
    cleanup_expired_premium_guilds()

    selected_guild_id = request.args.get("guild_id", "").strip()
    selected_game = request.args.get("game", "").strip()
    q = request.args.get("q", "").strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT guild_id FROM players ORDER BY guild_id ASC")
            guild_ids = [row["guild_id"] for row in cur.fetchall()]

            cur.execute("SELECT DISTINCT game FROM player_game_stats ORDER BY game ASC")
            games = [row["game"] for row in cur.fetchall()]

            params = []
            filters = []

            if selected_guild_id:
                filters.append("guild_id = %s")
                params.append(int(selected_guild_id))

            if selected_game:
                filters.append("game = %s")
                params.append(selected_game)

            if q:
                filters.append("(display_name ILIKE %s OR CAST(user_id AS TEXT) ILIKE %s)")
                params.append(f"%{q}%")
                params.append(f"%{q}%")

            if selected_game:
                where_clause = ""
                if filters:
                    safe_filters = []
                    for f in filters:
                        f = f.replace("guild_id", "pgs.guild_id")
                        f = f.replace("game", "pgs.game")
                        f = f.replace("user_id", "pgs.user_id")
                        f = f.replace("display_name", "COALESCE(pgs.display_name, p.display_name)")
                        safe_filters.append(f)
                    where_clause = "WHERE " + " AND ".join(safe_filters)

                ranking_sql = f"""
                    SELECT
                        pgs.guild_id,
                        pgs.user_id,
                        COALESCE(pgs.display_name, p.display_name) AS display_name,
                        pgs.mmr,
                        pgs.win,
                        pgs.lose,
                        CASE
                            WHEN (pgs.win + pgs.lose) = 0 THEN 0
                            ELSE ROUND((CAST(pgs.win AS NUMERIC) / (pgs.win + pgs.lose)) * 100, 1)
                        END AS winrate
                    FROM player_game_stats pgs
                    LEFT JOIN players p
                        ON pgs.guild_id = p.guild_id AND pgs.user_id = p.user_id
                    {where_clause}
                    ORDER BY pgs.mmr DESC, pgs.win DESC
                    LIMIT 50
                """
            else:
                where_clause = ""
                if filters:
                    where_clause = "WHERE " + " AND ".join(filters)

                ranking_sql = f"""
                    SELECT
                        guild_id,
                        user_id,
                        display_name,
                        mmr,
                        win,
                        lose,
                        CASE
                            WHEN (win + lose) = 0 THEN 0
                            ELSE ROUND((CAST(win AS NUMERIC) / (win + lose)) * 100, 1)
                        END AS winrate
                    FROM players
                    {where_clause}
                    ORDER BY mmr DESC, win DESC
                    LIMIT 50
                """

            cur.execute(ranking_sql, tuple(params))
            ranking = cur.fetchall()

            match_params = []
            match_filters = []

            if selected_guild_id:
                match_filters.append("guild_id = %s")
                match_params.append(int(selected_guild_id))

            if selected_game:
                match_filters.append("game = %s")
                match_params.append(selected_game)

            match_where = ""
            if match_filters:
                match_where = "WHERE " + " AND ".join(match_filters)

            cur.execute(
                f"""
                SELECT id, guild_id, game, winner_team, team_a_avg, team_b_avg, created_at
                FROM matches
                {match_where}
                ORDER BY id DESC
                LIMIT 20
                """,
                tuple(match_params)
            )
            matches = cur.fetchall()

    active_premium_count = count_active_premium_guilds()

    return render_template_string(
        INDEX_HTML,
        ranking=ranking,
        matches=matches,
        guild_ids=guild_ids,
        games=games,
        selected_guild_id=selected_guild_id,
        selected_game=selected_game,
        q=q,
        premium_price=PREMIUM_PRICE,
        premium_days=PREMIUM_DAYS,
        active_premium_count=active_premium_count,
    )


@app.route("/season")
def season_page():
    cleanup_expired_premium_guilds()

    guild_id_raw = request.args.get("guild_id", "").strip()
    selected_game = request.args.get("game", "").strip()

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT game FROM player_game_stats ORDER BY game ASC")
            games = [row["game"] for row in cur.fetchall()]

    season = None
    ranking = []
    matches = []
    summary = {"player_count": 0, "avg_mmr": 0, "top_mmr": 0, "match_count": 0}
    error_message = ""

    if guild_id_raw and selected_game:
        if not guild_id_raw.isdigit():
            error_message = "Guild ID는 숫자만 입력해주세요."
        else:
            guild_id = int(guild_id_raw)
            if not is_guild_premium(guild_id):
                error_message = "해당 서버는 프리미엄 서버가 아니어서 시즌 페이지를 사용할 수 없습니다."
            else:
                season = get_active_season(guild_id, selected_game)
                if not season:
                    error_message = "현재 이 게임의 활성 시즌이 없습니다."
                else:
                    ranking = get_season_ranking(guild_id, selected_game, season["id"], limit=50)
                    matches = get_season_matches(guild_id, selected_game, season["id"], limit=20)
                    summary = get_season_stats_summary(guild_id, selected_game, season["id"])

    return render_template_string(
        SEASON_HTML,
        guild_id=guild_id_raw,
        selected_game=selected_game,
        games=games,
        season=season,
        ranking=ranking,
        matches=matches,
        summary=summary,
        error_message=error_message
    )


@app.route("/guide")
def guide_page():
    return render_template_string(GUIDE_HTML)


@app.route("/support")
def support_page():
    return render_template_string(
        SUPPORT_HTML,
        bank_name=BANK_NAME,
        account_number=ACCOUNT_NUMBER,
        account_holder=ACCOUNT_HOLDER,
        premium_price=PREMIUM_PRICE,
        premium_days=PREMIUM_DAYS,
    )


@app.route("/player/<int:guild_id>/<int:user_id>")
def player_page(guild_id, user_id):
    cleanup_expired_premium_guilds()

    if not is_guild_premium(guild_id):
        return render_template_string(LOCKED_HTML)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT guild_id, user_id, display_name, mmr, win, lose
                FROM players
                WHERE guild_id = %s AND user_id = %s
                """,
                (guild_id, user_id)
            )
            player = cur.fetchone()

            cur.execute(
                """
                SELECT game, mmr, win, lose,
                CASE
                    WHEN (win + lose) = 0 THEN 0
                    ELSE ROUND((CAST(win AS NUMERIC) / (win + lose)) * 100, 1)
                END AS winrate
                FROM player_game_stats
                WHERE guild_id = %s AND user_id = %s
                ORDER BY game ASC
                """,
                (guild_id, user_id)
            )
            game_rows = cur.fetchall()

    if not player:
        abort(404)

    total = player["win"] + player["lose"]
    winrate = round((player["win"] / total) * 100, 1) if total > 0 else 0.0

    return render_template_string(
        PLAYER_HTML,
        player=player,
        total=total,
        winrate=winrate,
        game_rows=game_rows
    )


@app.route("/admin/premium")
def admin_premium_page():
    return render_template_string(ADMIN_PREMIUM_HTML)


@app.route("/health")
def health():
    return {"ok": True}


@app.route("/api/premium/request", methods=["POST"])
def api_premium_request():
    try:
        data = request.get_json()

        guild_id = str(data.get("guild_id") or "").strip()
        applicant_name = (data.get("applicant_name") or "").strip()
        discord_tag = (data.get("discord_tag") or "").strip()
        amount = str(data.get("amount") or "").strip()
        memo = (data.get("memo") or "").strip()

        if not guild_id:
            return jsonify({"ok": False, "message": "서버 ID를 입력해주세요."}), 400

        if not guild_id.isdigit():
            return jsonify({"ok": False, "message": "서버 ID는 숫자만 입력해주세요."}), 400

        if not applicant_name:
            return jsonify({"ok": False, "message": "입금자명을 입력해주세요."}), 400

        if not amount:
            return jsonify({"ok": False, "message": "입금 금액을 입력해주세요."}), 400

        if not amount.isdigit():
            return jsonify({"ok": False, "message": "입금 금액은 숫자만 입력해주세요."}), 400

        row = create_premium_request(
            guild_id=int(guild_id),
            applicant_name=applicant_name,
            amount=int(amount),
            discord_tag=discord_tag if discord_tag else None,
            memo=memo if memo else None
        )

        return jsonify({
            "ok": True,
            "message": "프리미엄 신청이 접수되었습니다.",
            "request_id": row["id"]
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


@app.route("/api/admin/premium/requests", methods=["GET"])
def api_admin_premium_requests():
    try:
        secret = request.headers.get("X-Admin-Secret", "").strip()
        if not ADMIN_SECRET or secret != ADMIN_SECRET:
            return jsonify({"ok": False, "message": "관리자 인증 실패"}), 403

        rows = get_premium_requests(limit=200)

        requests_data = []
        for row in rows:
            requests_data.append({
                "id": row["id"],
                "guild_id": row["guild_id"],
                "applicant_name": row["applicant_name"],
                "discord_tag": row.get("discord_tag"),
                "amount": row["amount"],
                "memo": row.get("memo"),
                "status": row["status"],
                "created_at": str(row["created_at"]),
                "approved_at": str(row["approved_at"]) if row.get("approved_at") else None,
                "approved_by": row.get("approved_by"),
            })

        return jsonify({
            "ok": True,
            "requests": requests_data
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


@app.route("/api/admin/premium/approve", methods=["POST"])
def api_admin_premium_approve():
    try:
        secret = request.headers.get("X-Admin-Secret", "").strip()
        if not ADMIN_SECRET or secret != ADMIN_SECRET:
            return jsonify({"ok": False, "message": "관리자 인증 실패"}), 403

        data = request.get_json()
        request_id = str(data.get("request_id") or "").strip()
        days = str(data.get("days") or PREMIUM_DAYS).strip()
        approved_by = (data.get("approved_by") or "admin").strip()

        if not request_id or not request_id.isdigit():
            return jsonify({"ok": False, "message": "request_id가 올바르지 않습니다."}), 400

        if not str(days).isdigit():
            return jsonify({"ok": False, "message": "days는 숫자여야 합니다."}), 400

        row = approve_premium_request(
            request_id=int(request_id),
            days=int(days),
            approved_by=approved_by
        )

        return jsonify({
            "ok": True,
            "message": "프리미엄이 활성화되었습니다.",
            "guild_id": row["guild_id"],
            "premium_until": str(row["premium_until"])
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


@app.route("/api/admin/premium/reject", methods=["POST"])
def api_admin_premium_reject():
    try:
        secret = request.headers.get("X-Admin-Secret", "").strip()
        if not ADMIN_SECRET or secret != ADMIN_SECRET:
            return jsonify({"ok": False, "message": "관리자 인증 실패"}), 403

        data = request.get_json()
        request_id = str(data.get("request_id") or "").strip()

        if not request_id or not request_id.isdigit():
            return jsonify({"ok": False, "message": "request_id가 올바르지 않습니다."}), 400

        row = reject_premium_request(int(request_id))

        if not row:
            return jsonify({"ok": False, "message": "신청 내역을 찾을 수 없습니다."}), 404

        return jsonify({
            "ok": True,
            "message": "프리미엄 신청이 거절 처리되었습니다.",
            "request_id": row["id"]
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)