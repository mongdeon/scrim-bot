import os

from flask import Flask, render_template_string, request, jsonify, abort
from psycopg2.extras import RealDictCursor

from core.db import (
    DB,
    init_premium_tables,
    create_premium_request,
    get_premium_requests,
    approve_premium_request,
    reject_premium_request,
    cleanup_expired_premium_guilds,
    get_active_premium_guilds,
    count_active_premium_guilds,
    is_guild_premium,
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
        h1, h2, h3 {
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
            margin-bottom: 8px;
            font-size: 13px;
        }
        .filters {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        select, input, button, textarea {
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #e2e8f0;
        }
        button {
            cursor: pointer;
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
        .action-btn {
            display: inline-block;
            padding: 10px 16px;
            border-radius: 10px;
            color: white;
            text-decoration: none;
            margin-right: 10px;
            margin-bottom: 20px;
        }
        .support-btn {
            background: #22c55e;
        }
        .donate-btn {
            background: #ec4899;
        }
        .admin-btn {
            background: #7c3aed;
        }
        .info-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        .info-chip {
            background: #334155;
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 13px;
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

        <div style="margin-bottom: 20px;">
            <a href="/support" class="action-btn support-btn">🛟 사용법 / 프리미엄</a>
            <a href="/support" class="action-btn donate-btn">💖 후원 / 프리미엄 신청</a>
            <a href="/admin/premium" class="action-btn admin-btn">🔐 관리자 페이지</a>
        </div>

        <div class="info-bar">
            <div class="info-chip">프리미엄 가격: {{ premium_price }}원</div>
            <div class="info-chip">프리미엄 기간: {{ premium_days }}일</div>
            <div class="info-chip">활성 프리미엄 서버 수: {{ active_premium_count }}</div>
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
                <button type="submit" style="background: #2563eb; border: none;">적용</button>
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
            <div class="stat">프리미엄 만료일: {{ premium_until }}</div>
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
        <p>후원 후 프리미엄 신청을 완료하고 승인되면 사용할 수 있습니다.</p>
        <p><a href="/support">→ 프리미엄 신청하러 가기</a></p>
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
    <title>지원 / 프리미엄</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: auto;
        }
        .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 20px;
        }
        h1, h2 {
            margin-bottom: 10px;
        }
        a {
            color: #60a5fa;
            text-decoration: none;
        }
        .copy-box {
            background: #334155;
            padding: 12px;
            border-radius: 10px;
            margin: 10px 0;
            word-break: break-all;
        }
        .form-group {
            margin-bottom: 14px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
        }
        .form-group input, .form-group textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            border-radius: 10px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #e2e8f0;
        }
        .btn {
            background: #ec4899;
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 10px;
            cursor: pointer;
        }
        .status {
            margin-top: 14px;
            font-weight: bold;
        }
        .ok {
            color: #86efac;
        }
        .err {
            color: #fca5a5;
        }
    </style>
</head>
<body>
<div class="container">

<h1>💖 후원 / 프리미엄 신청</h1>

<div class="card">
    <h2>📖 프리미엄 안내</h2>
    <p>프리미엄 가격: {{ premium_price }}원 / {{ premium_days }}일</p>
    <p>후원 입금 후 아래 신청 폼을 작성하면 관리자가 확인 후 프리미엄을 활성화합니다.</p>
    <p>프리미엄 만료 시 자동으로 비활성화됩니다.</p>
</div>

<div class="card">
    <h2>💳 후원 계좌</h2>
    <p><strong>은행</strong></p>
    <div class="copy-box">{{ bank_name }}</div>

    <p><strong>계좌번호</strong></p>
    <div class="copy-box">{{ account_number }}</div>

    <p><strong>예금주</strong></p>
    <div class="copy-box">{{ account_holder }}</div>
</div>

<div class="card">
    <h2>📝 프리미엄 신청</h2>

    <div class="form-group">
        <label for="guildId">서버 ID (Guild ID)</label>
        <input type="number" id="guildId" placeholder="예: 123456789012345678">
    </div>

    <div class="form-group">
        <label for="applicantName">입금자명</label>
        <input type="text" id="applicantName" placeholder="예: 홍길동">
    </div>

    <div class="form-group">
        <label for="discordTag">디스코드 아이디</label>
        <input type="text" id="discordTag" placeholder="예: user1234">
    </div>

    <div class="form-group">
        <label for="amount">입금 금액</label>
        <input type="number" id="amount" placeholder="예: 5000">
    </div>

    <div class="form-group">
        <label for="memo">메모</label>
        <textarea id="memo" placeholder="필요하면 추가 내용을 적어주세요."></textarea>
    </div>

    <button class="btn" onclick="submitPremiumRequest()">프리미엄 신청하기</button>
    <div id="statusText" class="status"></div>
</div>

<p><a href="/">← 홈으로 돌아가기</a></p>

</div>

<script>
async function submitPremiumRequest() {
    const guildId = document.getElementById("guildId").value.trim();
    const applicantName = document.getElementById("applicantName").value.trim();
    const discordTag = document.getElementById("discordTag").value.trim();
    const amount = document.getElementById("amount").value.trim();
    const memo = document.getElementById("memo").value.trim();
    const statusText = document.getElementById("statusText");

    statusText.textContent = "";
    statusText.className = "status";

    if (!guildId) {
        statusText.textContent = "서버 ID를 입력해주세요.";
        statusText.classList.add("err");
        return;
    }

    if (!applicantName) {
        statusText.textContent = "입금자명을 입력해주세요.";
        statusText.classList.add("err");
        return;
    }

    if (!amount) {
        statusText.textContent = "입금 금액을 입력해주세요.";
        statusText.classList.add("err");
        return;
    }

    try {
        const response = await fetch("/api/premium/request", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                guild_id: guildId,
                applicant_name: applicantName,
                discord_tag: discordTag,
                amount: amount,
                memo: memo
            })
        });

        const result = await response.json();

        if (result.ok) {
            statusText.textContent = "프리미엄 신청이 접수되었습니다. 신청번호: " + result.request_id;
            statusText.classList.add("ok");

            document.getElementById("guildId").value = "";
            document.getElementById("applicantName").value = "";
            document.getElementById("discordTag").value = "";
            document.getElementById("amount").value = "";
            document.getElementById("memo").value = "";
        } else {
            statusText.textContent = result.message || "신청 접수에 실패했습니다.";
            statusText.classList.add("err");
        }
    } catch (error) {
        statusText.textContent = "서버와 통신 중 오류가 발생했습니다.";
        statusText.classList.add("err");
    }
}
</script>

</body>
</html>
"""

ADMIN_PREMIUM_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>프리미엄 관리자</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: auto;
        }
        .card {
            background: #1e293b;
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 20px;
        }
        h1, h2 {
            margin-bottom: 12px;
        }
        input, button {
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #e2e8f0;
        }
        button {
            cursor: pointer;
            border: none;
        }
        .btn-login {
            background: #2563eb;
            color: white;
        }
        .btn-approve {
            background: #16a34a;
            color: white;
            margin-right: 8px;
        }
        .btn-reject {
            background: #dc2626;
            color: white;
        }
        .btn-refresh {
            background: #7c3aed;
            color: white;
        }
        .btn-cleanup {
            background: #f59e0b;
            color: #111827;
        }
        .request-card {
            background: #334155;
            padding: 16px;
            border-radius: 14px;
            margin-bottom: 14px;
        }
        .row {
            margin-bottom: 8px;
        }
        .status {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            background: #475569;
            font-size: 12px;
        }
        .ok {
            color: #86efac;
        }
        .err {
            color: #fca5a5;
        }
        .muted {
            color: #94a3b8;
        }
        .hidden {
            display: none;
        }
        .days-input {
            width: 100px;
            margin-right: 8px;
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        @media (max-width: 900px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
<div class="container">
    <h1>🔐 프리미엄 관리자 페이지</h1>

    <div class="card" id="loginCard">
        <h2>관리자 로그인</h2>
        <p class="muted">PREMIUM_ADMIN_SECRET 값을 입력하면 신청 목록과 활성 프리미엄 목록을 불러올 수 있습니다.</p>
        <input type="password" id="adminSecret" placeholder="관리자 시크릿 입력" style="width: 320px;">
        <button class="btn-login" onclick="loadAdminData()">불러오기</button>
        <div id="loginStatus" style="margin-top: 12px;"></div>
    </div>

    <div class="grid-2 hidden" id="adminGrid">
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                <h2>프리미엄 신청 목록</h2>
                <button class="btn-refresh" onclick="loadAdminData()">새로고침</button>
            </div>
            <div id="requestList"></div>
        </div>

        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                <h2>활성 프리미엄 서버</h2>
                <button class="btn-cleanup" onclick="cleanupExpired()">만료 자동 정리 실행</button>
            </div>
            <div id="cleanupStatus" style="margin-bottom: 12px;"></div>
            <div id="activePremiumList"></div>
        </div>
    </div>

    <p><a href="/" style="color:#60a5fa;">← 홈으로 돌아가기</a></p>
</div>

<script>
async function loadAdminData() {
    const secret = document.getElementById("adminSecret").value.trim();
    const loginStatus = document.getElementById("loginStatus");
    const requestList = document.getElementById("requestList");
    const activePremiumList = document.getElementById("activePremiumList");
    const adminGrid = document.getElementById("adminGrid");

    loginStatus.textContent = "";
    requestList.innerHTML = "";
    activePremiumList.innerHTML = "";

    if (!secret) {
        loginStatus.textContent = "관리자 시크릿을 입력해주세요.";
        loginStatus.className = "err";
        return;
    }

    try {
        const response = await fetch("/api/admin/premium/dashboard", {
            method: "GET",
            headers: {
                "X-Admin-Secret": secret
            }
        });

        const result = await response.json();

        if (!result.ok) {
            loginStatus.textContent = result.message || "불러오기에 실패했습니다.";
            loginStatus.className = "err";
            return;
        }

        loginStatus.textContent = "관리자 데이터를 불러왔습니다.";
        loginStatus.className = "ok";
        adminGrid.classList.remove("hidden");

        if (!result.requests || result.requests.length === 0) {
            requestList.innerHTML = "<p class='muted'>신청 내역이 없습니다.</p>";
        } else {
            requestList.innerHTML = result.requests.map((item) => `
                <div class="request-card">
                    <div class="row"><strong>신청번호:</strong> #${item.id}</div>
                    <div class="row"><strong>서버 ID:</strong> ${item.guild_id}</div>
                    <div class="row"><strong>입금자명:</strong> ${item.applicant_name}</div>
                    <div class="row"><strong>디스코드:</strong> ${item.discord_tag || "-"}</div>
                    <div class="row"><strong>입금 금액:</strong> ${item.amount}원</div>
                    <div class="row"><strong>메모:</strong> ${item.memo || "-"}</div>
                    <div class="row"><strong>상태:</strong> <span class="status">${item.status}</span></div>
                    <div class="row"><strong>신청일:</strong> ${item.created_at}</div>
                    <div class="row"><strong>승인자:</strong> ${item.approved_by || "-"}</div>
                    <div class="row" style="margin-top:12px;">
                        <input class="days-input" type="number" id="days-${item.id}" value="30" min="1">
                        <button class="btn-approve" onclick="approveRequest(${item.id})">승인</button>
                        <button class="btn-reject" onclick="rejectRequest(${item.id})">거절</button>
                    </div>
                    <div id="status-${item.id}" style="margin-top:10px;"></div>
                </div>
            `).join("");
        }

        if (!result.active_premiums || result.active_premiums.length === 0) {
            activePremiumList.innerHTML = "<p class='muted'>현재 활성 프리미엄 서버가 없습니다.</p>";
        } else {
            activePremiumList.innerHTML = result.active_premiums.map((item) => `
                <div class="request-card">
                    <div class="row"><strong>서버 ID:</strong> ${item.guild_id}</div>
                    <div class="row"><strong>프리미엄 상태:</strong> ${item.is_premium ? "활성" : "비활성"}</div>
                    <div class="row"><strong>만료일:</strong> ${item.premium_until || "-"}</div>
                    <div class="row"><strong>업데이트일:</strong> ${item.updated_at}</div>
                </div>
            `).join("");
        }
    } catch (error) {
        loginStatus.textContent = "서버와 통신 중 오류가 발생했습니다.";
        loginStatus.className = "err";
    }
}

async function approveRequest(requestId) {
    const secret = document.getElementById("adminSecret").value.trim();
    const days = document.getElementById(`days-${requestId}`).value.trim();
    const statusBox = document.getElementById(`status-${requestId}`);

    statusBox.textContent = "";

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

        if (result.ok) {
            statusBox.textContent = "승인 완료 / premium_until: " + result.premium_until;
            statusBox.className = "ok";
            loadAdminData();
        } else {
            statusBox.textContent = result.message || "승인 실패";
            statusBox.className = "err";
        }
    } catch (error) {
        statusBox.textContent = "서버와 통신 중 오류가 발생했습니다.";
        statusBox.className = "err";
    }
}

async function rejectRequest(requestId) {
    const secret = document.getElementById("adminSecret").value.trim();
    const statusBox = document.getElementById(`status-${requestId}`);

    statusBox.textContent = "";

    try {
        const response = await fetch("/api/admin/premium/reject", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Secret": secret
            },
            body: JSON.stringify({
                request_id: requestId
            })
        });

        const result = await response.json();

        if (result.ok) {
            statusBox.textContent = "거절 완료";
            statusBox.className = "ok";
            loadAdminData();
        } else {
            statusBox.textContent = result.message || "거절 실패";
            statusBox.className = "err";
        }
    } catch (error) {
        statusBox.textContent = "서버와 통신 중 오류가 발생했습니다.";
        statusBox.className = "err";
    }
}

async function cleanupExpired() {
    const secret = document.getElementById("adminSecret").value.trim();
    const cleanupStatus = document.getElementById("cleanupStatus");

    cleanupStatus.textContent = "";

    try {
        const response = await fetch("/api/admin/premium/cleanup-expired", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Admin-Secret": secret
            }
        });

        const result = await response.json();

        if (result.ok) {
            cleanupStatus.textContent = "만료 정리 완료 / 처리된 서버 수: " + result.updated_count;
            cleanupStatus.className = "ok";
            loadAdminData();
        } else {
            cleanupStatus.textContent = result.message || "정리 실패";
            cleanupStatus.className = "err";
        }
    } catch (error) {
        cleanupStatus.textContent = "서버와 통신 중 오류가 발생했습니다.";
        cleanupStatus.className = "err";
    }
}
</script>
</body>
</html>
"""


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return DB.get_connection()


@app.route("/")
def index():
    cleanup_expired_premium_guilds()

    selected_guild_id = request.args.get("guild_id", "").strip()
    selected_game = request.args.get("game", "").strip()
    q = request.args.get("q", "").strip()

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
        active_premium_count=count_active_premium_guilds(),
    )


@app.route("/player/<int:guild_id>/<int:user_id>")
def player_page(guild_id, user_id):
    premium_ok, premium_until = is_guild_premium(guild_id)

    if not premium_ok:
        return render_template_string(LOCKED_HTML)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT guild_id, user_id, display_name, mmr, win, lose
                FROM players
                WHERE guild_id = %s AND user_id = %s
            """, (guild_id, user_id))
            player = cur.fetchone()

            cur.execute("""
                SELECT
                    game,
                    mmr,
                    win,
                    lose,
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
        game_rows=game_rows,
        premium_until=str(premium_until) if premium_until else "-",
    )


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
            discord_tag=discord_tag if discord_tag else None,
            amount=int(amount),
            memo=memo if memo else None,
        )

        return jsonify({
            "ok": True,
            "message": "프리미엄 신청이 접수되었습니다.",
            "request_id": row["id"] if row else None
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


@app.route("/api/admin/premium/dashboard", methods=["GET"])
def api_admin_premium_dashboard():
    try:
        secret = request.headers.get("X-Admin-Secret", "").strip()
        if not ADMIN_SECRET or secret != ADMIN_SECRET:
            return jsonify({"ok": False, "message": "관리자 인증 실패"}), 403

        cleanup_expired_premium_guilds()

        return jsonify({
            "ok": True,
            "requests": [
                {
                    "id": row["id"],
                    "guild_id": row["guild_id"],
                    "applicant_name": row["applicant_name"],
                    "discord_tag": row["discord_tag"],
                    "amount": row["amount"],
                    "memo": row["memo"],
                    "status": row["status"],
                    "created_at": str(row["created_at"]),
                    "approved_at": str(row["approved_at"]) if row["approved_at"] else None,
                    "approved_by": row["approved_by"],
                }
                for row in get_premium_requests()
            ],
            "active_premiums": [
                {
                    "guild_id": row["guild_id"],
                    "is_premium": bool(row["is_premium"]),
                    "premium_until": str(row["premium_until"]) if row["premium_until"] else None,
                    "updated_at": str(row["updated_at"]),
                }
                for row in get_active_premium_guilds()
            ]
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

        if not days.isdigit():
            return jsonify({"ok": False, "message": "days는 숫자여야 합니다."}), 400

        result = approve_premium_request(
            request_id=int(request_id),
            days=int(days),
            approved_by=approved_by,
        )

        if not result["ok"]:
            return jsonify({
                "ok": False,
                "message": result["message"],
            }), result["status_code"]

        data_row = result["data"] or {}

        return jsonify({
            "ok": True,
            "message": result["message"],
            "guild_id": data_row.get("guild_id"),
            "premium_until": str(data_row.get("premium_until")) if data_row.get("premium_until") else None,
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

        result = reject_premium_request(int(request_id))

        if not result["ok"]:
            return jsonify({
                "ok": False,
                "message": result["message"],
            }), result["status_code"]

        data_row = result["data"] or {}

        return jsonify({
            "ok": True,
            "message": result["message"],
            "request_id": data_row.get("id"),
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


@app.route("/api/admin/premium/cleanup-expired", methods=["POST"])
def api_admin_premium_cleanup_expired():
    try:
        secret = request.headers.get("X-Admin-Secret", "").strip()
        if not ADMIN_SECRET or secret != ADMIN_SECRET:
            return jsonify({"ok": False, "message": "관리자 인증 실패"}), 403

        updated_guild_ids = cleanup_expired_premium_guilds()

        return jsonify({
            "ok": True,
            "message": "만료된 프리미엄 서버 정리가 완료되었습니다.",
            "updated_count": len(updated_guild_ids),
            "updated_guild_ids": updated_guild_ids
        })

    except Exception as e:
        return jsonify({
            "ok": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)