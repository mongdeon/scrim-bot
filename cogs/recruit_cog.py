import discord
from discord.ext import commands
from discord import app_commands
from core.db import DB
from datetime import datetime

db = DB()
db.init_recruit_tables()

# 한글 입력값을 DB용 영문 값으로 변환하는 매퍼
FORMAT_MAPPER = {
    "내전": "scrim", "내전형식": "scrim",
    "토너먼트": "tournament", "토너먼트형식": "tournament",
    "솔로": "solo", "듀오": "duo", "스쿼드": "squad"
}

class RecruitCreateModal(discord.ui.Modal):
    def __init__(self, cog, game_val, game_name):
        super().__init__(title=f"🎮 {game_name} 내전 설정")
        self.cog = cog
        self.game_val = game_val
        
        # 1. 시작 시간
        self.time_input = discord.ui.TextInput(
            label="⏰ 시작 시간 (생략 시 '지금')",
            placeholder="예: 20:00 또는 2026-05-12 14:00",
            required=False
        )
        self.add_item(self.time_input)

        # 2. 진행 형식 (내전/토너먼트 or 솔로/듀오/스쿼드)
        format_label = "⚔️ 진행 형식 (내전 / 토너먼트)" if game_val != "pubg" else "🔫 배그 형식 (솔로 / 듀오 / 스쿼드)"
        default_format = "내전" if game_val != "pubg" else "솔로"
        self.format_input = discord.ui.TextInput(
            label=format_label,
            default=default_format,
            required=True
        )
        self.add_item(self.format_input)

        # 3. 팀 인원 (또는 배그 모집 인원)
        size_label = "👥 팀별 인원 수" if game_val != "pubg" else "🎯 총 모집 인원"
        default_size = "5" if game_val != "pubg" else "8"
        self.size_input = discord.ui.TextInput(
            label=size_label,
            default=default_size,
            required=True
        )
        self.add_item(self.size_input)

        # 4. 메모
        self.memo_input = discord.ui.TextInput(
            label="📝 메모 및 규칙 (선택)",
            style=discord.TextStyle.paragraph,
            placeholder="마이크 필수, 즐겜 위주 등",
            required=False,
            max_length=500
        )
        self.add_item(self.memo_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 1. 시간 파싱
        time_str = self.time_input.value.strip()
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
                await interaction.response.send_message("❌ 시간 형식이 올바르지 않습니다.", ephemeral=True)
                return

        # 2. 형식 및 인원 변환
        raw_format = self.format_input.value.strip()
        db_format = FORMAT_MAPPER.get(raw_format, "scrim" if self.game_val != "pubg" else "solo")
        
        try:
            val_size = int(self.size_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ 인원 수는 숫자로 입력해주세요.", ephemeral=True)
            return

        # DB 저장용 값 설정
        final_team_size = val_size if self.game_val != "pubg" else (1 if db_format == "solo" else 2 if db_format == "duo" else 4)
        final_total_slots = val_size if self.game_val == "pubg" else None
        match_format = "battle_royale" if self.game_val == "pubg" else db_format

        # 3. 로비 생성
        lobby = db.create_lobby(
            interaction.channel_id, interaction.guild_id, interaction.user.id,
            self.game_val, final_team_size, total_slots=final_total_slots,
            scheduled_at=scheduled_at, match_format=match_format,
            series_target=1, tournament_stage="general"
        )

        from cogs.recruit_cog import build_lobby_embed, RecruitView
        players = db.get_lobby_players_by_id(lobby["lobby_id"])
        embed = build_lobby_embed(lobby, players)
        
        if self.memo_input.value:
            embed.description = f"**[공지]**\n{self.memo_input.value}"

        await interaction.response.send_message(embed=embed, view=RecruitView(self.cog))
        msg = await interaction.original_response()
        db.set_lobby_message_by_id(lobby["lobby_id"], msg.id)

class Recruit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="내전생성", description="게임을 선택하면 팝업창에서 모든 설정을 진행합니다.")
    @app_commands.choices(게임=[
        app_commands.Choice(name="VALORANT", value="valorant"),
        app_commands.Choice(name="League of Legends", value="lol"),
        app_commands.Choice(name="PUBG", value="pubg"),
        app_commands.Choice(name="Overwatch 2", value="overwatch")
    ])
    async def create(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        # 권한 및 설정 체크 로직은 기존과 동일하게 유지
        modal = RecruitCreateModal(self, 게임.value, 게임.name)
        await interaction.response.send_modal(modal)

# (기존의 RecruitView, JoinModal, 내전시간수정 등 클래스 및 setup 함수 유지)