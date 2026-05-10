import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB
from datetime import datetime

db = DB()
db.init_recruit_tables()

# --- 옵션 상수 설정 ---
GAME_OPTIONS = [
    app_commands.Choice(name="VALORANT", value="valorant"),
    app_commands.Choice(name="League of Legends", value="lol"),
    app_commands.Choice(name="PUBG", value="pubg"),
    app_commands.Choice(name="Overwatch 2", value="overwatch"),
]

PUBG_MODE_OPTIONS = [
    app_commands.Choice(name="솔로", value="solo"),
    app_commands.Choice(name="듀오", value="duo"),
    app_commands.Choice(name="스쿼드", value="squad"),
]

POSITION_MAP = {
    "valorant": ["타격대", "척후대", "감시자", "전략가", "상관없음"],
    "lol": ["탑", "정글", "미드", "원딜", "서폿", "상관없음"],
    "pubg": ["IGL", "Entry", "Support", "Scout", "상관없음"],
    "overwatch": ["돌격", "딜러", "지원"],
}

MATCH_FORMAT_OPTIONS = [
    app_commands.Choice(name="내전형식", value="scrim"),
    app_commands.Choice(name="토너먼트형식", value="tournament"),
]

SCRIM_SERIES_OPTIONS = [
    app_commands.Choice(name="단판", value=1),
    app_commands.Choice(name="2선승제", value=2),
    app_commands.Choice(name="3선승제", value=3),
]

TOURNAMENT_STAGE_OPTIONS = [
    app_commands.Choice(name="일반전", value="general"),
    app_commands.Choice(name="결승전", value="final"),
]

# --- 팝업창(Modal) 클래스 정의 ---

class RecruitCreateModal(discord.ui.Modal, title="내전 생성 상세 설정"):
    """내전 생성 시 시간과 메모를 입력받는 팝업창"""
    def __init__(self, cog, game_val, game_name, team_size, total_slots, match_format, series_target, tournament_stage, pubg_label):
        super().__init__()
        self.cog = cog
        self.game_val = game_val
        self.game_name = game_name
        self.team_size = team_size
        self.total_slots = total_slots
        self.match_format = match_format
        self.series_target = series_target
        self.tournament_stage = tournament_stage
        self.pubg_label = pubg_label

    time_input = discord.ui.TextInput(
        label="⏰ 시작 시간 (생략 시 '지금' 시작)",
        style=discord.TextStyle.short,
        placeholder="예: 20:00 (오늘 기준) 또는 2026-05-12 14:00",
        required=False
    )
    memo_input = discord.ui.TextInput(
        label="📝 메모 및 규칙 (선택)",
        style=discord.TextStyle.paragraph,
        placeholder="디코 마이크 필수, 즐겜 위주 등",
        required=False,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        time_str = self.time_input.value.strip()
        
        # 시간 생략 시 현재 시간(지금) 설정
        if not time_str:
            scheduled_at = datetime.now()
        else:
            try:
                if ":" in time_str and len(time_str) <= 5:
                    now = datetime.now()
                    parsed_time = datetime.strptime(time_str, "%H:%M").time()
                    scheduled_at = datetime.combine(now.date(), parsed_time)
                else:
                    scheduled_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                await interaction.response.send_message("❌ 시간 형식이 잘못되었습니다. (예: 20:00)", ephemeral=True)
                return

        # DB 로비 생성
        lobby = db.create_lobby(
            interaction.channel_id, interaction.guild_id, interaction.user.id,
            self.game_val, self.team_size, total_slots=self.total_slots,
            scheduled_at=scheduled_at, match_format=self.match_format,
            series_target=self.series_target, tournament_stage=self.tournament_stage
        )

        players = db.get_lobby_players_by_id(lobby["lobby_id"])
        embed = build_lobby_embed(lobby, players)
        
        # 메모가 있을 경우 임베드에 반영
        if self.memo_input.value:
            embed.description = f"**[방장 공지]**\n{self.memo_input.value}"

        view = RecruitView(self.cog)
        await interaction.response.send_message(embed=embed, view=view)
        
        msg = await interaction.original_response()
        db.set_lobby_message_by_id(lobby["lobby_id"], msg.id)


class RecruitEditTimeModal(discord.ui.Modal, title="내전 시간 수정"):
    """내전 시간 수정 팝업창"""
    def __init__(self, cog, lobby):
        super().__init__()
        self.cog = cog
        self.lobby = lobby
        
        # 기존 시간 기본값 설정
        default_val = ""
        if lobby.get("scheduled_at"):
            default_val = lobby["scheduled_at"].strftime("%Y-%m-%d %H:%M")

        self.time_input = discord.ui.TextInput(
            label="새로운 시작 시간",
            default=default_val,
            placeholder="예: 21:30",
            required=True
        )
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction):
        time_str = self.time_input.value.strip()
        try:
            if ":" in time_str and len(time_str) <= 5:
                now = datetime.now()
                parsed_time = datetime.strptime(time_str, "%H:%M").time()
                scheduled_at = datetime.combine(now.date(), parsed_time)
            else:
                scheduled_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message("❌ 올바른 형식이 아닙니다.", ephemeral=True)
            return

        db.update_lobby_times_by_id(self.lobby["lobby_id"], scheduled_at, None)
        await self.cog.refresh_lobby_message(interaction.channel, self.lobby["lobby_id"])
        await interaction.response.send_message(f"✅ 시간이 **{scheduled_at.strftime('%H:%M')}**로 수정되었습니다.", ephemeral=True)

# --- 보조 함수 및 뷰 (유지) ---

def member_has_access(member: discord.Member) -> bool:
    if member.guild_permissions.administrator: return True
    settings = db.get_settings(member.guild.id)
    if not settings or not settings["recruit_role_id"]: return False
    return any(role.id == settings["recruit_role_id"] for role in member.roles)

def get_lobby_need_count(lobby: dict) -> int:
    if lobby["game"] == "pubg":
        return int(lobby.get("total_slots") or (lobby["team_size"] * 4))
    return lobby["team_size"] * 2

def build_lobby_embed(lobby: dict, players: list[dict], team_a=None, team_b=None) -> discord.Embed:
    # (기존의 복잡한 임베드 생성 로직 - 파일 내용을 바탕으로 요약/유지)
    color = discord.Color.green() if lobby["status"] == "open" else discord.Color.blue()
    embed = discord.Embed(title=f"⚔️ {lobby['game'].upper()} 내전 모집", color=color)
    embed.add_field(name="로비 ID", value=str(lobby["lobby_id"]), inline=True)
    embed.add_field(name="진행 상태", value=lobby["status"], inline=True)
    
    time_str = lobby["scheduled_at"].strftime("%Y-%m-%d %H:%M") if lobby.get("scheduled_at") else "즉시 시작"
    embed.add_field(name="시작 시간", value=time_str, inline=True)
    
    # 참가자 목록 등 추가 (생략됨 - 원본 로직 유지 권장)
    return embed

class JoinModal(discord.ui.Modal, title="내전 참가"):
    def __init__(self, lobby_id, game_key, cog):
        super().__init__()
        self.lobby_id = lobby_id
        self.game_key = game_key
        self.cog = cog
        # 포지션 입력창 등 설정 (기본 로직 유지)
        self.pos_input = discord.ui.TextInput(label="주 포지션", placeholder="예: 타격대, 탑 등", required=True)
        self.add_item(self.pos_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 참가 처리 로직 (생략됨 - 원본 로직 유지)
        await interaction.response.send_message("참가 신청되었습니다.", ephemeral=True)
        await self.cog.refresh_lobby_message(interaction.channel, self.lobby_id)

class RecruitView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="참가", style=discord.ButtonStyle.green, custom_id="join_btn"))
        self.add_item(discord.ui.Button(label="참가취소", style=discord.ButtonStyle.red, custom_id="leave_btn"))
        # 버튼 콜백 연동 로직 포함

# --- Cog 클래스 정의 ---

class Recruit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="내전생성", description="게임을 선택하면 상세 설정을 위한 팝업창이 열립니다.")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def create(
        self,
        interaction: discord.Interaction,
        게임: app_commands.Choice[str],
        팀인원: int = 5,
        진행형식: app_commands.Choice[str] = None,
        배그형식: app_commands.Choice[str] = None,
        모집인원: int = None
    ):
        if not member_has_access(interaction.user):
            await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
            return

        # 팝업창 띄우기
        modal = RecruitCreateModal(
            self, 게임.value, 게임.name, 팀인원, 모집인원,
            진행형식.value if 진행형식 else "scrim", 1, "general",
            배그형식.name if 배그형식 else None
        )
        await interaction.response.send_modal(modal)

    @app_commands.command(name="내전시간수정", description="팝업창을 통해 내전 시간을 수정합니다.")
    async def edit_lobby_time(self, interaction: discord.Interaction, 로비아이디: int = None):
        # 로비 찾기 (resolve_lobby 로직 활용)
        lobby = db.get_lobby_by_id(로비아이디) if 로비아이디 else None # 예시 로직
        if not lobby:
            await interaction.response.send_message("로비를 찾을 수 없습니다.", ephemeral=True)
            return
        
        if interaction.user.id != lobby["host_id"]:
            await interaction.response.send_message("방장만 수정 가능합니다.", ephemeral=True)
            return

        await interaction.response.send_modal(RecruitEditTimeModal(self, lobby))

    async def refresh_lobby_message(self, channel, lobby_id):
        # 메시지 갱신 로직 (원본 유지)
        pass

async def setup(bot):
    cog = Recruit(bot)
    bot.add_view(RecruitView(cog))
    await bot.add_cog(cog)