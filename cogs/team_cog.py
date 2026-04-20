import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB
from cogs.recruit_cog import build_lobby_embed, build_lobby_list_embed
from core.matchmaking import auto_balance_players, calc_elo_delta


db = DB()


def format_team_block(team: list[dict]):
    return "\n".join(
        f"{p['display_name']} ({p['mmr']}, {p['position']})"
        for p in team
    )


async def send_operation_log(
    guild: discord.Guild,
    title: str,
    description: str,
    color: discord.Color = discord.Color.blue(),
):
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


def ensure_matches_table():
    db.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            lobby_id BIGINT,
            channel_id BIGINT NOT NULL,
            game VARCHAR(50) NOT NULL,
            winner_team VARCHAR(1) NOT NULL,
            team_a_avg INTEGER NOT NULL,
            team_b_avg INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("ALTER TABLE matches ADD COLUMN IF NOT EXISTS lobby_id BIGINT")


def add_match(
    guild_id: int,
    lobby_id: int,
    channel_id: int,
    game: str,
    winner_team: str,
    team_a_avg: int,
    team_b_avg: int,
):
    ensure_matches_table()
    db.execute("""
        INSERT INTO matches (guild_id, lobby_id, channel_id, game, winner_team, team_a_avg, team_b_avg)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (guild_id, lobby_id, channel_id, game, winner_team, team_a_avg, team_b_avg))


def apply_match_result(
    guild_id: int,
    game: str,
    winners: list[int],
    losers: list[int],
    winner_delta: int,
    loser_delta: int,
    name_map: dict[int, str],
):
    for uid in winners:
        display_name = name_map.get(uid)
        db.ensure_player(guild_id, uid, 1000, display_name)
        db.ensure_player_game(guild_id, uid, game, 1000, display_name)

        db.execute("""
            UPDATE players
            SET
                mmr = GREATEST(0, mmr + %s),
                win = win + 1,
                display_name = COALESCE(%s, display_name)
            WHERE guild_id = %s AND user_id = %s
        """, (winner_delta, display_name, guild_id, uid))

        db.execute("""
            UPDATE player_game_stats
            SET
                mmr = GREATEST(0, mmr + %s),
                win = win + 1,
                display_name = COALESCE(%s, display_name)
            WHERE guild_id = %s AND user_id = %s AND game = %s
        """, (winner_delta, display_name, guild_id, uid, game))

    for uid in losers:
        display_name = name_map.get(uid)
        db.ensure_player(guild_id, uid, 1000, display_name)
        db.ensure_player_game(guild_id, uid, game, 1000, display_name)

        db.execute("""
            UPDATE players
            SET
                mmr = GREATEST(0, mmr + %s),
                lose = lose + 1,
                display_name = COALESCE(%s, display_name)
            WHERE guild_id = %s AND user_id = %s
        """, (loser_delta, display_name, guild_id, uid))

        db.execute("""
            UPDATE player_game_stats
            SET
                mmr = GREATEST(0, mmr + %s),
                lose = lose + 1,
                display_name = COALESCE(%s, display_name)
            WHERE guild_id = %s AND user_id = %s AND game = %s
        """, (loser_delta, display_name, guild_id, uid, game))


class Team(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_channel_lobbies(self, channel_id: int, guild_id: int, active_only: bool = False):
        return db.get_channel_lobbies(channel_id, guild_id=guild_id, active_only=active_only)

    async def resolve_lobby(
        self,
        interaction: discord.Interaction,
        lobby_id: int | None,
        active_preferred: bool = True,
        send_list_on_ambiguous: bool = True,
    ):
        if lobby_id is not None:
            lobby = db.get_lobby_by_id(lobby_id)
            if not lobby:
                await interaction.response.send_message("해당 로비 ID를 찾을 수 없습니다.", ephemeral=True)
                return None
            if lobby["guild_id"] != interaction.guild_id or lobby["channel_id"] != interaction.channel_id:
                await interaction.response.send_message("해당 로비는 현재 채널의 로비가 아닙니다.", ephemeral=True)
                return None
            return lobby

        lobbies = self.get_channel_lobbies(interaction.channel_id, interaction.guild_id, active_only=active_preferred)
        if not lobbies and active_preferred:
            lobbies = self.get_channel_lobbies(interaction.channel_id, interaction.guild_id, active_only=False)

        if not lobbies:
            await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
            return None

        if len(lobbies) == 1:
            return lobbies[0]

        if send_list_on_ambiguous and isinstance(interaction.channel, discord.TextChannel):
            embed = build_lobby_list_embed(interaction.channel, lobbies)
            await interaction.response.send_message(
                content="같은 채널에 여러 로비가 있습니다. `로비아이디`를 함께 입력해주세요.",
                embed=embed,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "같은 채널에 여러 로비가 있습니다. `로비아이디`를 함께 입력해주세요.",
                ephemeral=True,
            )
        return None

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

        base_name = f"{lobby['game']}-{lobby['lobby_id']}"

        if waiting is None:
            waiting = await guild.create_voice_channel(
                name=f"{base_name}-대기방",
                category=category,
                overwrites=overwrites,
            )
        if team_a_ch is None:
            team_a_ch = await guild.create_voice_channel(
                name=f"{base_name}-A팀",
                category=category,
                overwrites=overwrites,
            )
        if team_b_ch is None:
            team_b_ch = await guild.create_voice_channel(
                name=f"{base_name}-B팀",
                category=category,
                overwrites=overwrites,
            )

        db.set_voice_channels_by_id(lobby["lobby_id"], waiting.id, team_a_ch.id, team_b_ch.id)
        return waiting, team_a_ch, team_b_ch

    async def move_members(self, guild: discord.Guild, user_ids, target_channel):
        for uid in user_ids:
            member = guild.get_member(uid)
            if member and member.voice and member.voice.channel:
                try:
                    await member.move_to(target_channel)
                except Exception:
                    pass

    async def refresh_lobby_message(self, channel: discord.TextChannel, lobby_id: int):
        lobby = db.get_lobby_by_id(lobby_id)
        if not lobby or not lobby.get("message_id"):
            return

        players = db.get_lobby_players_by_id(lobby_id)
        team_a = db.get_team_members_by_id(lobby_id, "A")
        team_b = db.get_team_members_by_id(lobby_id, "B")
        embed = build_lobby_embed(lobby, players, team_a, team_b)

        try:
            msg = await channel.fetch_message(lobby["message_id"])
            await msg.edit(embed=embed)
        except Exception:
            pass

    @app_commands.command(name="밸런스팀", description="MMR 기준으로 자동 팀 분배를 합니다.")
    @app_commands.describe(로비아이디="팀 분배할 로비 ID")
    async def balance_team(self, interaction: discord.Interaction, 로비아이디: int | None = None):
        try:
            lobby = await self.resolve_lobby(interaction, 로비아이디, active_preferred=True)
            if not lobby:
                return

            if lobby["game"] == "pubg":
                await interaction.response.send_message(
                    "배그는 배틀로얄 모집형이라 `/밸런스팀`을 사용하지 않습니다.\n정원이 차면 자동으로 모집 완료 처리됩니다.",
                    ephemeral=True,
                )
                return

            players = db.get_lobby_players_by_id(lobby["lobby_id"])
            need = lobby["team_size"] * 2

            if len(players) < need:
                await interaction.response.send_message(
                    f"인원이 부족합니다. 현재 {len(players)} / 필요 {need}",
                    ephemeral=True,
                )
                return

            selected = players[:need]
            (team_a, team_b), mode_text = auto_balance_players(lobby["game"], selected, lobby["team_size"])

            db.clear_teams_by_id(lobby["lobby_id"])
            for p in team_a:
                db.add_team_member_by_id(lobby["lobby_id"], "A", p["user_id"])
            for p in team_b:
                db.add_team_member_by_id(lobby["lobby_id"], "B", p["user_id"])

            db.set_lobby_status_by_id(lobby["lobby_id"], "balanced")

            a_sum = sum(p["mmr"] for p in team_a)
            b_sum = sum(p["mmr"] for p in team_b)

            waiting, team_a_ch, team_b_ch = await self.ensure_voice_channels(interaction.guild, lobby)
            if waiting and team_a_ch and team_b_ch:
                extra_text = (
                    f"\n\n대기방: {waiting.mention}"
                    f"\nA팀방: {team_a_ch.mention}"
                    f"\nB팀방: {team_b_ch.mention}"
                    f"\n\n아래 모집 메시지의 **내전시작** 버튼을 눌러 팀 채널로 이동하세요."
                )
            else:
                extra_text = (
                    "\n\n음성채널 자동 생성에 실패했습니다."
                    "\n`/설정카테고리` 와 `/설정역할` 설정을 확인해주세요."
                )

            await interaction.response.send_message(
                f"팀 분배 완료 ({mode_text})\n"
                f"로비 ID: **{lobby['lobby_id']}**\n\n"
                f"**A팀 총합:** {a_sum}\n{format_team_block(team_a)}\n\n"
                f"**B팀 총합:** {b_sum}\n{format_team_block(team_b)}\n\n"
                f"차이: {abs(a_sum - b_sum)}"
                f"{extra_text}"
            )
            await self.refresh_lobby_message(interaction.channel, lobby["lobby_id"])
            await send_operation_log(
                interaction.guild,
                "운영 로그 · 팀 분배",
                f"실행자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n"
                f"로비 ID: {lobby['lobby_id']}\n게임: {lobby['game']}\n"
                f"A팀 총합: {a_sum}\nB팀 총합: {b_sum}\n차이: {abs(a_sum - b_sum)}",
                discord.Color.orange(),
            )

        except Exception as e:
            print("밸런스팀 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="결과기록", description="경기 결과를 반영하고 ELO를 계산합니다.")
    @app_commands.describe(승리팀="A 또는 B", 로비아이디="결과를 기록할 로비 ID")
    async def record_result(self, interaction: discord.Interaction, 승리팀: str, 로비아이디: int | None = None):
        try:
            if not db.is_premium_guild(interaction.guild_id):
                await interaction.response.send_message(
                    "⚠️ ELO 기능은 프리미엄 서버 전용입니다.",
                    ephemeral=True,
                )
                return

            lobby = await self.resolve_lobby(interaction, 로비아이디, active_preferred=True)
            if not lobby:
                return

            if lobby["game"] == "pubg":
                await interaction.response.send_message(
                    "배그 배틀로얄 모집형은 현재 `/결과기록`을 지원하지 않습니다.",
                    ephemeral=True,
                )
                return

            winner = 승리팀.upper()
            if winner not in ["A", "B"]:
                await interaction.response.send_message("승리팀은 A 또는 B만 가능합니다.", ephemeral=True)
                return

            team_a_ids = db.get_team_members_by_id(lobby["lobby_id"], "A")
            team_b_ids = db.get_team_members_by_id(lobby["lobby_id"], "B")

            if not team_a_ids or not team_b_ids:
                await interaction.response.send_message("먼저 팀 분배를 완료하세요.", ephemeral=True)
                return

            players = db.get_lobby_players_by_id(lobby["lobby_id"])
            mmr_map = {p["user_id"]: p["mmr"] for p in players}
            name_map = {p["user_id"]: p["display_name"] for p in players}

            avg_a = round(sum(mmr_map[uid] for uid in team_a_ids) / len(team_a_ids))
            avg_b = round(sum(mmr_map[uid] for uid in team_b_ids) / len(team_b_ids))

            delta_a, delta_b = calc_elo_delta(avg_a, avg_b, winner)

            if winner == "A":
                apply_match_result(interaction.guild_id, lobby["game"], team_a_ids, team_b_ids, delta_a, delta_b, name_map)
            else:
                apply_match_result(interaction.guild_id, lobby["game"], team_b_ids, team_a_ids, delta_b, delta_a, name_map)

            add_match(
                interaction.guild_id,
                lobby["lobby_id"],
                interaction.channel_id,
                lobby["game"],
                winner,
                avg_a,
                avg_b,
            )
            db.set_lobby_status_by_id(lobby["lobby_id"], "finished")

            lines = []
            for uid in team_a_ids:
                delta = delta_a
                sign = "+" if delta >= 0 else ""
                lines.append(f"{name_map.get(uid, uid)}: {sign}{delta}")
            for uid in team_b_ids:
                delta = delta_b
                sign = "+" if delta >= 0 else ""
                lines.append(f"{name_map.get(uid, uid)}: {sign}{delta}")

            await interaction.response.send_message(
                f"결과 기록 완료\n"
                f"로비 ID: **{lobby['lobby_id']}**\n"
                f"승리팀: **{winner}팀**\n"
                f"A팀 평균: {avg_a}\n"
                f"B팀 평균: {avg_b}\n\n"
                f"**ELO/MMR 변동**\n" + "\n".join(lines)
            )
            await self.refresh_lobby_message(interaction.channel, lobby["lobby_id"])
            await send_operation_log(
                interaction.guild,
                "운영 로그 · 결과 기록",
                f"실행자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n"
                f"로비 ID: {lobby['lobby_id']}\n게임: {lobby['game']}\n승리팀: {winner}팀\n"
                f"A팀 평균: {avg_a}\nB팀 평균: {avg_b}",
                discord.Color.green(),
            )

        except Exception as e:
            print("결과기록 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="내전종료", description="통화방 정리 후 현재 채널 로비를 종료합니다.")
    @app_commands.describe(로비아이디="종료할 로비 ID")
    async def close_scrim(self, interaction: discord.Interaction, 로비아이디: int | None = None):
        try:
            lobby = await self.resolve_lobby(interaction, 로비아이디, active_preferred=False)
            if not lobby:
                return

            if interaction.user.id != lobby["host_id"] and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("호스트 또는 관리자만 종료할 수 있습니다.", ephemeral=True)
                return

            waiting_ch = interaction.guild.get_channel(lobby["waiting_voice_id"]) if lobby.get("waiting_voice_id") else None
            team_a_ch = interaction.guild.get_channel(lobby["team_a_voice_id"]) if lobby.get("team_a_voice_id") else None
            team_b_ch = interaction.guild.get_channel(lobby["team_b_voice_id"]) if lobby.get("team_b_voice_id") else None

            if waiting_ch and isinstance(waiting_ch, discord.VoiceChannel):
                for voice_ch in [team_a_ch, team_b_ch]:
                    if voice_ch and isinstance(voice_ch, discord.VoiceChannel):
                        for member in list(voice_ch.members):
                            try:
                                await member.move_to(waiting_ch)
                            except Exception:
                                pass

            for voice_ch in [team_a_ch, team_b_ch]:
                if voice_ch and isinstance(voice_ch, discord.VoiceChannel):
                    try:
                        await voice_ch.delete()
                    except Exception:
                        pass

            db.delete_lobby_by_id(lobby["lobby_id"])

            if waiting_ch and isinstance(waiting_ch, discord.VoiceChannel):
                await interaction.response.send_message(
                    f"내전 종료 완료\n"
                    f"로비 ID: **{lobby['lobby_id']}**\n"
                    f"남은 인원은 {waiting_ch.mention} 에 남아 있습니다.\n"
                    f"대기방 인원이 0명이 되면 자동으로 삭제됩니다."
                )
            else:
                await interaction.response.send_message(
                    f"내전 종료 완료\n로비 ID: **{lobby['lobby_id']}**"
                )

            await send_operation_log(
                interaction.guild,
                "운영 로그 · 내전 종료",
                f"실행자: {interaction.user.mention}\n채널: {interaction.channel.mention}\n"
                f"로비 ID: {lobby['lobby_id']}\n게임: {lobby['game']}\n호스트: <@{lobby['host_id']}>",
                discord.Color.red(),
            )

        except Exception as e:
            print("내전종료 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Team(bot))
