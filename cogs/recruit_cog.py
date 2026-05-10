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

# --- 도우미 함수 ---

def get_game_display_name(game_val: str) -> str:
    return {
        "valorant": "VALORANT", "lol": "League of Legends",
        "pubg": "PUBG", "overwatch": "Overwatch 2",
    }.get(game_val, game_val)

def get_lobby_need_count(lobby: dict) -> int:
    if lobby["game"] == "pubg":
        return int(lobby.get("total_slots") or 8)
    return lobby["team_size"] * 2

def build_lobby_list_embed(channel: discord.TextChannel, lobbies: list[dict]) -> discord.Embed:
    embed = discord.Embed(title="현재 채널 내전 로비 목록", color=discord.Color.blurple())
    if not lobbies:
        embed.description = "현재 표시할 로비가 없습니다."
        return embed
    lines = [f"• `ID {lb['lobby_id']}` | {lb['game'].upper()} | 상태 `{lb['status']}`" for lb in lobbies]
    embed.description = "\n".join(lines)
    return embed

def build_lobby_embed(lobby: dict, players: list[dict]) -> discord.Embed:
    game_name = get_game_display_name(lobby['game'])
    embed = discord.Embed(title=f"⚔️ {game_name} 내전 모집", color=discord.Color.green())
    embed.add_field(name="로비 ID", value=str(lobby["lobby_id"]), inline=True)
    time_str = lobby["scheduled_at"].strftime("%Y-%m-%d %H:%M") if lobby.get("scheduled_at") else "즉시 시작"
    embed.add_field(name="시작 시간", value=time_str, inline=True)
    
    # 세트 규칙 표시 추가
    series_text = f"{lobby.get('series_target', 1)}선승제" if lobby.get('series_target', 1) > 1 else "단판"
    embed.add_field(name="세트 규칙", value=series_text, inline=True)
    
    embed.add_field(name="인원", value=f"{len(players)} / {get_lobby_need_count(lobby)}", inline=True)
    return embed

# --- 팝업창(Modal) 설정 ---

class RecruitCreateModal(discord.ui.Modal):
    def __init__(self, cog, game_val: str, game_name: str):
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

        # 2. 진행 형식
        format_label = "⚔️ 형식 (내전 / 토너먼트)" if game_val != "pubg" else "🔫 배그 형식 (솔로 / 듀오 / 스쿼드)"
        self.format_input = discord.ui.TextInput(
            label=format_label,
            default="내전" if game_val != "pubg" else "솔로",
            required=True
        )
        self.add_item(self.format_input)

        # 3. 인원 설정
        size_label = "👥 팀별 인원" if game_val != "pubg" else "🎯 총 모집 인원"
        self.size_input = discord.ui.TextInput(
            label=size_label,
            default="5" if game_val != "pubg" else "8",
            required=True
        )
        self.add_item(self.size_input)

        # 4. 선승제 설정 (새로 추가)
        self.series_input = discord.ui.TextInput(
            label="🏆 세트 규칙 (1: 단판, 2: 3판2선...)",
            default="1",
            placeholder="숫자만 입력 (예: 1, 2, 3)",
            required=True,
            max_length=1
        )
        self.add_item(self.series_input)

        # 5. 메모
        self.memo_input = discord.ui.TextInput(
            label="📝 메모 (선택)",
            style=discord.TextStyle.paragraph,
            placeholder="마이크 필수 등",
            required=False,
            max_length=500
        )
        self.add_item(self.memo_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 시간 처리
        time_str = self.time_input.value.strip()
        scheduled_at = datetime.now()
        if time_str:
            try:
                if ":" in time_str and len(time_str) <= 5:
                    parsed_time = datetime.strptime(time_str, "%H:%M").time()
                    scheduled_at = datetime.combine(datetime.now().date(), parsed_time)
                else:
                    scheduled_at = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                await interaction.response.send_message("❌ 시간 형식이 올바르지 않습니다.", ephemeral=True)
                return

        # 형식 및 인원 처리
        db_format = FORMAT_MAPPER.get(self.format_input.value.strip(), "scrim")
        try:
            val_size = int(self.size_input.value.strip())
            series_target = int(self.series_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ 인원과 선승제는 숫자로 입력해주세요.", ephemeral=True)
            return

        final_team_size = val_size if self.game_val != "pubg" else (1 if db_format == "solo" else 2 if db_format == "duo" else 4)
        final_total_slots = val_size if self.game_val == "pubg" else None

        # 로비 생성
        lobby = db.create_lobby(
            interaction.channel_id, interaction.guild_id, interaction.user.id,
            self.game_val, final_team_size, total_slots=final_total_slots,
            scheduled_at=scheduled_at, match_format=db_format,
            series_target=series_target, tournament_stage="general"
        )

        players = db.get_lobby_players_by_id(lobby["lobby_id"])
        embed = build_lobby_embed(lobby, players)
        if self.memo_input.value:
            embed.description = f"**[방장 메모]**\n{self.memo_input.value}"

        await interaction.response.send_message(embed=embed, view=RecruitView(self.cog))
        msg = await interaction.original_response()
        db.set_lobby_message_by_id(lobby["lobby_id"], msg.id)

class RecruitView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        # 필요한 버튼들(참가 등)을 여기에 다시 추가하세요.

class RecruitCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="내전생성", description="팝업창을 통해 내전을 상세 설정합니다.")
    @app_commands.choices(게임=[
        app_commands.Choice(name="VALORANT", value="valorant"),
        app_commands.Choice(name="League of Legends", value="lol"),
        app_commands.Choice(name="Overwatch 2", value="overwatch"),
        app_commands.Choice(name="PUBG", value="pubg")
    ])
    async def create_recruit(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        await interaction.response.send_modal(RecruitCreateModal(self, 게임.value, 게임.name))

async def setup(bot: commands.Bot):
    cog = RecruitCog(bot)
    bot.add_view(RecruitView(cog))
    await bot.add_cog(cog)