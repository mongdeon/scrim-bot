import os
from flask import Flask, render_template_string

app = Flask(__name__)

# Tailwind CSS 및 모던 UI가 적용된 HTML 템플릿
# 별도의 HTML 파일 없이 이 변수에서 웹 페이지의 모든 디자인을 관리합니다.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>내전랩 - 완벽한 디스코드 내전 솔루션</title>
    <!-- Tailwind CSS (CDN) -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome 아이콘 -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <!-- Pretendard 폰트 -->
    <link rel="stylesheet" as="style" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.8/dist/web/static/pretendard.css" />
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Pretendard', 'sans-serif'],
                    },
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

        // 모달 열기/닫기 스크립트
        function openModal(modalId) {
            document.getElementById(modalId).classList.remove('hidden');
            document.getElementById(modalId).classList.add('flex');
            document.body.style.overflow = 'hidden'; // 배경 스크롤 방지
        }

        function closeModal(modalId) {
            document.getElementById(modalId).classList.add('hidden');
            document.getElementById(modalId).classList.remove('flex');
            document.body.style.overflow = 'auto'; // 배경 스크롤 원복
        }

        // 공통 커스텀 알림(Alert) 기능
        function showAlert(message) {
            document.getElementById('alertMessage').innerText = message;
            openModal('alertModal');
        }

        // 관리자 권한 확인 및 모달 열기 (비밀번호 보호)
        function checkAdminAndOpen() {
            // 커스텀 비밀번호 입력 모달 열기
            document.getElementById('adminPasswordInput').value = '';
            document.getElementById('adminAuthError').classList.add('hidden');
            openModal('adminAuthModal');
        }

        // 비밀번호 검증 기능
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

        // 관리자 권한 부여 기능 (프론트 UI 테스트용)
        function grantPremium() {
            const serverId = document.getElementById('adminServerId').value;
            const packageType = document.getElementById('adminPackage').options[document.getElementById('adminPackage').selectedIndex].text;
            if(!serverId) { 
                showAlert("서버 ID를 입력해주세요."); 
                return; 
            }
            showAlert("✅ 서버 ID [" + serverId + "] 에 [" + packageType + "] 권한이 성공적으로 부여되었습니다.");
            closeModal('adminModal');
            document.getElementById('adminServerId').value = '';
        }

        // 임시 전적 검색 기능
        function searchRecords() {
            const resultDiv = document.getElementById('searchResult');
            resultDiv.classList.remove('hidden');
            resultDiv.innerHTML = '<div class="animate-pulse text-discord"><i class="fa-solid fa-spinner fa-spin mr-2"></i>서버 데이터를 불러오는 중...</div>';
            
            setTimeout(() => {
                resultDiv.innerHTML = `
                    <div class="text-left mt-6">
                        <div class="flex items-center gap-4 mb-6">
                            <div class="w-12 h-12 rounded-full bg-gray-700 flex items-center justify-center text-xl font-bold">🎯</div>
                            <div>
                                <h3 class="text-xl font-bold text-white">검색된 서버: 발로란트 내전방</h3>
                                <p class="text-sm text-gray-400">총 진행된 내전: 1,284회</p>
                            </div>
                        </div>
                        <div class="bg-[#121212] rounded-xl p-4 border border-white/5">
                            <p class="text-gray-400 text-sm text-center">웹 대시보드와 DB가 연동되면 이곳에 서버 유저들의 랭킹과 전적이 표시됩니다.</p>
                        </div>
                    </div>
                `;
            }, 800);
        }

        // 계좌번호 복사 기능
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
        body {
            background-color: #0F1014;
            color: #FFFFFF;
            overflow-x: hidden;
        }
        .glass-card {
            background: rgba(30, 30, 30, 0.6);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            transition: transform 0.3s ease, border-color 0.3s ease;
        }
        .glass-card:hover {
            border-color: rgba(88, 101, 242, 0.5);
        }
        .gradient-text {
            background: linear-gradient(135deg, #5865F2, #00D4FF);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .premium-gradient-text {
            background: linear-gradient(135deg, #F5C451, #FF8C00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .glow-button {
            box-shadow: 0 0 15px rgba(88, 101, 242, 0.4);
            transition: all 0.3s ease;
        }
        .glow-button:hover {
            box-shadow: 0 0 25px rgba(88, 101, 242, 0.7);
        }
        
        /* 스크롤바 커스텀 */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0F1014; }
        ::-webkit-scrollbar-thumb { background: #2D2F36; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #5865F2; }
    </style>
</head>
<body class="antialiased min-h-screen flex flex-col font-sans relative">

    <!-- 네비게이션 바 -->
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

    <!-- 히어로 섹션 (메인 화면) -->
    <main class="flex-grow pt-32 pb-12 flex items-center justify-center relative">
        <!-- 배경 장식 효과 -->
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
                    <i class="fa-brands fa-discord text-xl"></i>
                    서버에 봇 초대하기
                </a>
                <button onclick="openModal('manualModal')" class="glass-card hover:bg-white/10 text-white font-semibold py-4 px-8 rounded-lg text-lg flex items-center justify-center gap-2 transition-colors cursor-pointer">
                    <i class="fa-solid fa-book"></i>
                    초보자용 사용 설명서
                </button>
            </div>
        </div>
    </main>

    <!-- 주요 기능 섹션 (패키지별 안내) -->
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
                        <h3 class="text-2xl font-bold text-white mt-4 mb-2">서포터</h3>
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
                
                <!-- 프로 패키지 (강조) -->
                <div class="glass-card p-8 rounded-2xl flex flex-col h-[550px] border-premium/50 shadow-[0_0_30px_rgba(245,196,81,0.1)] relative transform md:-translate-y-4 z-10 bg-gradient-to-b from-[#1E1E1E] to-[#121212]">
                    <div class="absolute -top-3 left-1/2 transform -translate-x-1/2 bg-premium text-[#0F1014] font-extrabold text-xs px-4 py-1.5 rounded-full flex items-center gap-1 shadow-lg">
                        <i class="fa-solid fa-star"></i> BEST PICK
                    </div>
                    <div class="mb-6">
                        <span class="text-premium font-bold tracking-wider text-xs uppercase bg-premium/10 px-3 py-1 rounded-full border border-premium/20">Pro</span>
                        <h3 class="text-3xl font-bold text-white mt-4 mb-2">프로</h3>
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
                        <h3 class="text-2xl font-bold text-white mt-4 mb-2">클랜</h3>
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

    <!-- 서버별 전적 검색 섹션 -->
    <section id="records" class="py-20 relative z-10 bg-[#0F1014] border-t border-white/5">
        <div class="max-w-4xl mx-auto px-6 lg:px-8 text-center">
            <i class="fa-solid fa-magnifying-glass-chart text-4xl text-discord mb-6"></i>
            <h2 class="text-3xl font-bold text-white mb-4">서버별 내전 전적 검색</h2>
            <p class="text-gray-400 mb-10">디스코드 서버에 기록된 유저들의 실시간 랭킹과 전적을 확인해보세요.</p>
            
            <div class="glass-card p-4 rounded-xl flex flex-col sm:flex-row gap-3">
                <div class="relative flex-grow">
                    <i class="fa-solid fa-server absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400"></i>
                    <input type="text" placeholder="서버 이름 또는 서버 ID를 입력하세요" class="w-full bg-[#121212] border border-white/10 rounded-lg pl-12 pr-4 py-4 text-white focus:outline-none focus:border-discord transition-colors placeholder-gray-600" />
                </div>
                <button onclick="searchRecords()" class="bg-discord hover:bg-discordHover text-white px-8 py-4 rounded-lg font-bold transition-colors whitespace-nowrap shadow-lg">
                    전적 검색
                </button>
            </div>

            <!-- 검색 결과 표시 영역 (기본 숨김) -->
            <div id="searchResult" class="hidden mt-8 glass-card p-8 rounded-xl transition-all duration-300">
                <!-- 결과 내용은 스크립트에서 채워집니다 -->
            </div>
        </div>
    </section>

    <!-- 푸터 -->
    <footer class="bg-[#050505] py-10 border-t border-white/10 relative z-10">
        <div class="max-w-7xl mx-auto px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between">
            <div class="flex items-center gap-2 mb-4 md:mb-0">
                <i class="fa-solid fa-gamepad text-discord"></i>
                <span class="text-white font-bold text-xl">내전랩 <span class="text-sm text-gray-500 font-normal">Scrim Lab</span></span>
            </div>
            <p class="text-gray-500 text-sm text-center md:text-left">
                &copy; 2026 Scrim Lab Bot. All rights reserved.<br/>
                디스코드 내전을 가장 스마트하게 관리하는 방법.
            </p>
            <div class="flex gap-5 mt-6 md:mt-0">
                <a href="https://discord.com/oauth2/authorize?client_id=1485512756550570094&permissions=20016128&integration_type=0&scope=bot+applications.commands" target="_blank" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-gray-400 hover:bg-discord hover:text-white transition-all"><i class="fa-brands fa-discord"></i></a>
                <a href="#" class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center text-gray-400 hover:text-white transition-all"><i class="fa-solid fa-envelope"></i></a>
            </div>
        </div>
    </footer>

    <!-- 사용 설명서 모달 -->
    <div id="manualModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col rounded-2xl relative border-discord/30 shadow-[0_0_50px_rgba(88,101,242,0.15)]">
            
            <div class="p-6 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-2xl font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-book-open text-discord"></i> 내전랩 5분 완성 가이드
                </h2>
                <button onclick="closeModal('manualModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center transition-colors">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            
            <div class="p-6 overflow-y-auto custom-scrollbar flex-grow bg-[#0A0A0C]">
                <p class="text-gray-400 mb-8">내전랩 봇을 처음 사용하시나요? 아래 순서대로 슬래시(<code>/</code>) 명령어를 입력하여 내전을 시작해보세요!</p>

                <div class="space-y-6">
                    <!-- Step 1 -->
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-discord text-white flex items-center justify-center font-bold">1</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-discord bg-discord/10 px-2 py-0.5 rounded text-sm mr-2">/설정...</span>초기 설정하기</h3>
                            <p class="text-gray-400 text-sm">봇을 서버에 초대한 후 관리자가 가장 먼저 해야 할 일입니다. <code>/설정보기</code>, <code>/설정역할</code>, <code>/설정카테고리</code>, <code>/설정로그채널</code>, <code>/설정팀결과채널</code>, <code>/설정공지채널</code> 명령어를 통해 서버 환경에 맞게 봇을 세팅합니다.</p>
                        </div>
                    </div>

                    <!-- Step 2 -->
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold">2</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded text-sm mr-2">/내전생성</span>내전 인원 모으기</h3>
                            <p class="text-gray-400 text-sm">명령어를 입력하면 참가 버튼이 있는 패널이 생성됩니다. 서버 유저들은 <strong>[참가하기]</strong> 버튼을 눌러 내전에 등록합니다.</p>
                        </div>
                    </div>

                    <!-- Step 3 -->
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-purple-500 text-white flex items-center justify-center font-bold">3</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded text-sm mr-2">/팀분배</span>밸런스 팀 나누기</h3>
                            <p class="text-gray-400 text-sm">인원이 모두 모이면 이 명령어를 사용하세요. 봇이 유저들의 과거 전적과 MMR을 분석하여 가장 공평한 두 팀(1팀/2팀)으로 알아서 나누어 줍니다.</p>
                        </div>
                    </div>

                    <!-- Step 4 -->
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-red-500 text-white flex items-center justify-center font-bold">4</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-red-400 bg-red-500/10 px-2 py-0.5 rounded text-sm mr-2">/맵뽑기</span>(선택) 맵 정하기</h3>
                            <p class="text-gray-400 text-sm">경기를 진행할 맵을 정해야 한다면 이 명령어를 사용하세요. 해당 게임의 공식 맵들 중에서 무작위로 하나의 맵이 자동으로 뽑힙니다.</p>
                        </div>
                    </div>

                    <!-- Step 5 -->
                    <div class="flex gap-4">
                        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-green-500 text-white flex items-center justify-center font-bold">5</div>
                        <div>
                            <h3 class="text-lg font-bold text-white mb-1"><span class="text-green-400 bg-green-500/10 px-2 py-0.5 rounded text-sm mr-2">/결과기록</span>경기 결과 기록하기</h3>
                            <p class="text-gray-400 text-sm">내전이 끝난 후 이기고 진 팀을 기록합니다. 결과가 반영되면 참가자들의 MMR 점수와 전적이 자동으로 갱신되며 시즌 랭킹에 반영됩니다.</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="p-4 border-t border-white/10 bg-[#121212]/80 text-right">
                <button onclick="closeModal('manualModal')" class="bg-gray-700 hover:bg-gray-600 text-white px-6 py-2 rounded-lg text-sm font-bold transition-colors">닫기</button>
            </div>
        </div>
    </div>

    <!-- 후원/패키지 신청 안내 모달 -->
    <div id="donateModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-md overflow-hidden flex flex-col rounded-2xl relative border-premium/30 shadow-[0_0_50px_rgba(245,196,81,0.15)]">
            
            <div class="p-6 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-xl font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-crown text-premium"></i> 내전랩 패키지 후원
                </h2>
                <button onclick="closeModal('donateModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center transition-colors">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            
            <div class="p-8 bg-[#0A0A0C]">
                <div class="text-center mb-6">
                    <div class="w-16 h-16 bg-premium/20 rounded-full flex items-center justify-center mx-auto mb-4">
                        <i class="fa-solid fa-hand-holding-dollar text-3xl text-premium"></i>
                    </div>
                    <p class="text-gray-300 text-sm leading-relaxed">
                        후원해주신 서버에는<br/>
                        <strong class="text-premium">내전랩 패키지별 프리미엄 기능 권한</strong>이 부여됩니다.
                    </p>
                </div>

                <!-- 후원 계좌 안내 영역 -->
                <div class="bg-[#121212] p-4 rounded-xl border border-white/5 mb-6">
                    <h4 class="text-white font-bold text-sm mb-3 flex items-center"><i class="fa-solid fa-won-sign text-green-400 mr-2"></i>후원 계좌 안내</h4>
                    
                    <div class="flex justify-between items-center bg-black/40 p-3 rounded-lg">
                        <div class="flex flex-col">
                            <span class="text-xs text-gray-500 mb-1">토스뱅크 (예금주: 김태용)</span>
                            <span class="text-gray-300 text-sm font-mono">3333-00-0000000</span>
                        </div>
                        <button onclick="copyAccount('100001032111')" class="text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded transition-colors text-white font-bold">복사</button>
                    </div>
                </div>

                <!-- 프리미엄 신청 절차 영역 -->
                <div class="text-left mb-6">
                    <h4 class="text-white font-bold text-sm mb-3 flex items-center"><i class="fa-brands fa-discord text-discord mr-2"></i>패키지 신청 방법</h4>
                    <ol class="text-sm text-gray-400 space-y-2.5 ml-1">
                        <li class="flex items-start"><span class="text-discord font-bold mr-2">1.</span> 위 계좌로 원하시는 패키지 금액을 후원합니다.</li>
                        <li class="flex items-start"><span class="text-discord font-bold mr-2">2.</span> 아래 버튼을 눌러 공식 디스코드 서버에 입장합니다.</li>
                        <li class="flex items-start"><span class="text-discord font-bold mr-2">3.</span> <span class="bg-white/10 px-1.5 py-0.5 rounded text-gray-200 text-xs mt-0.5 mx-1">#프리미엄-신청</span> 채널에서 티켓을 열고 내역을 남겨주세요.</li>
                    </ol>
                </div>

                <a href="https://discord.gg/FgX5mkY93K" target="_blank" class="flex justify-center items-center gap-2 w-full bg-discord hover:bg-discordHover text-white font-bold py-3.5 rounded-lg transition-colors shadow-lg">
                    <i class="fa-brands fa-discord"></i> 공식 서포트 서버 입장하기
                </a>
            </div>
        </div>
    </div>

    <!-- 관리자 전용 서버 ID 프리미엄 부여 모달 -->
    <div id="adminModal" class="fixed inset-0 z-[100] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-md overflow-hidden flex flex-col rounded-2xl relative border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.15)]">
            
            <div class="p-6 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-xl font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-shield-halved text-red-400"></i> 관리자 대시보드
                </h2>
                <button onclick="closeModal('adminModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center transition-colors">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            
            <div class="p-8 bg-[#0A0A0C]">
                <div class="text-center mb-6">
                    <p class="text-gray-300 text-sm leading-relaxed">
                        계좌 입금 내역을 확인한 후,<br/>
                        대상 서버에 프리미엄 권한을 수동으로 부여합니다.
                    </p>
                </div>

                <div class="space-y-4 mb-6">
                    <div>
                        <label class="block text-sm font-bold text-gray-400 mb-2">디스코드 서버 ID</label>
                        <input type="text" id="adminServerId" placeholder="예: 123456789012345678" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-red-400 transition-colors placeholder-gray-600" />
                    </div>
                    
                    <div>
                        <label class="block text-sm font-bold text-gray-400 mb-2">부여할 패키지 선택</label>
                        <select id="adminPackage" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-red-400 transition-colors appearance-none">
                            <option value="supporter">서포터 (Supporter)</option>
                            <option value="pro">프로 (Pro)</option>
                            <option value="clan">클랜 (Clan)</option>
                        </select>
                    </div>
                </div>

                <button onclick="grantPremium()" class="flex justify-center items-center gap-2 w-full bg-red-500 hover:bg-red-600 text-white font-bold py-3.5 rounded-lg transition-colors shadow-lg">
                    <i class="fa-solid fa-check"></i> 프리미엄 권한 즉시 부여
                </button>
            </div>
        </div>
    </div>

    <!-- 관리자 인증 (비밀번호 입력) 모달 -->
    <div id="adminAuthModal" class="fixed inset-0 z-[110] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-sm overflow-hidden flex flex-col rounded-2xl relative border-red-500/30 shadow-[0_0_50px_rgba(239,68,68,0.15)]">
            <div class="p-5 border-b border-white/10 flex justify-between items-center bg-[#121212]/80">
                <h2 class="text-lg font-bold text-white flex items-center gap-2">
                    <i class="fa-solid fa-lock text-red-400"></i> 관리자 인증
                </h2>
                <button onclick="closeModal('adminAuthModal')" class="text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 w-8 h-8 rounded-full flex items-center justify-center transition-colors">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            </div>
            <div class="p-6 bg-[#0A0A0C]">
                <p class="text-gray-400 text-sm mb-4">관리자 전용 페이지입니다. 비밀번호를 입력하세요.</p>
                <input type="password" id="adminPasswordInput" class="w-full bg-[#121212] border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-red-400 transition-colors mb-2" placeholder="비밀번호 입력" onkeydown="if(event.key === 'Enter') verifyAdminPassword()">
                <p id="adminAuthError" class="text-red-500 text-xs hidden mb-4">⛔ 비밀번호가 일치하지 않습니다.</p>
                <button onclick="verifyAdminPassword()" class="w-full mt-2 bg-red-500 hover:bg-red-600 text-white font-bold py-3 rounded-lg transition-colors">확인</button>
            </div>
        </div>
    </div>
    
    <!-- 커스텀 알림(Alert) 모달 -->
    <div id="alertModal" class="fixed inset-0 z-[120] hidden items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm transition-opacity">
        <div class="glass-card w-full max-w-sm overflow-hidden flex flex-col rounded-2xl relative border-discord/30">
            <div class="p-6 bg-[#0A0A0C] text-center">
                <div class="w-12 h-12 bg-discord/20 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i class="fa-solid fa-circle-info text-2xl text-discord"></i>
                </div>
                <p id="alertMessage" class="text-white text-sm mb-6"></p>
                <button onclick="closeModal('alertModal')" class="w-full bg-discord hover:bg-discordHover text-white font-bold py-3 rounded-lg transition-colors">확인</button>
            </div>
        </div>
    </div>

</body>
</html>
"""

@app.route('/')
def index():
    """
    루트 경로 접속 시 HTML_TEMPLATE을 렌더링하여 반환합니다.
    """
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health_check():
    """웹 서버 및 봇의 상태를 확인하기 위한 API 엔드포인트입니다."""
    return {"status": "online", "bot": "Scrim Lab"}, 200

def run_web_server():
    """
    Flask 서버를 실행하는 함수입니다.
    Heroku 등의 환경에서 PORT 환경 변수를 받아 사용합니다.
    """
    port = int(os.environ.get('PORT', 8080))
    # debug=False로 설정하여 프로덕션 환경에 맞게 구동합니다.
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    run_web_server()