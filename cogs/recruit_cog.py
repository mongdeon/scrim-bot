import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB
from core.matchmaking import auto_balance_players

db = DB()

GAME_OPTIONS = [
    app_commands.Choice(name="VALORANT", value="valorant"),
    app_commands.Choice(name="League of Legends", value="lol"),
    app_commands.Choice(name="PUBG", value="pubg"),
    app_commands.Choice(name="Overwatch 2", value="overwatch"),
]

POSITION_MAP = {
    "valorant": ["타격대", "척후대", "감시자", "전략가", "상관없음"],
    "lol": ["탑", "정글", "미드", "원딜", "서폿", "상관없음"],
    "pubg": ["IGL", "Entry", "Support", "Scout", "상관없음"],
    "overwatch": ["돌격", "딜러", "지원", "상관없음"],
}


def member_has_access(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True

    settings = db.get_settings(member.guild.id)
    if not settings or not settings["role_id"]:
        return False

    return any(role.id == settings["role_id"] for role in member.roles)


def build_lobby_embed(lobby: dict, players: list[dict], team_a=None, team_b=None) -> discord.Embed:
    game_name = {
        "valorant": "VALORANT",
        "lol": "League of Legends",
        "pubg": "PUBG",
        "overwatch": "Overwatch 2"
    }.get(lobby["game"], lobby["game"])

    color = discord.Color.green()
    if lobby["status"] == "balanced":
        color = discord.Color.orange()
    elif lobby["status"] == "started":
        color = discord.Color.blurple()
    elif lobby["status"] == "finished":
        color = discord.Color.red()

    embed = discord.Embed(
        title=f"{game_name} 내전 모집",
        color=color
    )

    embed.add_field(name="상태", value=lobby["status"], inline=True)
    embed.add_field(name="팀 인원", value=str(lobby["team_size"]), inline=True)
    embed.add_field(name="현재 인원", value=str(len(players)), inline=True)

    if players:
        lines = []
        for idx, player in enumerate(players, start=1):
            lines.append(
                f"{idx}. <@{player['user_id']}> | MMR {player['mmr']} | {player['position']}"
            )
        embed.add_field(name="참가자", value="\n".join(lines[:25]), inline=False)
    else:
        embed.add_field(name="참가자", value="아직 없음", inline=False)

    if team_a:
        embed.add_field(name="A팀", value="\n".join(f"<@{uid}>" for uid in team_a), inline=True)
    if team_b:
        embed.add_field(name="B팀", value="\n".join(f"<@{uid}>" for uid in team_b), inline=True)

    if lobby["status"] == "open":
        embed.set_footer(text="참가 버튼을 눌러 포지션과 MMR을 입력하세요.")
    elif lobby["status"] == "balanced":
        embed.set_footer(text="정원이 차서 자동 팀 분배가 완료되었습니다.")
    elif lobby["status"] == "started":
        embed.set_footer(text="내전이 시작되었습니다.")
    else:
        embed.set_footer(text="내전이 종료되었습니다.")

    return embed


class JoinModal(discord.ui.Modal, title="내전 참가"):
    def __init__(self, channel_id: int, game_key: str, cog):
        super().__init__()
        self.channel_id = channel_id
        self.game_key = game_key
        self.cog = cog

        pos_hint = ", ".join(POSITION_MAP.get(game_key, ["상관없음"]))

        self.position = discord.ui.TextInput(
            label="포지션",
            placeholder=pos_hint,
            required=True,
            max_length=20
        )
        self.mmr = discord.ui.TextInput(
            label="MMR",
            placeholder="예: 1000",
            required=True,
            max_length=10
        )

        self.add_item(self.position)
        self.add_item(self.mmr)

    async def on_submit(self, interaction: discord.Interaction):
        lobby = db.get_lobby(self.channel_id)
        if not lobby:
            await interaction.response.send_message("로비가 없습니다.", ephemeral=True)
            return

        if lobby["status"] != "open":
            await interaction.response.send_message("현재 모집 중이 아닙니다.", ephemeral=True)
            return

        position = str(self.position).strip()
        mmr_raw = str(self.mmr).strip()

        if position not in POSITION_MAP.get(self.game_key, []):
            await interaction.response.send_message(
                f"가능한 포지션: {', '.join(POSITION_MAP.get(self.game_key, []))}",
                ephemeral=True
            )
            return

        if not mmr_raw.isdigit():
            await interaction.response.send_message("MMR은 숫자로 입력해주세요.", ephemeral=True)
            return

        mmr = int(mmr_raw)
        if mmr < 1 or mmr > 9999:
            await interaction.response.send_message("MMR은 1~9999 사이로 입력해주세요.", ephemeral=True)
            return

        db.add_lobby_player(
            self.channel_id,
            interaction.user.id,
            interaction.user.display_name,
            mmr,
            position
        )
        db.ensure_player(interaction.guild_id, interaction.user.id, mmr)
        db.set_player_mmr(interaction.guild_id, interaction.user.id, mmr)

        await interaction.response.send_message("참가 완료", ephemeral=True)

        # 메시지 갱신
        await self.cog.refresh_lobby_message(interaction.channel, self.channel_id)

        # 정원 꽉 찼으면 자동 팀 분배
        await self.cog.try_auto_balance(interaction.channel, self.channel_id)


class JoinButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="참가", style=discord.ButtonStyle.green, custom_id="scrim_join_button")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if not member_has_access(interaction.user):
            await interaction.response.send_message("설정된 인증 역할이 있어야 참가할 수 있습니다.", ephemeral=True)
            return

        lobby = db.get_lobby(interaction.channel_id)
        if not lobby:
            await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
            return

        if lobby["status"] != "open":
            await interaction.response.send_message("현재 모집 중이 아닙니다.", ephemeral=True)
            return

        await interaction.response.send_modal(
            JoinModal(interaction.channel_id, lobby["game"], self.cog)
        )


class LeaveButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="참가취소", style=discord.ButtonStyle.red, custom_id="scrim_leave_button")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        lobby = db.get_lobby(interaction.channel_id)
        if not lobby:
            await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
            return

        if lobby["status"] != "open":
            await interaction.response.send_message("팀 분배 이후에는 참가취소를 사용할 수 없습니다.", ephemeral=True)
            return

        if not db.has_lobby_player(interaction.channel_id, interaction.user.id):
            await interaction.response.send_message("참가 중이 아닙니다.", ephemeral=True)
            return

        db.remove_lobby_player(interaction.channel_id, interaction.user.id)
        await interaction.response.send_message("참가 취소 완료", ephemeral=True)
        await self.cog.refresh_lobby_message(interaction.channel, interaction.channel_id)


class StatusButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(label="상태보기", style=discord.ButtonStyle.blurple, custom_id="scrim_status_button")
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        lobby = db.get_lobby(interaction.channel_id)
        if not lobby:
            await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
            return

        players = db.get_lobby_players(interaction.channel_id)
        team_a = db.get_team_members(interaction.channel_id, "A")
        team_b = db.get_team_members(interaction.channel_id, "B")
        embed = build_lobby_embed(lobby, players, team_a, team_b)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RecruitView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.add_item(JoinButton(cog))
        self.add_item(LeaveButton(cog))
        self.add_item(StatusButton(cog))


class Recruit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def refresh_lobby_message(self, channel: discord.TextChannel, channel_id: int):
        lobby = db.get_lobby(channel_id)
        if not lobby:
            return

        players = db.get_lobby_players(channel_id)
        team_a = db.get_team_members(channel_id, "A")
        team_b = db.get_team_members(channel_id, "B")
        embed = build_lobby_embed(lobby, players, team_a, team_b)
        view = RecruitView(self)

        if not lobby["message_id"]:
            return

        try:
            msg = await channel.fetch_message(lobby["message_id"])
            await msg.edit(embed=embed, view=view)
        except discord.NotFound:
            new_msg = await channel.send(embed=embed, view=view)
            db.set_lobby_message(channel_id, new_msg.id)

    async def try_auto_balance(self, channel: discord.TextChannel, channel_id: int):
        lobby = db.get_lobby(channel_id)
        if not lobby or lobby["status"] != "open":
            return

        players = db.get_lobby_players(channel_id)
        need = lobby["team_size"] * 2

        if len(players) < need:
            return

        selected = players[:need]
        (team_a, team_b), mode_text = auto_balance_players(lobby["game"], selected, lobby["team_size"])

        db.clear_teams(channel_id)
        for p in team_a:
            db.add_team_member(channel_id, "A", p["user_id"])
        for p in team_b:
            db.add_team_member(channel_id, "B", p["user_id"])

        db.set_lobby_status(channel_id, "balanced")

        await self.refresh_lobby_message(channel, channel_id)

        a_sum = sum(p["mmr"] for p in team_a)
        b_sum = sum(p["mmr"] for p in team_b)

        await channel.send(
            f"정원이 차서 자동 팀 분배가 완료되었습니다. ({mode_text})\n\n"
            f"**A팀 총합:** {a_sum}\n" +
            "\n".join(f"<@{p['user_id']}> ({p['mmr']}, {p['position']})" for p in team_a) +
            f"\n\n**B팀 총합:** {b_sum}\n" +
            "\n".join(f"<@{p['user_id']}> ({p['mmr']}, {p['position']})" for p in team_b) +
            f"\n\n차이: {abs(a_sum - b_sum)}"
        )

    @app_commands.command(name="내전생성", description="내전 모집 메시지를 생성합니다.")
    @app_commands.describe(게임="게임 선택", 팀인원="한 팀 인원 수")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def create(self, interaction: discord.Interaction, 게임: app_commands.Choice[str], 팀인원: int):
        try:
            if not member_has_access(interaction.user):
                await interaction.response.send_message("설정된 인증 역할이 있어야 내전을 만들 수 있습니다.", ephemeral=True)
                return

            settings = db.get_settings(interaction.guild_id)
            if not settings or not settings["role_id"] or not settings["category_id"]:
                await interaction.response.send_message("먼저 /설정역할 과 /설정카테고리 를 해주세요.", ephemeral=True)
                return

            if 팀인원 < 2 or 팀인원 > 10:
                await interaction.response.send_message("팀 인원은 2~10 사이로 입력해주세요.", ephemeral=True)
                return

            if db.get_lobby(interaction.channel_id):
                await interaction.response.send_message("이미 이 채널에 로비가 있습니다.", ephemeral=True)
                return

            db.create_lobby(
                interaction.channel_id,
                interaction.guild_id,
                interaction.user.id,
                게임.value,
                팀인원
            )

            lobby = db.get_lobby(interaction.channel_id)
            players = db.get_lobby_players(interaction.channel_id)
            embed = build_lobby_embed(lobby, players)
            view = RecruitView(self)

            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_response()
            db.set_lobby_message(interaction.channel_id, msg.id)

        except Exception as e:
            print("내전생성 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="내전상태", description="현재 채널 로비 상태를 확인합니다.")
    async def lobby_status(self, interaction: discord.Interaction):
        lobby = db.get_lobby(interaction.channel_id)
        if not lobby:
            await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
            return

        players = db.get_lobby_players(interaction.channel_id)
        team_a = db.get_team_members(interaction.channel_id, "A")
        team_b = db.get_team_members(interaction.channel_id, "B")
        embed = build_lobby_embed(lobby, players, team_a, team_b)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    cog = Recruit(bot)
    bot.add_view(RecruitView(cog))
    await bot.add_cog(cog)