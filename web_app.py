import os
from flask import Flask, render_template_string, request, jsonify
import asyncio
from core.db import set_premium_days

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>내전랩 - 완벽한 디스코드 내전 솔루션</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css" />
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Pretendard', 'sans-serif'] },
                    colors: {
                        discord: '#5865F2',
                        discordHover: '#4752C4',
                        darkBg: '#0F1014',
                        cardBg: '#1E1E1E',
                        premium: '#F5C451',
                    }
                }
            }
        }

        function openModal(modalId) {
            document.getElementById(modalId).classList.remove('hidden');
            document.getElementById(modalId).classList.add('flex');
            document.body.style.overflow = 'hidden'; 
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.add('hidden');
            document.getElementById(modalId).classList.remove('flex');
            document.body.style.overflow = 'auto'; 
        }

        function showAlert(message) {
            document.getElementById('alertMessage').innerText = message;
            openModal('alertModal');
        }

        function checkAdminAndOpen() {
            document.getElementById('adminPasswordInput').value = '';
            document.getElementById('adminAuthError').classList.add('hidden');
            openModal('adminAuthModal');
        }

        function verifyAdminPassword() {
            const password = document.getElementById('adminPasswordInput').value;
            const ADMIN_PASSWORD = "secretlabcode07128"; 

            if (password === ADMIN_PASSWORD) {
                closeModal('adminAuthModal');
                openModal('adminModal');
            } else {
                document.getElementById('adminAuthError').classList.remove('hidden');
            }
        }

        async function grantPremium() {
            const serverId = document.getElementById('adminServerId').value;
            const packageType = document.getElementById('adminPackage').options[document.getElementById('adminPackage').selectedIndex].text;
            const password = document.getElementById('adminPasswordInput').value;

            if(!serverId) { 
                showAlert("서버 ID를 입력해주세요."); 
                return; 
            }
            
            try {
                const response = await fetch('/api/premium', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        guild_id: serverId,
                        package_type: packageType,
                        password: password
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    showAlert(result.message);
                    closeModal('adminModal');
                    document.getElementById('adminServerId').value = '';
                } else {
                    showAlert("⛔ 오류: " + result.message);
                }
            } catch (error) {
                showAlert("❌ 서버 통신 중 오류가 발생했습니다.");
            }
        }

        function searchRecords() {
            const searchInput = document.getElementById('searchInput').value;
            const gameSelect = document.getElementById('gameSelect');
            const selectedGameName = gameSelect.options[gameSelect.selectedIndex].text;
            
            if(!searchInput) {
                showAlert("검색할 서버 이름이나 ID를 입력해주세요.");
                return;
            }

            const resultDiv = document.getElementById('searchResult');
            resultDiv.classList.remove('hidden');
            resultDiv.innerHTML = '<div class="animate-pulse text-discord text-center py-8"><i class="fa-solid fa-spinner fa-spin mr-2"></i>서버 데이터를 불러오는 중...</div>';
            
            const dummyMatches = Math.floor(Math.random() * 500) + 50;

            setTimeout(() => {
                resultDiv.innerHTML = `
                    <div class="text-left mt-2">
                        <div class="flex flex-col md:flex-row md:items-center justify-between border-b border-white/10 pb-4 mb-6">
                            <div class="flex items-center gap-4 mb-4 md:mb-0">
                                <div class="w-14 h-14 rounded-full bg-discord/20 flex items-center justify-center text-2xl font-bold border border-discord/50 text-discord">
                                    <i class="fa-solid fa-server"></i>
                                </div>
                                <div>
                                    <h3 class="text-2xl font-bold text-white tracking-tight">${searchInput}</h3>
                                    <p class="text-sm text-gray-400 mt-1">
                                        <span class="inline-block w-2 h-2 rounded-full bg-green-500 mr-1"></span>
                                        실시간 데이터 동기화 완료
                                    </p>
                                </div>
                            </div>
                            <div class="bg-[#121212] px-4 py-2 rounded-lg border border-white/5 flex items-center gap-3 shadow-inner">
                                <span class="text-gray-400 text-sm">선택된 게임</span>
                                <span class="text-discord font-bold bg-discord/10 px-3 py-1 rounded-md text-sm border border-discord/20">${selectedGameName}</span>
                            </div>
                        </div>
                        
                        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                            <div class="bg-[#121212] p-5 rounded-xl border border-white/5 text-center transition-colors hover:border-discord/50">
                                <p class="text-gray-400 text-sm mb-2"><i class="fa-solid fa-gamepad mr-1"></i> 누적 진행 내전</p>
                                <p class="text-3xl font-bold text-white">${dummyMatches}<span class="text-sm font-normal text-gray-500 ml-1">회</span></p>
                            </div>
                            <div class="bg-[#121212] p-5 rounded-xl border border-white/5 text-center transition-colors hover:border-discord/50">
                                <p class="text-gray-400 text-sm mb-2"><i class="fa-solid fa-users mr-1"></i> 등록된 유저 수</p>
                                <p class="text-3xl font-bold text-white">${Math.floor(dummyMatches * 1.5)}<span class="text-sm font-normal text-gray-500 ml-1">명</span></p>
                            </div>
                            <div class="bg-[#121212] p-5 rounded-xl border border-premium/30 text-center relative overflow-hidden group">
                                <p class="text-gray-400 text-sm mb-2"><i class="fa-solid fa-ranking-star mr-1 text-premium"></i> 현재 시즌 랭킹</p>
                                <p class="text-2xl font-bold text-white opacity-20 blur-[2px] mt-1">시즌 1 진행중</p>
                                <div class="absolute inset-0 bg-black/80 backdrop-blur-[2px] flex flex-col items-center justify-center border border-premium/20 rounded-xl cursor-not-allowed">
                                    <i class="fa-solid fa-lock text-premium text-xl mb-1"></i>
                                    <span class="text-xs text-premium font-bold">Pro 패키지 전용</span>
                                </div>
                            </div>
                        </div>

                        <div class="bg-black/40 rounded-xl p-8 border border-white/5 relative overflow-hidden flex flex-col items-center justify-center">
                            <div class="w-16 h-16 bg-premium/10 rounded-full flex items-center justify-center text-premium mb-4 border border-premium/20">
                                <i class="fa-solid fa-lock text-2xl"></i>
                            </div>
                            <h4 class="text-lg font-bold text-white mb-2">상세 전적 데이터는 Pro 권한이 필요합니다.</h4>
                            <p class="text-sm text-gray-400 text-center max-w-md">
                                내전랩 Pro 패키지를 이용 중인 서버는 이곳에 <strong>${selectedGameName}</strong> 종목의 유저별 티어, 승률, 모스트 맵 등 세부 통계가 표시됩니다.
                            </p>
                            <button onclick="openModal('donateModal')" class="mt-6 bg-white/5 hover:bg-white/10 text-white font-bold py-2 px-6 rounded-lg transition-colors border border-white/10 text-sm">
                                패키지 안내 보기
                            </button>
                        </div>
                    </div>
                `;
            }, 800);
        }

        function copyAccount(text) {
            try {
                const textArea = document.createElement("textarea");
                textArea.value = text;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand("copy");
                document.body.removeChild(textArea);
                showAlert("계좌번호가 복사되었습니다.");
            } catch (err) {
                showAlert("계좌번호 복사에 실패했습니다.");
            }
        }
    </script>
    <style>
        body { background-color: #0F1014; color: #FFFFFF; overflow-x: hidden; }
        .glass-card { background: rgba(30, 30, 30, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); transition: transform 0.3s ease, border-color 0.3s ease; }
        .glass-card:hover { border-color: rgba(88, 101, 242, 0.5); }
        .gradient-text { background: linear-gradient(135deg, #5865F2, #00D4FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .glow-button { box-shadow: 0 0 15px rgba(88, 101, 242, 0.4); transition: all 0.3s ease; }
        .glow-button:hover { box-shadow: 0 0 25px rgba(88, 101, 242, 0.7); }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0F1014; }
        ::-webkit-scrollbar-thumb { background: #2D2F36; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #5865F2; }
    </style>
</head>
<body class="antialiased min-h-screen flex flex-col font-sans relative">

    <nav class="fixed w-full z-50 glass-card border-b border-white/10" style="transform: none !important;">
        <div class="max-w-7xl mx-auto px-6 lg:px-8">
            <div class="flex items-center justify-between h-16">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-discord flex items-center justify-center">
                        <i class="fa-solid fa-gamepad text-white text-sm"></i>
                    </div>
                    <span class="font-bold text-xl tracking-tight text-white">내전랩</span>
                </div>
                <div class="hidden md:block">
                    <div class="ml-10 flex items-center space-x-6">
                        <a href="#features" class="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors">기능 소개</a>
                        <a href="#records" class="text-gray-300 hover:text-white px-3 py-2 rounded-md text-sm font-medium transition-colors">서버 전적</a>
                        <button onclick="openModal('donateModal')" class="text-premium hover:text-white px-3 py-2 rounded-md text-sm font-bold transition-colors flex items-center gap-1">
                            <i class="fa-solid fa-crown"></i> 후원하기
                        </button>
                        <button onclick="checkAdminAndOpen()" class="text-red-400 hover:text-red-300 px-3 py-2 rounded-md text-sm font-bold transition-colors flex items-center gap-1">
                            <i class="fa-solid fa-shield-halved"></i> 관리자
                        </button>
                        <a href="https://discord.com/oauth2/authorize?client_id=1485512756550570094&permissions=20016128&integration_type=0&scope=bot+applications.commands" target="_blank" class="bg-discord hover:bg-discordHover text-white px-4 py-2 rounded-md text-sm font-bold transition-colors shadow-lg ml-2">
                            <i class="fa-brands fa-discord mr-1"></i> 디스코드 추가
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </nav>

    <main class="flex-grow pt-32 pb-12 flex items-center justify-center relative">
        <div class="absolute top-1/4 left-1/4 w-96 h-96 bg-discord/20 rounded-full blur-[120px] pointer-events-none"></div>
        <div class="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-500/20 rounded-full blur-[120px] pointer-events-none"></div>

        <div class="max-w-7xl mx-auto px-6 lg:px-8 relative z-10 text-center mt-8 mb-12">
            <h1 class="text-5xl md:text-7xl font-extrabold tracking-tight mb-6">
                당신의 디스코드 서버를 위한<br/>
                <span class="gradient-text">완벽한 내전 봇</span>
            </h1>
            <p class="mt-4 max-w-2xl mx-auto text-xl text-gray-400 mb-10 leading-relaxed">
                MMR 기반 자동 팀 밸런싱부터 맵 밴픽, 체계적인 시즌 랭킹 전적까지.<br/>
                내전랩 봇 하나로 모든 귀찮은 과정을 자동화하세요.
            </p>
            <div class="flex flex-col sm:flex-row justify-center gap-4">
                <a href="https://discord.com/oauth2/authorize?client_id=1485512756550570094&permissions=20016128&integration_type=0&scope=bot+applications.commands" target="_blank" class="glow-button bg-discord hover:bg-discordHover text-white font-bold py-4 px-8 rounded-lg text-lg flex items-center justify-center gap-2">
                    <i class="fa-brands fa-discord text-xl"></i> 서버에 봇 초대하기
                </a>
                <button onclick="openModal('manualModal')" class="glass-card hover:bg-white/10 text-white font-semibold py-4 px-8 rounded-lg text-lg flex items-center justify-center gap-2 transition-colors cursor-pointer">
                    <i class="fa-solid fa-book"></i> 초보자용 사용 설명서
                </button>
            </div>
        </div>
    </main>

    <section id="features" class="py-20 relative z-10 bg-[#0A0A0C]">
        <div class="max-w-7xl mx-auto px-6 lg:px-8">
            <div class="text-center mb-16">
                <h2 class="text-3xl font-bold text-white mb-4">내전랩 패키지 안내</h2>
                <p class="text-gray-400">서버의 규모와 운영 방식에 맞는 최적의 패키지를 선택하세요.</p>
                <div class="w-16 h-1 bg-discord mx-auto rounded-full mt-6"></div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
                
                <!-- 서포터 패키지 -->
                <div class="glass-card p-8 rounded-2xl flex flex-col h-[500px] hover:-translate-y-2 transition-transform duration-300">
                    <div class="mb-6">
                        <span class="text-blue-400 font-bold tracking-wider text-xs uppercase bg-blue-500/10 px-3 py-1 rounded-full border border-blue-500/20">Supporter</span>
                        <h3 class="text-2xl font-bold text-white mt-4 mb-1">서포터</h3>
                        <div class="flex items-baseline gap-1 mb-2">
                            <span class="text-3xl font-extrabold text-white">3,000</span>
                            <span class="text-gray-400 font-medium">원 / 30일</span>
                        </div>
                        <p class="text-gray-400 text-sm">소규모 내전 서버를 위한 기본 강화 패키지</p>
                    </div>
                    <ul class="space-y-4 mb-8 flex-grow">
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-discord mt-0.5"></i>
                            <span>자동 맵 뽑기 기능 지원</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-discord mt-0.5"></i>
                            <span>유저 프로필 서포터 역할 부여</span>
                        </li>
                    </ul>
                    <button onclick="openModal('donateModal')" class="w-full py-3 rounded-lg font-bold bg-white/5 hover:bg-white/10 text-white border border-white/10 transition-colors">자세히 보기</button>
                </div>
                
                <!-- 프로 패키지 -->
                <div class="glass-card p-8 rounded-2xl flex flex-col h-[550px] border-premium/50 shadow-[0_0_30px_rgba(245,196,81,0.1)] relative transform md:-translate-y-4 z-10 bg-gradient-to-b from-[#1E1E1E] to-[#121212]">
                    <div class="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-premium text-[#0F1014] font-extrabold text-xs px-4 py-1.5 rounded-full flex items-center gap-1 shadow-lg">
                        <i class="fa-solid fa-star"></i> BEST PICK
                    </div>
                    <div class="mb-6">
                        <span class="text-premium font-bold tracking-wider text-xs uppercase bg-premium/10 px-3 py-1 rounded-full border border-premium/20">Pro</span>
                        <h3 class="text-3xl font-bold text-white mt-4 mb-1">프로</h3>
                        <div class="flex items-baseline gap-1 mb-2">
                            <span class="text-4xl font-extrabold text-white">4,990</span>
                            <span class="text-gray-400 font-medium">원 / 30일</span>
                        </div>
                        <p class="text-gray-400 text-sm">가장 인기있는 체계적인 내전 운영 패키지</p>
                    </div>
                    <ul class="space-y-4 mb-8 flex-grow">
                        <li class="flex items-start gap-3 text-sm text-gray-300 font-medium">
                            <i class="fa-solid fa-plus text-premium mt-0.5"></i>
                            <span class="text-white">서포터 패키지의 모든 기능 포함</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-premium mt-0.5"></i>
                            <span>정규 시즌제 및 티어 랭킹 시스템</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-premium mt-0.5"></i>
                            <span>상세 전적 분석 스탯 제공</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-premium mt-0.5"></i>
                            <span>서버 맞춤형 커스텀 전적 프로필 생성</span>
                        </li>
                    </ul>
                    <button onclick="openModal('donateModal')" class="w-full py-4 rounded-lg font-bold bg-premium hover:bg-yellow-500 text-[#0F1014] transition-colors shadow-lg shadow-premium/20">패키지 신청하기</button>
                </div>

                <!-- 클랜 패키지 -->
                <div class="glass-card p-8 rounded-2xl flex flex-col h-[500px] hover:-translate-y-2 transition-transform duration-300">
                    <div class="mb-6">
                        <span class="text-purple-400 font-bold tracking-wider text-xs uppercase bg-purple-500/10 px-3 py-1 rounded-full border border-purple-500/20">Clan</span>
                        <h3 class="text-2xl font-bold text-white mt-4 mb-1">클랜</h3>
                        <div class="flex items-baseline gap-1 mb-2">
                            <span class="text-3xl font-extrabold text-white">6,990</span>
                            <span class="text-gray-400 font-medium">원 / 30일</span>
                        </div>
                        <p class="text-gray-400 text-sm">대규모 클랜 및 커뮤니티 전용 프리미엄 패키지</p>
                    </div>
                    <ul class="space-y-4 mb-8 flex-grow">
                        <li class="flex items-start gap-3 text-sm text-gray-300 font-medium">
                            <i class="fa-solid fa-plus text-purple-400 mt-0.5"></i>
                            <span class="text-white">프로 패키지의 모든 기능 포함</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-discord mt-0.5"></i>
                            <span>서버 전용 독립 봇 (이름/프사 커스텀)</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-discord mt-0.5"></i>
                            <span>클랜전 전용 매칭 및 통계 시스템</span>
                        </li>
                        <li class="flex items-start gap-3 text-sm text-gray-300">
                            <i class="fa-solid fa-check text-discord mt-0.5"></i>
                            <span>매칭 서버 최우선 할당 및 딜레이 제거</span>
                        </li>
                    </ul>
                    <button onclick="openModal('donateModal')" class="w-full py-3 rounded-lg font-bold bg-white/5 hover:bg-white/10 text-white border border-white/10 transition-colors">자세히 보기</button>
                </div>
            </div>
        </div>
    </section>

    <section id="records" class="py-20 relative z-10 bg-[#0F1014] border-t border-white/5">
        <div class="max-w-4xl mx-auto px-6 lg:px-8 text-center">
            <i class="fa-solid fa-magnifying-glass-chart text-4xl text-discord mb-6"></i>
            <h2 class="text-3xl font-bold text-white mb-4">서버별 내전 전적 검색</h2>
            <p class="text-gray-400 mb-10">디스코드 서버에 기록된 유저들의 실시간 랭킹과 전적을 확인해보세요.</p>
            
            <div class="glass-card p-4 rounded-xl flex flex-col sm:flex-row gap-3">
                <div class="relative flex-grow">
                    <i class="fa-solid fa-server absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input type="text" id="searchInput" placeholder="서버 이름 또는 서버 ID를 입력하세요" class="w-full bg-[#121212] border border-white/10 rounded-lg pl-12 pr-4 py-4 text-white focus:outline-none focus:border-discord transition-colors placeholder-gray-600" />
                </div>
                <div class="relative w-full sm:w-48">
                    <select id="gameSelect" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-4 text-white focus:outline-none focus:border-discord transition-colors appearance-none cursor-pointer font-medium">
                        <option value="valorant">발로란트</option>
                        <option value="lol">리그 오브 레전드</option>
                        <option value="overwatch">오버워치 2</option>
                        <option value="pubg">배틀그라운드</option>
                    </select>
                    <i class="fa-solid fa-chevron-down absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none"></i>
                </div>
                <button onclick="searchRecords()" class="bg-discord hover:bg-discordHover text-white px-8 py-4 rounded-lg font-bold transition-colors whitespace-nowrap shadow-lg">전적 검색</button>
            </div>
            <div id="searchResult" class="hidden mt-8 glass-card p-8 rounded-xl transition-all duration-300"></div>
        </div>
    </section>

    <footer class="bg-[#050505] py-10 border-t border-white/10 relative z-10">
        <div class="max-w-7xl mx-auto px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between">
            <div class="flex items-center gap-2 mb-4 md:mb-0">
                <i class="fa-solid fa-gamepad text-discord"></i>
                <span class="text-white font-bold text-xl">내전랩 <span class="text-sm text-gray-500 font-normal">Scrim Lab</span></span>
            </div>
            <p class="text-gray-500 text-sm text-center md:text-left">
                &copy; 2026 Scrim Lab Bot. All rights reserved.<br/>디스코드 내전을 가장 스마트하게 관리하는 방법.
            </p>
            <div class="flex gap-5 mt-6 md:mt-0">
                <a href="https://discord.com/oauth2/authorize?client_id=1485512756550570094&permissions=20016128&integration_type=0&scope=bot+applications.commands" target="_blank" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-gray-400 hover:bg-discord hover:text-white transition-all"><i class="fa-brands fa-discord"></i></a>
                <a href="#" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-gray-400 hover:text-white transition-all"><i class="fa-solid fa-envelope"></i></a>
            </div>
        </div>
    </footer>

    <!-- 모달 레이아웃 구조 -->
    <div id="manualModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col rounded-2xl relative border-discord/30 shadow-[0_0_50px_rgba(88,101,242,0.15)]">
            <div class="p-6 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-2xl font-bold text-white flex items-center gap-2"><i class="fa-solid fa-book-open text-discord"></i> 내전랩 5분 완성 가이드</h2>
                <button onclick="closeModal('manualModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="p-6 overflow-y-auto custom-scrollbar flex-grow bg-[#0A0A0C]">
                <div class="space-y-6">
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-discord text-white flex items-center justify-center font-bold">1</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-discord bg-discord/10 px-2 py-0.5 rounded text-sm mr-2">/설정...</span>초기 설정하기</h3>
                            <p class="text-gray-400 text-sm">봇을 서버에 초대한 후 관리자가 가장 먼저 해야 할 일입니다. <code>/설정보기</code> 등을 설정합니다.</p>
                        </div>
                    </div>
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold">2</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded text-sm mr-2">/내전생성</span>내전 인원 모으기</h3>
                            <p class="text-gray-400 text-sm">명령어를 입력해 참가 패널을 생성하고 유저를 등록받습니다.</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="p-4 border-t border-white/10 bg-[#121212]/80 text-right">
                <button onclick="closeModal('manualModal')" class="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded-lg text-sm font-bold">닫기</button>
            </div>
        </div>
    </div>

    <div id="donateModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-md overflow-hidden flex flex-col rounded-2xl relative border-premium/30 shadow-[0_0_50px_rgba(245,196,81,0.15)]">
            <div class="p-6 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-xl font-bold text-white flex items-center gap-2"><i class="fa-solid fa-crown text-premium"></i> 내전랩 패키지 후원</h2>
                <button onclick="closeModal('donateModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="p-8 bg-[#0A0A0C]">
                <div class="bg-[#121212] p-4 rounded-xl border border-white/5 mb-6">
                    <h4 class="text-white font-bold text-sm mb-3 flex items-center"><i class="fa-solid fa-won-sign text-green-400 mr-2"></i>후원 계좌 안내</h4>
                    <div class="flex justify-between items-center bg-black/40 p-3 rounded-lg">
                        <div class="flex flex-col">
                            <span class="text-xs text-gray-500 mb-1">토스뱅크 (예금주: 김태용)</span>
                            <span class="text-gray-300 text-sm font-mono">1000-0103-2111</span>
                        </div>
                        <button onclick="copyAccount('100001032111')" class="text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded text-white font-bold">복사</button>
                    </div>
                </div>
                <a href="https://discord.gg/FgX5mkY93K" target="_blank" class="flex justify-center items-center gap-2 w-full bg-discord hover:bg-discordHover text-white font-bold py-3.5 rounded-lg shadow-lg">
                    <i class="fa-brands fa-discord"></i> 공식 서포트 서버 입장하기
                </a>
            </div>
        </div>
    </div>

    <div id="adminModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-md overflow-hidden flex flex-col rounded-2xl relative border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.15)]">
            <div class="p-6 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-xl font-bold text-white flex items-center gap-2"><i class="fa-solid fa-shield-halved text-red-400"></i> 관리자 대시보드</h2>
                <button onclick="closeModal('adminModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="p-8 bg-[#0A0A0C]">
                <div class="space-y-4 mb-6">
                    <div>
                        <label class="block text-sm font-bold text-gray-400 mb-2">디스코드 서버 ID</label>
                        <input type="text" id="adminServerId" placeholder="예: 123456789012345678" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-red-400 placeholder-gray-600" />
                    </div>
                    <div>
                        <label class="block text-sm font-bold text-gray-400 mb-2">부여할 패키지 선택</label>
                        <select id="adminPackage" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-red-400 appearance-none">
                            <option value="supporter">서포터 (Supporter)</option>
                            <option value="pro">프로 (Pro)</option>
                            <option value="clan">클랜 (Clan)</option>
                        </select>
                    </div>
                </div>
                <button onclick="grantPremium()" class="flex justify-center items-center gap-2 w-full bg-red-500 hover:bg-red-600 text-white font-bold py-3.5 rounded-lg shadow-lg"><i class="fa-solid fa-check"></i> 프리미엄 권한 즉시 부여</button>
            </div>
        </div>
    </div>

    <div id="adminAuthModal" class="fixed inset-0 z-[110] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-sm overflow-hidden flex flex-col rounded-2xl relative border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.15)]">
            <div class="p-5 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-lg font-bold text-white flex items-center gap-2"><i class="fa-solid fa-lock text-red-400"></i> 관리자 인증</h2>
                <button onclick="closeModal('adminAuthModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center"><i class="fa-solid fa-xmark"></i></button>
            </div>
            <div class="p-6 bg-[#0A0A0C]">
                <p class="text-gray-400 text-sm mb-4">관리자 전용 페이지입니다. 비밀번호를 입력하세요.</p>
                <input type="password" id="adminPasswordInput" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-red-400 mb-2" placeholder="비밀번호 입력" onkeydown="if(event.key === 'Enter') verifyAdminPassword()">
                <p id="adminAuthError" class="text-red-500 text-xs hidden mb-4">⛔ 비밀번호가 일치하지 않습니다.</p>
                <button onclick="verifyAdminPassword()" class="w-full mt-2 bg-red-500 hover:bg-red-600 text-white font-bold py-3 rounded-lg">확인</button>
            </div>
        </div>
    </div>
    
    <div id="alertModal" class="fixed inset-0 z-[120] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-sm overflow-hidden flex flex-col rounded-2xl relative border-discord/30">
            <div class="p-6 bg-[#0A0A0C] text-center">
                <div class="w-12 h-12 bg-discord/20 rounded-full flex items-center justify-center mx-auto mb-4"><i class="fa-solid fa-circle-info text-2xl text-discord"></i></div>
                <p id="alertMessage" class="text-white text-sm mb-6"></p>
                <button onclick="closeModal('alertModal')" class="w-full bg-discord hover:bg-discordHover text-white font-bold py-3">확인</button>
            </div>
        </div>
    </div>

</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/premium', methods=['POST'])
def api_grant_premium():
    data = request.json
    guild_id = data.get('guild_id')
    package_type = data.get('package_type')
    password = data.get('password')

    if password != "secretlabcode07128":
        return jsonify({"success": False, "message": "권한이 거부되었습니다. 비밀번호를 확인해주세요."}), 403

    if not guild_id or not package_type:
        return jsonify({"success": False, "message": "서버 ID와 패키지 종류가 정확하지 않습니다."}), 400

    plan_map = {
        "서포터 (Supporter)": "supporter",
        "프로 (Pro)": "pro",
        "클랜 (Clan)": "clan"
    }
    plan_key = plan_map.get(package_type, "supporter")
    
    try:
        asyncio.run(set_premium_days(int(guild_id), days=30, plan_key=plan_key))
        return jsonify({"success": True, "message": f"서버 ID [{guild_id}]에 [{package_type}] 권한이 성공적으로 부여되었습니다!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"데이터베이스 업데이트 실패: {str(e)}"}), 500

@app.route('/health')
def health_check():
    return {"status": "online", "bot": "Scrim Lab"}, 200

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    run_web_server()