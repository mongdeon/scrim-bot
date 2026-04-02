import discord
from discord.ext import commands, tasks
from discord import app_commands

from core.db import DB
from datetime import datetime
from core.matchmaking import auto_balance_players

db = DB()
db.init_recruit_tables()

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

OVERWATCH_ROLES = ["돌격", "딜러", "지원"]

def parse_date_time(date_text: str | None, time_text: str | None):
    if not date_text and not time_text:
        return None
    if not date_text or not time_text:
        raise ValueError("날짜와 시간은 함께 입력해야 합니다.")
    return datetime.strptime(f"{date_text.strip()} {time_text.strip()}", "%Y-%m-%d %H:%M")

async def send_operation_log(guild: discord.Guild, title: str, description: str, color: discord.Color = discord.Color.blue()):
    settings = db.get_settings(guild.id)
    if not settings:
        return

    channel_id = settings.get("log_channel_id")
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return

    embed = discord.Embed(title=title, description=description, color=color)
    try:
        await channel.send(embed=embed)
    except Exception:
        pass



def member_has_access(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True

    settings = db.get_settings(member.guild.id)
    if not settings or not settings["recruit_role_id"]:
        return False

    return any(role.id == settings["recruit_role_id"] for role in member.roles)


def is_pubg_lobby(lobby: dict) -> bool:
    return lobby["game"] == "pubg"


def get_pubg_mode_label(team_size: int) -> str:
    if team_size == 1:
        return "솔로"
    if team_size == 2:
        return "듀오"
    if team_size == 4:
        return "스쿼드"
    return f"{team_size}인"


def get_lobby_need_count(lobby: dict) -> int:
    if is_pubg_lobby(lobby):
        if lobby.get("total_slots") is not None:
            return int(lobby["total_slots"])

        if lobby["team_size"] == 1:
            return 8
        if lobby["team_size"] == 2:
            return 8
        if lobby["team_size"] == 4:
            return 16

    return lobby["team_size"] * 2


def get_game_display_name(lobby: dict) -> str:
    if lobby["game"] == "pubg":
        return f"PUBG 배틀로얄 ({get_pubg_mode_label(lobby['team_size'])})"

    return {
        "valorant": "VALORANT",
        "lol": "League of Legends",
        "pubg": "PUBG",
        "overwatch": "Overwatch 2"
    }.get(lobby["game"], lobby["game"])


def build_party_lines(channel_id: int) -> list[str]:
    parties = db.get_lobby_parties(channel_id)
    lines = []

    for idx, party in enumerate(parties, start=1):
        members = party["members"]
        member_names = ", ".join(m["display_name"] for m in members)
        lines.append(
            f"{idx}. 코드 `{party['party_code']}` | {len(members)}/{party['mode_size']}명 | {member_names}"
        )

    return lines


def build_lobby_embed(lobby: dict, players: list[dict], team_a=None, team_b=None) -> discord.Embed:
    game_name = get_game_display_name(lobby)
    need = get_lobby_need_count(lobby)

    color = discord.Color.green()
    if lobby["status"] == "balanced":
        color = discord.Color.orange()
    elif lobby["status"] == "started":
        color = discord.Color.blurple()
    elif lobby["status"] == "finished":
        color = discord.Color.red()

    embed = discord.Embed(title=f"{game_name} 내전 모집", color=color)
    embed.add_field(name="상태", value=lobby["status"], inline=True)

    if is_pubg_lobby(lobby):
        embed.add_field(name="배그 형식", value=get_pubg_mode_label(lobby["team_size"]), inline=True)
        embed.add_field(name="총 모집 인원", value=str(need), inline=True)
        embed.add_field(name="현재 참가 인원", value=f"{len(players)} / {need}", inline=False)
    else:
        embed.add_field(name="팀 인원", value=f"{lobby['team_size']} vs {lobby['team_size']}", inline=True)
        embed.add_field(name="현재 인원", value=f"{len(players)} / {need}", inline=True)

    if players:
        if is_pubg_lobby(lobby) and lobby["team_size"] in [2, 4]:
            grouped = {}
            no_party_rows = []

            for player in players:
                party_id = player.get("party_id")
                if party_id:
                    grouped.setdefault(party_id, []).append(player)
                else:
                    no_party_rows.append(player)

            lines = []
            group_idx = 1

            for _, members in grouped.items():
                member_text = " / ".join(f"{m['display_name']} ({m['mmr']})" for m in members)
                lines.append(f"[파티 {group_idx}] {member_text}")
                group_idx += 1

            for player in no_party_rows:
                pos_text = player['position'] if not player.get('sub_position') else f"{player['position']} / {player['sub_position']}"
                lines.append(f"{player['display_name']} | MMR {player['mmr']} | {pos_text}")

            embed.add_field(name="참가자", value="\n".join(lines[:25]), inline=False)
        else:
            lines = []
            for idx, player in enumerate(players, start=1):
                pos_text = player['position'] if not player.get('sub_position') else f"{player['position']} / {player['sub_position']}"
                lines.append(f"{idx}. {player['display_name']} | MMR {player['mmr']} | {pos_text}")
            embed.add_field(name="참가자", value="\n".join(lines[:25]), inline=False)
    else:
        embed.add_field(name="참가자", value="아직 없음", inline=False)

    if lobby.get("scheduled_at"):
        embed.add_field(name="내전 시간", value=str(lobby["scheduled_at"])[:16], inline=True)
    if lobby.get("recruit_close_at"):
        embed.add_field(name="모집 마감", value=str(lobby["recruit_close_at"])[:16], inline=True)

    if is_pubg_lobby(lobby) and lobby["team_size"] in [2, 4]:
        party_lines = build_party_lines(lobby["channel_id"])
        if party_lines:
            embed.add_field(name="현재 파티", value="\n".join(party_lines[:20]), inline=False)
        else:
            embed.add_field(name="현재 파티", value="아직 없음", inline=False)

    if not is_pubg_lobby(lobby):
        if team_a:
            embed.add_field(name="A팀", value="\n".join(f"<@{uid}>" for uid in team_a), inline=True)
        if team_b:
            embed.add_field(name="B팀", value="\n".join(f"<@{uid}>" for uid in team_b), inline=True)

    if lobby["status"] == "open":
        if is_pubg_lobby(lobby):
            if lobby["team_size"] == 1:
                embed.set_footer(text="배그 솔로는 개인 참가형입니다. 정원이 차면 대기방으로 자동 이동합니다.")
            else:
                embed.set_footer(text="배그 듀오/스쿼드는 먼저 파티를 만든 뒤 참가하세요. 정원이 차면 대기방으로 자동 이동합니다.")
        else:
            embed.set_footer(text="참가 버튼을 눌러 포지션과 MMR을 입력하세요.")
    elif lobby["status"] == "started":
        if is_pubg_lobby(lobby):
            embed.set_footer(text="배그 모집이 완료되어 대기방으로 이동되었습니다.")
        else:
            embed.set_footer(text="정원이 차서 자동 팀 분배 + 자동 음성 이동이 완료되었습니다.")
    else:
        embed.set_footer(text="내전 상태를 확인하세요.")

    return embed


class JoinModal(discord.ui.Modal, title="내전 참가"):
    def __init__(self, channel_id: int, game_key: str, cog):
        super().__init__()
        self.channel_id = channel_id
        self.game_key = game_key
        self.cog = cog

        pos_hint = ", ".join(POSITION_MAP.get(game_key, ["상관없음"]))
        self.main_position = discord.ui.TextInput(label="주 포지션", placeholder=pos_hint, required=True, max_length=20)
        self.sub_position = discord.ui.TextInput(label="부 포지션", placeholder=pos_hint, required=False, max_length=20)
        self.add_item(self.main_position)
        self.add_item(self.sub_position)
        if game_key != "overwatch":
            self.mmr = discord.ui.TextInput(label="MMR", placeholder="예: 1000", required=True, max_length=10)
            self.add_item(self.mmr)

    async def on_submit(self, interaction: discord.Interaction):
        lobby = db.get_lobby(self.channel_id)
        if not lobby:
            await interaction.response.send_message("로비가 없습니다.", ephemeral=True)
            return
        if lobby["status"] != "open":
            await interaction.response.send_message("현재 모집 중이 아닙니다.", ephemeral=True)
            return

        main_position = self.main_position.value.strip()
        sub_position = self.sub_position.value.strip() or None
        valid_positions = POSITION_MAP.get(self.game_key, [])
        if main_position not in valid_positions:
            await interaction.response.send_message(f"가능한 주 포지션: {', '.join(valid_positions)}", ephemeral=True)
            return
        if sub_position and sub_position not in valid_positions:
            await interaction.response.send_message(f"가능한 부 포지션: {', '.join(valid_positions)}", ephemeral=True)
            return
        if sub_position and sub_position == main_position:
            await interaction.response.send_message("주 포지션과 부 포지션은 다르게 입력해주세요.", ephemeral=True)
            return

        if self.game_key == "overwatch":
            mmr = db.get_overwatch_role_mmr(interaction.guild_id, interaction.user.id, main_position)
            if mmr is None:
                await interaction.response.send_message("오버워치는 역할군별 MMR 등록이 필요합니다. `/옵치티어등록 역할군:<주포지션> 티어:<티어>` 를 먼저 사용해주세요.", ephemeral=True)
                return
            ow_role = main_position
        else:
            mmr_raw = self.mmr.value.strip()
            if not mmr_raw.isdigit():
                await interaction.response.send_message("MMR은 숫자로 입력해주세요.", ephemeral=True)
                return
            mmr = int(mmr_raw)
            if mmr < 1 or mmr > 9999:
                await interaction.response.send_message("MMR은 1~9999 사이로 입력해주세요.", ephemeral=True)
                return
            ow_role = None

        party_id = None
        if lobby["game"] == "pubg" and lobby["team_size"] in [2, 4]:
            party = db.get_user_party(self.channel_id, interaction.user.id)
            if not party:
                await interaction.response.send_message("배그 듀오/스쿼드는 먼저 파티를 만들어야 참가할 수 있습니다.\n`/파티생성` 또는 `/파티참가`를 사용하세요.", ephemeral=True)
                return
            members = db.get_party_members(self.channel_id, party["id"])
            if len(members) != lobby["team_size"]:
                await interaction.response.send_message(f"현재 파티 인원이 {len(members)}명입니다. {lobby['team_size']}명 파티를 완성한 뒤 참가하세요.", ephemeral=True)
                return
            party_id = party["id"]

        db.add_lobby_player(self.channel_id, interaction.user.id, interaction.user.display_name, mmr, main_position, sub_position=sub_position, ow_role=ow_role, party_id=party_id)
        db.ensure_player(interaction.guild_id, interaction.user.id, mmr, interaction.user.display_name)
        db.ensure_player_game(interaction.guild_id, interaction.user.id, lobby["game"], mmr, interaction.user.display_name)

        await interaction.response.send_message("참가 완료", ephemeral=True)
        await self.cog.refresh_lobby_message(interaction.channel, self.channel_id)
        await self.cog.try_auto_balance_and_start(interaction.channel, self.channel_id)


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

        await interaction.response.send_modal(JoinModal(interaction.channel_id, lobby["game"], self.cog))


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
            await interaction.response.send_message("모집 완료 이후에는 참가취소를 사용할 수 없습니다.", ephemeral=True)
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
        db.execute("ALTER TABLE lobbies ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP")
        db.execute("ALTER TABLE lobbies ADD COLUMN IF NOT EXISTS recruit_close_at TIMESTAMP")
        db.execute("ALTER TABLE lobbies ADD COLUMN IF NOT EXISTS close_notice_sent BOOLEAN NOT NULL DEFAULT FALSE")
        db.execute("ALTER TABLE lobby_players ADD COLUMN IF NOT EXISTS sub_position VARCHAR(50)")
        db.execute("ALTER TABLE lobby_players ADD COLUMN IF NOT EXISTS ow_role VARCHAR(20)")
        self.recruit_close_loop.start()

    def cog_unload(self):
        self.recruit_close_loop.cancel()

    @tasks.loop(minutes=1)
    async def recruit_close_loop(self):
        for lobby in db.get_due_close_notice_lobbies():
            guild = self.bot.get_guild(lobby["guild_id"])
            channel = guild.get_channel(lobby["channel_id"]) if guild else None
            if channel:
                await channel.send(f"⏰ 인원 모집 마감 10분 전입니다. 마감 시간: **{str(lobby['recruit_close_at'])[:16]}**")
            db.mark_close_notice_sent(lobby["channel_id"])
        for lobby in db.get_due_close_lobbies():
            guild = self.bot.get_guild(lobby["guild_id"])
            channel = guild.get_channel(lobby["channel_id"]) if guild else None
            db.set_lobby_status(lobby["channel_id"], "closed")
            if channel:
                await self.refresh_lobby_message(channel, lobby["channel_id"])
                await channel.send("🔒 인원 모집 시간이 종료되었습니다.")

    @recruit_close_loop.before_loop
    async def before_recruit_close_loop(self):
        await self.bot.wait_until_ready()

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

    async def ensure_voice_channels(self, guild: discord.Guild, lobby: dict):
        settings = db.get_settings(guild.id)
        if not settings or not settings["category_id"] or not settings["recruit_role_id"]:
            return None, None, None

        category = guild.get_channel(settings["category_id"])
        role = guild.get_role(settings["recruit_role_id"])
        me = guild.me or guild.get_member(self.bot.user.id)

        if not category or not role or not me:
            return None, None, None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True, manage_channels=True),
        }

        host_member = guild.get_member(lobby["host_id"])
        if host_member:
            overwrites[host_member] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True)

        waiting = guild.get_channel(lobby["waiting_voice_id"]) if lobby["waiting_voice_id"] else None
        team_a_ch = guild.get_channel(lobby["team_a_voice_id"]) if lobby["team_a_voice_id"] else None
        team_b_ch = guild.get_channel(lobby["team_b_voice_id"]) if lobby["team_b_voice_id"] else None

        if waiting is None:
            waiting = await guild.create_voice_channel(
                name=f"{lobby['game']}-대기방",
                category=category,
                overwrites=overwrites
            )
        if team_a_ch is None:
            team_a_ch = await guild.create_voice_channel(
                name=f"{lobby['game']}-A팀",
                category=category,
                overwrites=overwrites
            )
        if team_b_ch is None:
            team_b_ch = await guild.create_voice_channel(
                name=f"{lobby['game']}-B팀",
                category=category,
                overwrites=overwrites
            )

        db.set_voice_channels(lobby["channel_id"], waiting.id, team_a_ch.id, team_b_ch.id)
        return waiting, team_a_ch, team_b_ch

    async def ensure_pubg_waiting_channel(self, guild: discord.Guild, lobby: dict):
        settings = db.get_settings(guild.id)
        if not settings or not settings["category_id"] or not settings["recruit_role_id"]:
            return None

        category = guild.get_channel(settings["category_id"])
        role = guild.get_role(settings["recruit_role_id"])
        me = guild.me or guild.get_member(self.bot.user.id)

        if not category or not role or not me:
            return None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
            role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            me: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True, manage_channels=True),
        }

        host_member = guild.get_member(lobby["host_id"])
        if host_member:
            overwrites[host_member] = discord.PermissionOverwrite(view_channel=True, connect=True, speak=True, move_members=True)

        waiting = guild.get_channel(lobby["waiting_voice_id"]) if lobby["waiting_voice_id"] else None
        if waiting is None:
            waiting = await guild.create_voice_channel(
                name=f"pubg-{get_pubg_mode_label(lobby['team_size'])}-대기방",
                category=category,
                overwrites=overwrites
            )

        db.set_voice_channels(lobby["channel_id"], waiting.id, 0, 0)
        return waiting

    async def move_members(self, guild: discord.Guild, user_ids, target_channel):
        for uid in user_ids:
            member = guild.get_member(uid)
            if member and member.voice and member.voice.channel:
                try:
                    await member.move_to(target_channel)
                except Exception:
                    pass

    async def try_auto_balance_and_start(self, channel: discord.TextChannel, channel_id: int):
        lobby = db.get_lobby(channel_id)
        if not lobby or lobby["status"] != "open":
            return

        players = db.get_lobby_players(channel_id)
        need = get_lobby_need_count(lobby)

        if len(players) < need:
            return

        if is_pubg_lobby(lobby):
            if lobby["team_size"] in [2, 4]:
                parties = db.get_lobby_parties(channel_id)

                for party in parties:
                    if len(party["members"]) != lobby["team_size"]:
                        return

                    joined_ids = {p["user_id"] for p in players}
                    party_member_ids = {m["user_id"] for m in party["members"]}
                    if not party_member_ids.issubset(joined_ids):
                        return

            waiting = await self.ensure_pubg_waiting_channel(channel.guild, {**lobby, "channel_id": channel_id})

            db.set_lobby_status(channel_id, "started")
            await self.refresh_lobby_message(channel, channel_id)

            player_ids = [p["user_id"] for p in players[:need]]
            if waiting:
                await self.move_members(channel.guild, player_ids, waiting)

            if lobby["team_size"] in [2, 4]:
                party_lines = build_party_lines(channel_id)
                party_text = "\n".join(party_lines) if party_lines else "없음"
                await channel.send(
                    f"배그 배틀로얄 모집 완료\n"
                    f"형식: **{get_pubg_mode_label(lobby['team_size'])}**\n"
                    f"총 인원: **{need}명**\n\n"
                    f"파티 목록:\n{party_text}"
                )
            else:
                await channel.send(
                    f"배그 배틀로얄 모집 완료\n"
                    f"형식: **{get_pubg_mode_label(lobby['team_size'])}**\n"
                    f"총 인원: **{need}명**\n\n"
                    + "\n".join(f"- {p['display_name']} ({p['mmr']}, {p['position']})" for p in players[:need])
                )
            return

        selected = players[:need]
        (team_a, team_b), mode_text = auto_balance_players(lobby["game"], selected, lobby["team_size"])

        db.clear_teams(channel_id)
        for p in team_a:
            db.add_team_member(channel_id, "A", p["user_id"])
        for p in team_b:
            db.add_team_member(channel_id, "B", p["user_id"])

        waiting, team_a_ch, team_b_ch = await self.ensure_voice_channels(channel.guild, {
            **lobby,
            "channel_id": channel_id
        })

        db.set_lobby_status(channel_id, "started")

        team_a_ids = [p["user_id"] for p in team_a]
        team_b_ids = [p["user_id"] for p in team_b]

        if team_a_ch and team_b_ch:
            await self.move_members(channel.guild, team_a_ids, team_a_ch)
            await self.move_members(channel.guild, team_b_ids, team_b_ch)

        await self.refresh_lobby_message(channel, channel_id)

        a_sum = sum(p["mmr"] for p in team_a)
        b_sum = sum(p["mmr"] for p in team_b)

        await channel.send(
            f"정원이 차서 자동 팀 분배 + 자동 음성 이동이 완료되었습니다. ({mode_text})\n\n"
            f"**A팀 총합:** {a_sum}\n"
            + "\n".join(f"{p['display_name']} ({p['mmr']}, {p['position']})" for p in team_a)
            + f"\n\n**B팀 총합:** {b_sum}\n"
            + "\n".join(f"{p['display_name']} ({p['mmr']}, {p['position']})" for p in team_b)
            + f"\n\n차이: {abs(a_sum - b_sum)}"
        )

    @app_commands.command(name="내전생성", description="내전 모집 메시지를 생성합니다.")
    @app_commands.describe(
        게임="게임 선택",
        팀인원="한 팀 인원 수 (배그는 입력하지 않음)",
        날짜="내전 날짜 (YYYY-MM-DD)",
        시간="내전 시간 (HH:MM)",
        모집마감날짜="인원 모집 마감 날짜 (YYYY-MM-DD)",
        모집마감시간="인원 모집 마감 시간 (HH:MM)",
        배그형식="배그일 때 솔로 / 듀오 / 스쿼드",
        모집인원="배그 총 모집 인원"
    )
    @app_commands.choices(게임=GAME_OPTIONS, 배그형식=PUBG_MODE_OPTIONS)
    async def create(
        self,
        interaction: discord.Interaction,
        게임: app_commands.Choice[str],
        팀인원: int | None = None,
        날짜: str | None = None,
        시간: str | None = None,
        모집마감날짜: str | None = None,
        모집마감시간: str | None = None,
        배그형식: app_commands.Choice[str] | None = None,
        모집인원: int | None = None
    ):
        try:
            if not member_has_access(interaction.user):
                await interaction.response.send_message("설정된 인증 역할이 있어야 내전을 만들 수 있습니다.", ephemeral=True)
                return

            settings = db.get_settings(interaction.guild_id)
            if not settings or not settings["recruit_role_id"] or not settings["category_id"]:
                await interaction.response.send_message("먼저 /설정역할 과 /설정카테고리 를 해주세요.", ephemeral=True)
                return

            if db.get_lobby(interaction.channel_id):
                await interaction.response.send_message("이미 이 채널에 로비가 있습니다.", ephemeral=True)
                return
            if not db.has_premium_plan(interaction.guild_id, "supporter") and db.count_active_guild_lobbies(interaction.guild_id) >= 2:
                await interaction.response.send_message("무료 서버는 동시에 최대 2개의 내전만 생성할 수 있습니다. 2개 이상은 서포터 이상 패키지에서 사용 가능합니다.", ephemeral=True)
                return

            scheduled_at = parse_date_time(날짜, 시간)
            recruit_close_at = parse_date_time(모집마감날짜, 모집마감시간)
            if recruit_close_at and scheduled_at and recruit_close_at >= scheduled_at:
                await interaction.response.send_message("모집 마감 시간은 내전 시간보다 이전이어야 합니다.", ephemeral=True)
                return

            final_team_size: int | None = 팀인원
            final_total_slots: int | None = None

            if 게임.value == "pubg":
                if 배그형식 is None:
                    await interaction.response.send_message(
                        "배그는 `배그형식`을 선택해야 합니다. (솔로 / 듀오 / 스쿼드)",
                        ephemeral=True
                    )
                    return

                if 모집인원 is None:
                    await interaction.response.send_message(
                        "배그는 `모집인원`을 입력해야 합니다.",
                        ephemeral=True
                    )
                    return

                if 배그형식.value == "solo":
                    final_team_size = 1
                    if 모집인원 < 2 or 모집인원 > 100:
                        await interaction.response.send_message("배그 솔로 모집인원은 2 ~ 100 사이만 가능합니다.", ephemeral=True)
                        return

                elif 배그형식.value == "duo":
                    final_team_size = 2
                    if 모집인원 < 4 or 모집인원 > 100:
                        await interaction.response.send_message("배그 듀오 모집인원은 4 ~ 100 사이만 가능합니다.", ephemeral=True)
                        return
                    if 모집인원 % 2 != 0:
                        await interaction.response.send_message("배그 듀오 모집인원은 2의 배수만 가능합니다.", ephemeral=True)
                        return

                elif 배그형식.value == "squad":
                    final_team_size = 4
                    if 모집인원 < 8 or 모집인원 > 100:
                        await interaction.response.send_message("배그 스쿼드 모집인원은 8 ~ 100 사이만 가능합니다.", ephemeral=True)
                        return
                    if 모집인원 % 4 != 0:
                        await interaction.response.send_message("배그 스쿼드 모집인원은 4의 배수만 가능합니다.", ephemeral=True)
                        return

                final_total_slots = 모집인원

            else:
                if final_team_size is None:
                    await interaction.response.send_message("팀 인원을 입력해주세요.", ephemeral=True)
                    return

                if final_team_size < 2 or final_team_size > 10:
                    await interaction.response.send_message("팀 인원은 2~10 사이로 입력해주세요.", ephemeral=True)
                    return

            db.create_lobby(
                interaction.channel_id,
                interaction.guild_id,
                interaction.user.id,
                게임.value,
                final_team_size,
                total_slots=final_total_slots,
                scheduled_at=scheduled_at,
                recruit_close_at=recruit_close_at
            )

            lobby = db.get_lobby(interaction.channel_id)
            players = db.get_lobby_players(interaction.channel_id)
            embed = build_lobby_embed(lobby, players)
            view = RecruitView(self)

            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_response()
            db.set_lobby_message(interaction.channel_id, msg.id)

            if 게임.value == "pubg":
                log_desc = (
                    f"생성자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n"
                    f"게임: PUBG\n형식: {배그형식.name if 배그형식 else '-'}\n총 모집 인원: {final_total_slots}"
                )
            else:
                log_desc = (
                    f"생성자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n"
                    f"게임: {게임.name}\n팀 인원: {final_team_size} vs {final_team_size}"
                )

            await send_operation_log(
                interaction.guild,
                "운영 로그 · 내전 생성",
                log_desc,
                discord.Color.blue()
            )

        except Exception as e:
            print("내전생성 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


    @app_commands.command(name="내전시간수정", description="현재 내전의 날짜/시간과 모집 마감 시간을 수정합니다.")
    @app_commands.describe(날짜="내전 날짜 (YYYY-MM-DD)", 시간="내전 시간 (HH:MM)", 모집마감날짜="모집 마감 날짜 (YYYY-MM-DD)", 모집마감시간="모집 마감 시간 (HH:MM)")
    async def edit_lobby_time(self, interaction: discord.Interaction, 날짜: str | None = None, 시간: str | None = None, 모집마감날짜: str | None = None, 모집마감시간: str | None = None):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return
            scheduled_at = parse_date_time(날짜, 시간)
            recruit_close_at = parse_date_time(모집마감날짜, 모집마감시간)
            if recruit_close_at and scheduled_at and recruit_close_at >= scheduled_at:
                await interaction.response.send_message("모집 마감 시간은 내전 시간보다 이전이어야 합니다.", ephemeral=True)
                return
            db.update_lobby_times(interaction.channel_id, scheduled_at, recruit_close_at)
            await self.refresh_lobby_message(interaction.channel, interaction.channel_id)
            await interaction.response.send_message("내전 시간/모집 마감 시간이 수정되었습니다.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="파티생성", description="배그 듀오/스쿼드 파티를 생성합니다.")
    async def create_party(self, interaction: discord.Interaction):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
                return

            if lobby["game"] != "pubg" or lobby["team_size"] not in [2, 4]:
                await interaction.response.send_message("파티 시스템은 배그 듀오 / 스쿼드에서만 사용합니다.", ephemeral=True)
                return

            party = db.create_lobby_party(
                interaction.channel_id,
                interaction.user.id,
                interaction.user.display_name,
                lobby["team_size"]
            )

            await interaction.response.send_message(
                f"파티 생성 완료\n"
                f"파티 코드: `{party['party_code']}`\n"
                f"정원: {party['mode_size']}명\n"
                f"다른 멤버는 `/파티참가 파티코드:{party['party_code']}` 로 들어오면 됩니다.",
                ephemeral=True
            )

            await self.refresh_lobby_message(interaction.channel, interaction.channel_id)
            await send_operation_log(
                interaction.guild,
                "운영 로그 · 파티 생성",
                f"사용자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n파티 코드: `{party['party_code']}`\n정원: {party['mode_size']}명",
                discord.Color.teal()
            )

        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="파티참가", description="배그 듀오/스쿼드 파티 코드로 파티에 참가합니다.")
    @app_commands.describe(파티코드="파티 코드 입력")
    async def join_party(self, interaction: discord.Interaction, 파티코드: str):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
                return

            if lobby["game"] != "pubg" or lobby["team_size"] not in [2, 4]:
                await interaction.response.send_message("파티 시스템은 배그 듀오 / 스쿼드에서만 사용합니다.", ephemeral=True)
                return

            party = db.join_lobby_party(
                interaction.channel_id,
                파티코드.strip().upper(),
                interaction.user.id,
                interaction.user.display_name
            )

            members = db.get_party_members(interaction.channel_id, party["id"])

            await interaction.response.send_message(
                f"파티 참가 완료\n"
                f"파티 코드: `{party['party_code']}`\n"
                f"현재 인원: {len(members)} / {party['mode_size']}",
                ephemeral=True
            )

            await self.refresh_lobby_message(interaction.channel, interaction.channel_id)
            await send_operation_log(
                interaction.guild,
                "운영 로그 · 파티 참가",
                f"사용자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n파티 코드: `{party['party_code']}`\n현재 인원: {len(members)} / {party['mode_size']}",
                discord.Color.teal()
            )

        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="파티나가기", description="현재 배그 파티에서 나갑니다.")
    async def leave_party(self, interaction: discord.Interaction):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
                return

            result = db.leave_lobby_party(interaction.channel_id, interaction.user.id)

            if result["action"] == "none":
                await interaction.response.send_message("현재 속한 파티가 없습니다.", ephemeral=True)
                return

            if result["action"] == "disbanded":
                await interaction.response.send_message(
                    f"파티장이라 파티 `{result['party_code']}` 가 해체되었습니다.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"파티 `{result['party_code']}` 에서 나갔습니다.",
                    ephemeral=True
                )

            await self.refresh_lobby_message(interaction.channel, interaction.channel_id)
            await send_operation_log(
                interaction.guild,
                "운영 로그 · 파티 이탈",
                f"사용자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n결과: {result['action']}\n파티 코드: `{result.get('party_code', '-')}`",
                discord.Color.teal()
            )

        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="파티상태", description="현재 채널의 배그 파티 상태를 확인합니다.")
    async def party_status(self, interaction: discord.Interaction):
        lobby = db.get_lobby(interaction.channel_id)
        if not lobby:
            await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
            return

        if lobby["game"] != "pubg" or lobby["team_size"] not in [2, 4]:
            await interaction.response.send_message("파티 시스템은 배그 듀오 / 스쿼드에서만 사용합니다.", ephemeral=True)
            return

        lines = build_party_lines(interaction.channel_id)
        if not lines:
            await interaction.response.send_message("현재 파티가 없습니다.", ephemeral=True)
            return

        await interaction.response.send_message("현재 파티 목록\n" + "\n".join(lines), ephemeral=True)

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