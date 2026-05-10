import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from core.db import DB

db = DB()
db.init_recruit_tables()

# --- mapban_cog가 참조하는 필수 도우미 함수들 ---

def get_game_display_name(game_val: str) -> str:
    return {
        "valorant": "VALORANT",
        "lol": "League of Legends",
        "pubg": "PUBG",
        "overwatch": "Overwatch 2",
    }.get(game_val, game_val)

def get_lobby_need_count(lobby: dict) -> int:
    if lobby["game"] == "pubg":
        return int(lobby.get("total_slots") or 8)
    return lobby["team_size"] * 2

def build_lobby_list_embed(channel: discord.TextChannel, lobbies: list[dict]) -> discord.Embed:
    """mapban_cog에서 로비 목록을 보여줄 때 사용하는 필수 함수"""
    embed = discord.Embed(title="현재 채널 내전 로비 목록", color=discord.Color.blurple())
    if not lobbies:
        embed.description = "현재 표시할 로비가 없습니다."
        return embed
    lines = [f"• `ID {lb['lobby_id']}` | {lb['game'].upper()} | 상태 `{lb['status']}`" for lb in lobbies]
    embed.description = "\n".join(lines)
    return embed

def build_lobby_embed(lobby: dict, players: list[dict]) -> discord.Embed:
    embed = discord.Embed(title=f"⚔️ {get_game_display_name(lobby['game'])} 내전 모집", color=discord.Color.green())
    embed.add_field(name="로비 ID", value=str(lobby["lobby_id"]), inline=True)
    time_str = lobby["scheduled_at"].strftime("%Y-%m-%d %H:%M") if lobby.get("scheduled_at") else "즉시 시작"
    embed.add_field(name="시작 시간", value=time_str, inline=True)
    embed.add_field(name="인원", value=f"{len(players)} / {get_lobby_need_count(lobby)}", inline=True)
    return embed

# --- 팝업창(Modal) 및 명령어 설정 ---

class RecruitCreateModal(discord.ui.Modal):
    def __init__(self, cog, game_val: str, game_name: str):
        super().__init__(title=f"{game_name} 내전 설정")
        self.cog = cog
        self.game_val = game_val

    time_input = discord.ui.TextInput(label="시작 시간 (생략 시 '지금')", placeholder="예: 20:00", required=False)
    memo_input = discord.ui.TextInput(label="설명 및 규칙", style=discord.TextStyle.paragraph, required=False)
    team_size = discord.ui.TextInput(label="팀당 인원 (배그는 총 모집인원)", default="5", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        time_str = self.time_input.value.strip()
        scheduled_at = datetime.now()
        if time_str:
            try:
                parsed_time = datetime.strptime(time_str, "%H:%M").time()
                scheduled_at = datetime.combine(datetime.now().date(), parsed_time)
            except: pass

        lobby = db.create_lobby(
            interaction.channel_id, interaction.guild_id, interaction.user.id,
            self.game_val, int(self.team_size.value), scheduled_at=scheduled_at
        )
        players = db.get_lobby_players_by_id(lobby["lobby_id"])
        embed = build_lobby_embed(lobby, players)
        await interaction.response.send_message(embed=embed, view=RecruitView(self.cog))

class RecruitView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)

class RecruitCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="내전생성", description="팝업창을 통해 상세 정보를 입력하여 내전을 생성합니다.")
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