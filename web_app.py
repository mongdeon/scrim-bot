import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template_string, request, abort

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")
DONATION_URL = "https://toss.me/여기에_후원링크_넣기"


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
        }
        th {
            background: #334155;
        }
        a {
            color: #60a5fa;
            text-decoration: none;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 내전봇 전적 사이트</h1>

        <a href="{{ donation_url }}" target="_blank" class="donate-btn">
            💖 후원하기
        </a>

        <div class="card">
            <h2>🏆 랭킹 TOP 50</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>닉네임</th>
                        <th>MMR</th>
                        <th>승</th>
                        <th>패</th>
                        <th>상세</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in ranking %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ row.display_name or "-" }}</td>
                        <td>{{ row.mmr }}</td>
                        <td>{{ row.win }}</td>
                        <td>{{ row.lose }}</td>
                        <td><a href="/player/{{ row.guild_id }}/{{ row.user_id }}">보기</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
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
            font-family: Arial;
            background: #0f172a;
            color: white;
            padding: 20px;
        }
        .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 16px;
        }
    </style>
</head>
<body>
    <a href="/">← 돌아가기</a>
    <div class="card">
        <h1>{{ player.display_name }}</h1>
        <p>MMR: {{ player.mmr }}</p>
        <p>{{ player.win }}승 {{ player.lose }}패</p>
        <p>승률: {{ winrate }}%</p>
    </div>
</body>
</html>
"""

LOCKED_HTML = """
<h1 style="text-align:center;color:white;margin-top:100px;">
🔒 프리미엄 서버만 상세 전적을 볼 수 있습니다
</h1>
"""


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


@app.route("/")
def index():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT guild_id, user_id, display_name, mmr, win, lose
                FROM players
                ORDER BY mmr DESC
                LIMIT 50
            """)
            ranking = cur.fetchall()

    return render_template_string(
        INDEX_HTML,
        ranking=ranking,
        donation_url=DONATION_URL
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
            row = cur.fetchone()

            if not row or not row["is_premium"]:
                return render_template_string(LOCKED_HTML)

            cur.execute("""
                SELECT * FROM players
                WHERE guild_id=%s AND user_id=%s
            """, (guild_id, user_id))
            player = cur.fetchone()

    if not player:
        abort(404)

    total = player["win"] + player["lose"]
    winrate = round((player["win"] / total) * 100, 1) if total else 0

    return render_template_string(
        PLAYER_HTML,
        player=player,
        winrate=winrate
    )


@app.route("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)