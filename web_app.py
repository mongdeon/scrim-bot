import os
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template_string, request, jsonify, abort

from core.db import (
    init_premium_tables,
    cleanup_expired_premium_guilds,
    create_premium_request,
    get_premium_requests,
    approve_premium_request,
    reject_premium_request,
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

SUPPORT_SERVER_URL = os.environ.get("SUPPORT_SERVER_URL", "").strip()

init_premium_tables()
cleanup_expired_premium_guilds()


def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


BASE_STYLE = """
<style>
    * { box-sizing: border-box; }
    body {
        font-family: Arial, sans-serif;
        background: #071633;
        color: #e2e8f0;
        margin: 0;
        padding: 0;
    }
    .container {
        max-width: 1280px;
        margin: 0 auto;
        padding: 28px 16px 60px;
    }
    h1, h2, h3 {
        margin: 0 0 16px 0;
    }
    .page-title {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 18px;
    }
    .action-row {
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        margin-bottom: 20px;
    }
    .action-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 14px 22px;
        border-radius: 12px;
        color: white;
        text-decoration: none;
        font-weight: 700;
        border: none;
        cursor: pointer;
        min-width: 170px;
    }
    .btn-guide { background: linear-gradient(135deg, #22c55e, #16a34a); }
    .btn-support { background: linear-gradient(135deg, #ec4899, #d946ef); }
    .btn-admin { background: linear-gradient(135deg, #8b5cf6, #6366f1); }

    .info-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 18px;
    }
    .pill {
        display: inline-block;
        padding: 10px 14px;
        border-radius: 999px;
        background: #24344f;
        color: #e2e8f0;
        font-size: 14px;
        font-weight: 700;
    }

    .card {
        background: #1f2f49;
        border-radius: 20px;
        padding: 20px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.18);
    }

    .filters {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        align-items: center;
    }

    select, input, textarea, button {
        font: inherit;
    }

    select, input, textarea {
        padding: 12px 14px;
        border-radius: 12px;
        border: 1px solid #425472;
        background: #08162f;
        color: #e2e8f0;
        outline: none;
    }

    textarea {
        width: 100%;
        min-height: 120px;
        resize: vertical;
    }

    .search-input {
        min-width: 260px;
    }

    .submit-btn {
        background: #2f6fe4;
        color: white;
        border: none;
        padding: 12px 18px;
        border-radius: 12px;
        font-weight: 700;
        cursor: pointer;
    }

    .top3 {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-bottom: 24px;
    }

    .top-card {
        background: #394b67;
        border-radius: 18px;
        padding: 18px;
    }

    .top-card h3 {
        font-size: 20px;
        margin-bottom: 16px;
    }

    .top-card p {
        margin: 0 0 12px;
        font-size: 18px;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        overflow: hidden;
        border-radius: 12px;
    }

    th, td {
        padding: 14px 12px;
        border-bottom: 1px solid #334155;
        text-align: left;
    }

    th {
        background: #394b67;
        font-weight: 800;
    }

    tr:last-child td {
        border-bottom: none;
    }

    a {
        color: #60a5fa;
        text-decoration: none;
    }

    .match-list {
        display: flex;
        flex-direction: column;
        gap: 14px;
    }

    .match-item {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }

    .chip {
        display: inline-block;
        padding: 8px 12px;
        border-radius: 999px;
        background: #324766;
        font-size: 14px;
        font-weight: 700;
    }

    .section-title {
        font-size: 18px;
        font-weight: 800;
        margin-bottom: 16px;
    }

    .copy-box {
        background: #394b67;
        padding: 14px;
        border-radius: 12px;
        margin: 8px 0 16px;
        word-break: break-all;
    }

    .form-group {
        margin-bottom: 14px;
    }

    .form-group label {
        display: block;
        margin-bottom: 8px;
        font-weight: 700;
    }

    .status {
        margin-top: 14px;
        font-weight: 800;
    }

    .ok { color: #86efac; }
    .err { color: #fca5a5; }
    .muted { color: #94a3b8; }

    .admin-login-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
    }

    .request-card {
        background: #394b67;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 14px;
    }

    .request-row {
        margin-bottom: 8px;
    }

    .status-badge {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #24344f;
        font-size: 12px;
        font-weight: 800;
    }

    .days-input {
        width: 100px;
        margin-right: 8px;
    }

    .inline-actions {
        margin-top: 12px;
    }

    .approve-btn {
        background: #16a34a;
        color: white;
        border: none;
        padding: 10px 14px;
        border-radius: 10px;
        cursor: pointer;
        font-weight: 700;
        margin-right: 8px;
    }

    .reject-btn {
        background: #dc2626;
        color: white;
        border: none;
        padding: 10px 14px;
        border-radius: 10px;
        cursor: pointer;
        font-weight: 700;
    }

    .guide-list {
        display: grid;
        gap: 14px;
    }

    .guide-item {
        background: #394b67;
        padding: 18px;
        border-radius: 16px;
    }

    .guide-item h3 {
        margin-bottom: 10px;
        font-size: 20px;
    }

    .guide-item p {
        margin: 0;
        line-height: 1.7;
    }

    @media (max-width: 900px) {
        .top3 {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 640px) {
        .action-btn {
            width: 100%;
        }
        .search-input {
            min-width: 100%;
        }
    }
</style>
"""

INDEX_HTML = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>내전봇 전적 사이트</title>
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="page-title">🎮 내전봇 전적 사이트</div>

        <div class="action-row">
            <a href="/guide" class="action-btn btn-guide">🛟 사용법 / 프리미엄</a>
            <a href="/support" class="action-btn btn-support">💖 후원 / 프리미엄 신청</a>
            <a href="/admin/premium" class="action-btn btn-admin">🔐 관리자 페이지</a>
        </div>

        <div class="info-row">
            <span class="pill">프리미엄 가격: {{ premium_price }}원</span>
            <span class="pill">프리미엄 기간: {{ premium_days }}일</span>
            <span class="pill">활성 프리미엄 서버 수: {{ active_premium_count }}</span>
        </div>

        <div class="card">
            <form method="get" class="filters">
                <select name="guild_id">
                    <option value="">전체 서버</option>
                    {{% for gid in guild_ids %}}
                        <option value="{{{{ gid }}}}" {{% if selected_guild_id == gid|string %}}selected{{% endif %}}>Guild {{{{ gid }}}}</option>
                    {{% endfor %}}
                </select>

                <select name="game">
                    <option value="">전체 게임</option>
                    {{% for g in games %}}
                        <option value="{{{{ g }}}}" {{% if selected_game == g %}}selected{{% endif %}}>{{{{ g }}}}</option>
                    {{% endfor %}}
                </select>

                <input class="search-input" type="text" name="q" placeholder="닉네임 또는 유저 ID 검색" value="{{{{ q or '' }}}}">
                <button type="submit" class="submit-btn">적용</button>
            </form>
        </div>

        {{% if ranking|length >= 1 %}}
        <div class="top3">
            {{% for row in ranking[:3] %}}
            <div class="top-card">
                <h3>#{{{{ loop.index }}}} {{{{ row.display_name or row.user_id }}}}</h3>
                <p>MMR {{{{ row.mmr }}}}</p>
                <p>{{{{ row.win }}}}승 {{{{ row.lose }}}}패 | 승률 {{{{ row.winrate }}}}%</p>
            </div>
            {{% endfor %}}
        </div>
        {{% endif %}}

        <div class="card">
            <h2 class="section-title">🏆 랭킹 TOP 50</h2>
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
                    {{% for row in ranking %}}
                    <tr>
                        <td>{{{{ loop.index }}}}</td>
                        <td>{{{{ row.display_name or "-" }}}}</td>
                        <td>{{{{ row.user_id }}}}</td>
                        <td>{{{{ row.mmr }}}}</td>
                        <td>{{{{ row.win }}}}</td>
                        <td>{{{{ row.lose }}}}</td>
                        <td>{{{{ row.winrate }}}}%</td>
                        <td><a href="/player/{{{{ row.guild_id }}}}/{{{{ row.user_id }}}}">보기</a></td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2 class="section-title">📝 최근 경기</h2>
            <div class="match-list">
                {{% for match in matches %}}
                <div class="match-item">
                    <span class="chip">Guild {{{{ match.guild_id }}}}</span>
                    <span class="chip">{{{{ match.game }}}}</span>
                    <span class="chip">승리팀 {{{{ match.winner_team }}}}</span>
                    <span class="chip">A평균 {{{{ match.team_a_avg }}}}</span>
                    <span class="chip">B평균 {{{{ match.team_b_avg }}}}</span>
                    <span class="chip">{{{{ match.created_at }}}}</span>
                </div>
                {{% endfor %}}
            </div>
        </div>
    </div>
</body>
</html>
"""

GUIDE_HTML = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>사용법 / 프리미엄</title>
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="page-title">🛟 사용법 / 프리미엄</div>

        <div class="action-row">
            <a href="/" class="action-btn btn-guide">🏠 홈으로</a>
            <a href="/support" class="action-btn btn-support">💖 후원 / 프리미엄 신청</a>
            <a href="/admin/premium" class="action-btn btn-admin">🔐 관리자 페이지</a>
        </div>

        <div class="card">
            <h2 class="section-title">📘 기본 사용 순서</h2>
            <div class="guide-list">
                <div class="guide-item">
                    <h3>1. /설정역할</h3>
                    <p>내전에 참여할 수 있는 인증 역할을 설정합니다. 해당 역할이 있는 유저만 내전 참가와 생성이 가능합니다.</p>
                </div>

                <div class="guide-item">
                    <h3>2. /설정카테고리</h3>
                    <p>내전용 음성 채널이 자동 생성될 카테고리를 설정합니다. A팀 / B팀 / 대기방 생성에 사용됩니다.</p>
                </div>

                <div class="guide-item">
                    <h3>3. /내전생성</h3>
                    <p>현재 채널에 내전 모집 메시지를 생성합니다. 게임 종류와 팀 인원 수를 입력하면 참가 버튼이 포함된 모집창이 만들어집니다.</p>
                </div>

                <div class="guide-item">
                    <h3>4. 참가 버튼</h3>
                    <p>참가자는 버튼을 눌러 포지션과 MMR을 입력해 참가합니다. 모집 중에는 참가취소 버튼도 사용할 수 있습니다.</p>
                </div>

                <div class="guide-item">
                    <h3>5. /밸런스팀</h3>
                    <p>현재 참가자 기준으로 MMR 밸런스를 계산해 A팀 / B팀을 자동으로 나눕니다.</p>
                </div>

                <div class="guide-item">
                    <h3>6. /결과기록 A 또는 /결과기록 B</h3>
                    <p>경기 종료 후 승리팀을 기록합니다. 프리미엄 서버에서는 ELO/MMR과 전적이 자동 반영됩니다.</p>
                </div>

                <div class="guide-item">
                    <h3>7. /내전종료</h3>
                    <p>현재 로비를 종료하고 팀 음성 채널을 정리합니다. 남은 인원은 대기방으로 이동됩니다.</p>
                </div>
            </div>
        </div>

        <div class="card">
            <h2 class="section-title">⭐ 프리미엄 기능</h2>
            <div class="guide-list">
                <div class="guide-item">
                    <h3>상세 전적 페이지</h3>
                    <p>프리미엄 서버만 유저 상세 전적 페이지를 열 수 있습니다.</p>
                </div>
                <div class="guide-item">
                    <h3>ELO / 결과기록 기능</h3>
                    <p>프리미엄 서버는 결과기록과 함께 ELO/MMR 반영이 가능합니다.</p>
                </div>
                <div class="guide-item">
                    <h3>프리미엄 가격</h3>
                    <p>{{{{ premium_price }}}}원 / {{{{ premium_days }}}}일 기준으로 운영됩니다.</p>
                </div>
            </div>
        </div>

        {{% if support_server_url %}}
        <div class="card">
            <h2 class="section-title">🛟 서포트 서버</h2>
            <p>문의나 공지는 디스코드 서포트 서버에서 확인할 수 있습니다.</p>
            <p><a href="{{{{ support_server_url }}}}" target="_blank">서포트 서버 들어가기</a></p>
        </div>
        {{% endif %}}
    </div>
</body>
</html>
"""

SUPPORT_HTML = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>후원 / 프리미엄 신청</title>
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="page-title">💖 후원 / 프리미엄 신청</div>

        <div class="action-row">
            <a href="/guide" class="action-btn btn-guide">🛟 사용법 / 프리미엄</a>
            <a href="/" class="action-btn btn-support">🏠 홈으로</a>
            <a href="/admin/premium" class="action-btn btn-admin">🔐 관리자 페이지</a>
        </div>

        <div class="card">
            <h2 class="section-title">📖 프리미엄 안내</h2>
            <p>프리미엄 가격: <strong>{{{{ premium_price }}}}원 / {{{{ premium_days }}}}일</strong></p>
            <p>후원 입금 후 아래 신청 폼을 작성하면 관리자가 확인 후 프리미엄을 활성화합니다.</p>
            <p>프리미엄 만료 시 자동으로 비활성화됩니다.</p>
        </div>

        <div class="card">
            <h2 class="section-title">💳 후원 계좌</h2>
            <p><strong>은행</strong></p>
            <div class="copy-box">{{{{ bank_name }}}}</div>

            <p><strong>계좌번호</strong></p>
            <div class="copy-box">{{{{ account_number }}}}</div>

            <p><strong>예금주</strong></p>
            <div class="copy-box">{{{{ account_holder }}}}</div>
        </div>

        <div class="card">
            <h2 class="section-title">📝 프리미엄 신청</h2>

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

            <button class="submit-btn" onclick="submitPremiumRequest()">프리미엄 신청하기</button>
            <div id="statusText" class="status"></div>
        </div>
    </div>

<script>
async function submitPremiumRequest() {{
    const guildId = document.getElementById("guildId").value.trim();
    const applicantName = document.getElementById("applicantName").value.trim();
    const discordTag = document.getElementById("discordTag").value.trim();
    const amount = document.getElementById("amount").value.trim();
    const memo = document.getElementById("memo").value.trim();
    const statusText = document.getElementById("statusText");

    statusText.textContent = "";
    statusText.className = "status";

    if (!guildId) {{
        statusText.textContent = "서버 ID를 입력해주세요.";
        statusText.classList.add("err");
        return;
    }}

    if (!applicantName) {{
        statusText.textContent = "입금자명을 입력해주세요.";
        statusText.classList.add("err");
        return;
    }}

    if (!amount) {{
        statusText.textContent = "입금 금액을 입력해주세요.";
        statusText.classList.add("err");
        return;
    }}

    try {{
        const response = await fetch("/api/premium/request", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json"
            }},
            body: JSON.stringify({{
                guild_id: guildId,
                applicant_name: applicantName,
                discord_tag: discordTag,
                amount: amount,
                memo: memo
            }})
        }});

        const result = await response.json();

        if (result.ok) {{
            statusText.textContent = "프리미엄 신청이 접수되었습니다. 신청번호: " + result.request_id;
            statusText.classList.add("ok");

            document.getElementById("guildId").value = "";
            document.getElementById("applicantName").value = "";
            document.getElementById("discordTag").value = "";
            document.getElementById("amount").value = "";
            document.getElementById("memo").value = "";
        }} else {{
            statusText.textContent = result.message || "신청 접수에 실패했습니다.";
            statusText.classList.add("err");
        }}
    }} catch (error) {{
        statusText.textContent = "서버와 통신 중 오류가 발생했습니다.";
        statusText.classList.add("err");
    }}
}}
</script>
</body>
</html>
"""

PLAYER_HTML = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>유저 전적</title>
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="action-row">
            <a href="/" class="action-btn btn-guide">🏠 홈으로</a>
        </div>

        <div class="card">
            <h1>👤 유저 전적</h1>
            <p>닉네임: {{{{ player.display_name or "-" }}}}</p>
            <p>Guild ID: {{{{ player.guild_id }}}}</p>
            <p>User ID: {{{{ player.user_id }}}}</p>
            <p>전체 MMR: {{{{ player.mmr }}}}</p>
            <p>전체 승: {{{{ player.win }}}}</p>
            <p>전체 패: {{{{ player.lose }}}}</p>
            <p>전체 승률: {{{{ winrate }}}}%</p>
        </div>

        <div class="card">
            <h2 class="section-title">🎯 게임별 전적</h2>
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
                    {{% for row in game_rows %}}
                    <tr>
                        <td>{{{{ row.game }}}}</td>
                        <td>{{{{ row.mmr }}}}</td>
                        <td>{{{{ row.win }}}}</td>
                        <td>{{{{ row.lose }}}}</td>
                        <td>{{{{ row.winrate }}}}%</td>
                    </tr>
                    {{% endfor %}}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

LOCKED_HTML = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>프리미엄 전용</title>
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>🔒 프리미엄 전용</h1>
            <p>상세 전적 페이지는 프리미엄 서버 전용입니다.</p>
            <p>후원 후 프리미엄 신청을 완료하고 승인되면 사용할 수 있습니다.</p>
            <p><a href="/support">→ 프리미엄 신청하러 가기</a></p>
            <p><a href="/">← 홈으로 돌아가기</a></p>
        </div>
    </div>
</body>
</html>
"""

ADMIN_PREMIUM_HTML = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>프리미엄 관리자</title>
    {BASE_STYLE}
</head>
<body>
    <div class="container">
        <div class="page-title">🔐 프리미엄 관리자 페이지</div>

        <div class="action-row">
            <a href="/" class="action-btn btn-guide">🏠 홈으로</a>
            <a href="/guide" class="action-btn btn-support">🛟 사용법</a>
            <a href="/support" class="action-btn btn-admin">💖 프리미엄 신청 페이지</a>
        </div>

        <div class="card">
            <h2 class="section-title">관리자 로그인</h2>
            <p class="muted">PREMIUM_ADMIN_SECRET 값을 입력하면 신청 목록을 불러올 수 있습니다.</p>
            <div class="admin-login-row">
                <input type="password" id="adminSecret" placeholder="관리자 시크릿 입력" style="min-width:320px;">
                <button class="submit-btn" onclick="loadRequests()">불러오기</button>
            </div>
            <div id="loginStatus" class="status"></div>
        </div>

        <div class="card">
            <h2 class="section-title">프리미엄 신청 목록</h2>
            <div id="requestList"></div>
        </div>
    </div>

<script>
async function loadRequests() {{
    const secret = document.getElementById("adminSecret").value.trim();
    const loginStatus = document.getElementById("loginStatus");
    const requestList = document.getElementById("requestList");

    loginStatus.textContent = "";
    loginStatus.className = "status";
    requestList.innerHTML = "";

    if (!secret) {{
        loginStatus.textContent = "관리자 시크릿을 입력해주세요.";
        loginStatus.classList.add("err");
        return;
    }}

    try {{
        const response = await fetch("/api/admin/premium/requests", {{
            method: "GET",
            headers: {{
                "X-Admin-Secret": secret
            }}
        }});

        const result = await response.json();

        if (!result.ok) {{
            loginStatus.textContent = result.message || "불러오기에 실패했습니다.";
            loginStatus.classList.add("err");
            return;
        }}

        loginStatus.textContent = "신청 목록을 불러왔습니다.";
        loginStatus.classList.add("ok");

        if (!result.requests || result.requests.length === 0) {{
            requestList.innerHTML = "<p class='muted'>신청 내역이 없습니다.</p>";
            return;
        }}

        requestList.innerHTML = result.requests.map((item) => `
            <div class="request-card">
                <div class="request-row"><strong>신청번호:</strong> #${{item.id}}</div>
                <div class="request-row"><strong>서버 ID:</strong> ${{item.guild_id}}</div>
                <div class="request-row"><strong>입금자명:</strong> ${{item.applicant_name}}</div>
                <div class="request-row"><strong>디스코드:</strong> ${{item.discord_tag || "-"}}</div>
                <div class="request-row"><strong>입금 금액:</strong> ${{item.amount}}원</div>
                <div class="request-row"><strong>메모:</strong> ${{item.memo || "-"}}</div>
                <div class="request-row"><strong>상태:</strong> <span class="status-badge">${{item.status}}</span></div>
                <div class="request-row"><strong>신청일:</strong> ${{item.created_at}}</div>

                <div class="inline-actions">
                    <input class="days-input" type="number" id="days-${{item.id}}" value="30" min="1">
                    <button class="approve-btn" onclick="approveRequest(${{item.id}})">승인</button>
                    <button class="reject-btn" onclick="rejectRequest(${{item.id}})">거절</button>
                </div>

                <div id="status-${{item.id}}" class="status"></div>
            </div>
        `).join("");
    }} catch (error) {{
        loginStatus.textContent = "서버와 통신 중 오류가 발생했습니다.";
        loginStatus.classList.add("err");
    }}
}}

async function approveRequest(requestId) {{
    const secret = document.getElementById("adminSecret").value.trim();
    const days = document.getElementById(`days-${{requestId}}`).value.trim();
    const statusBox = document.getElementById(`status-${{requestId}}`);

    statusBox.textContent = "";
    statusBox.className = "status";

    try {{
        const response = await fetch("/api/admin/premium/approve", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json",
                "X-Admin-Secret": secret
            }},
            body: JSON.stringify({{
                request_id: requestId,
                days: days,
                approved_by: "admin_page"
            }})
        }});

        const result = await response.json();

        if (result.ok) {{
            statusBox.textContent = "승인 완료 / premium_until: " + result.premium_until;
            statusBox.classList.add("ok");
            loadRequests();
        }} else {{
            statusBox.textContent = result.message || "승인 실패";
            statusBox.classList.add("err");
        }}
    }} catch (error) {{
        statusBox.textContent = "서버와 통신 중 오류가 발생했습니다.";
        statusBox.classList.add("err");
    }}
}}

async function rejectRequest(requestId) {{
    const secret = document.getElementById("adminSecret").value.trim();
    const statusBox = document.getElementById(`status-${{requestId}}`);

    statusBox.textContent = "";
    statusBox.className = "status";

    try {{
        const response = await fetch("/api/admin/premium/reject", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json",
                "X-Admin-Secret": secret
            }},
            body: JSON.stringify({{
                request_id: requestId
            }})
        }});

        const result = await response.json();

        if (result.ok) {{
            statusBox.textContent = "거절 완료";
            statusBox.classList.add("ok");
            loadRequests();
        }} else {{
            statusBox.textContent = result.message || "거절 실패";
            statusBox.classList.add("err");
        }}
    }} catch (error) {{
        statusBox.textContent = "서버와 통신 중 오류가 발생했습니다.";
        statusBox.classList.add("err");
    }}
}}
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


@app.route("/guide")
def guide_page():
    return render_template_string(
        GUIDE_HTML,
        premium_price=PREMIUM_PRICE,
        premium_days=PREMIUM_DAYS,
        support_server_url=SUPPORT_SERVER_URL,
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