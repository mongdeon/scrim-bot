import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template_string, request, abort

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

BANK_NAME = "토스뱅크"
ACCOUNT_NUMBER = "1000-0103-2111"
ACCOUNT_HOLDER = "김태용"


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
        h1, h2 {
            margin-bottom: 16px;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
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
        th {
            background: #334155;
        }
        a {
            color: #60a5fa;
            text-decoration: none;
        }
        .pill {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #334155;
            margin-right: 8px;
            font-size: 13px;
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
        button {
            cursor: pointer;
            background: #2563eb;
            border: none;
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
        .donate-btn {
            display: inline-block;
            background: #ec4899;
            padding: 10px 16px;
            border-radius: 10px;
            color: white;
            text-decoration: none;
            margin-bottom: 20px;
        }
        @media (max-width: 768px) {
            .top3 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 내전봇 전적 사이트</h1>

        <a href="/support" class="donate-btn">💖 후원하기</a>

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

PLAYER_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>유저 전적</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
        }
        a { color: #60a5fa; text-decoration: none; }
        .stat { margin: 10px 0; font-size: 18px; }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 10px;
            border-bottom: 1px solid #334155;
            text-align: left;
        }
        th { background: #334155; }
    </style>
</head>
<body>
    <div class="container">
        <p><a href="/">← 홈으로</a></p>

        <div class="card">
            <h1>👤 유저 전적</h1>
            <div class="stat">닉네임: {{ player.display_name or "-" }}</div>
            <div class="stat">Guild ID: {{ player.guild_id }}</div>
            <div class="stat">User ID: {{ player.user_id }}</div>
            <div class="stat">전체 MMR: {{ player.mmr }}</div>
            <div class="stat">전체 승: {{ player.win }}</div>
            <div class="stat">전체 패: {{ player.lose }}</div>
            <div class="stat">전체 승률: {{ winrate }}%</div>
        </div>

        <div class="card">
            <h2>🎯 게임별 전적</h2>
            <table>
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
        </div>
    </div>
</body>
</html>
"""

LOCKED_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>프리미엄 전용</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .card {
            background: #1e293b;
            padding: 32px;
            border-radius: 16px;
            text-align: center;
            max-width: 700px;
        }
        a { color: #60a5fa; text-decoration: none; }
        .badge {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 999px;
            background: #f59e0b;
            color: #0f172a;
            font-weight: bold;
            margin-bottom: 16px;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">PREMIUM ONLY</div>
        <h1>상세 전적 페이지는 프리미엄 서버 전용입니다.</h1>
        <p>이 서버는 현재 무료 서버라서 유저 상세 전적을 볼 수 없습니다.</p>
        <p><a href="/">← 홈으로 돌아가기</a></p>
    </div>
</body>
</html>
"""

SUPPORT_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>후원 안내</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
        }
        .card {
            background: #1e293b;
            padding: 32px;
            border-radius: 16px;
            text-align: center;
            max-width: 700px;
            line-height: 1.8;
        }
        a { color: #60a5fa; text-decoration: none; }
        .copy-box {
            background: #334155;
            padding: 12px;
            border-radius: 10px;
            margin: 10px 0;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>💖 개발 후원</h1>
        <p>이 봇이 도움이 되었다면 후원으로 개발을 응원해주세요.</p>

        <p><strong>은행</strong></p>
        <div class="copy-box">{{ bank_name }}</div>

        <p><strong>계좌번호</strong></p>
        <div class="copy-box">{{ account_number }}</div>

        <p><strong>예금주</strong></p>
        <div class="copy-box">{{ account_holder }}</div>

        <p>후원금은 서버비와 기능 업데이트에 사용됩니다.</p>
        <p><a href="/">← 홈으로 돌아가기</a></p>
    </div>
</body>
</html>
"""


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@app.route("/")
def index():
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

            cur.execute(f"""
                SELECT id, guild_id, game, winner_team, team_a_avg, team_b_avg, created_at
                FROM matches
                {match_where}
                ORDER BY id DESC
                LIMIT 20
            """, tuple(match_params))
            matches = cur.fetchall()

    return render_template_string(
        INDEX_HTML,
        ranking=ranking,
        matches=matches,
        guild_ids=guild_ids,
        games=games,
        selected_guild_id=selected_guild_id,
        selected_game=selected_game,
        q=q
    )


@app.route("/player/<int:guild_id>/<int:user_id>")
def player_page(guild_id, user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT is_premium
                FROM premium_guilds
                WHERE guild_id = %s
            """, (guild_id,))
            premium_row = cur.fetchone()
            is_premium = bool(premium_row["is_premium"]) if premium_row else False

            if not is_premium:
                return render_template_string(LOCKED_HTML)

            cur.execute("""
                SELECT guild_id, user_id, display_name, mmr, win, lose
                FROM players
                WHERE guild_id = %s AND user_id = %s
            """, (guild_id, user_id))
            player = cur.fetchone()

            cur.execute("""
                SELECT game, mmr, win, lose,
                CASE
                    WHEN (win + lose) = 0 THEN 0
                    ELSE ROUND((CAST(win AS NUMERIC) / (win + lose)) * 100, 1)
                END AS winrate
                FROM player_game_stats
                WHERE guild_id = %s AND user_id = %s
                ORDER BY game ASC
            """, (guild_id, user_id))
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


@app.route("/support")
def support_page():
    return render_template_string(
        SUPPORT_HTML,
        bank_name=BANK_NAME,
        account_number=ACCOUNT_NUMBER,
        account_holder=ACCOUNT_HOLDER
    )


@app.route("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)