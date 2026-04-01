import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

PLAN_LABELS = {"free": "무료", "supporter": "서포터", "pro": "프로", "clan": "클랜"}
from cogs.recruit_cog import build_lobby_embed
from core.matchmaking import auto_balance_players, calc_elo_delta

db = DB()


def format_team_block(team: list[dict]):
    return "\n".join(
        f"{p['display_name']} ({p['mmr']}, {p['position']})"
        for p in team
    )


def ensure_matches_table():
    db.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id BIGSERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            channel_id BIGINT NOT NULL,
            game VARCHAR(50) NOT NULL,
            winner_team VARCHAR(1) NOT NULL,
            team_a_avg INTEGER NOT NULL,
            team_b_avg INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


def add_match(guild_id: int, channel_id: int, game: str, winner_team: str, team_a_avg: int, team_b_avg: int):
    ensure_matches_table()
    db.execute("""
        INSERT INTO matches (guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg))


def apply_match_result(guild_id: int, game: str, winners: list[int], losers: list[int], winner_delta: int, loser_delta: int, name_map: dict[int, str]):
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

    def _current_plan_label(self, guild_id: int) -> str:
        info = db.get_premium_info(guild_id)
        return info.get("plan_name") or PLAN_LABELS.get(info.get("plan_key", "free"), "무료")

    async def _require_plan(self, interaction: discord.Interaction, required_plan_key: str, feature_name: str) -> bool:
        if db.has_premium_plan(interaction.guild_id, required_plan_key):
            return True

        required_name = PLAN_LABELS.get(required_plan_key, required_plan_key)
        current_name = self._current_plan_label(interaction.guild_id)
        await interaction.response.send_message(
            f"⚠️ {feature_name} 기능은 **{required_name} 패키지 이상**에서 사용할 수 있습니다.\n"
            f"현재 서버 패키지: **{current_name}**",
            ephemeral=True
        )
        return False

    async def refresh_message(self, channel: discord.TextChannel, channel_id: int):
        lobby = db.get_lobby(channel_id)
        if not lobby or not lobby["message_id"]:
            return

        players = db.get_lobby_players(channel_id)
        team_a = db.get_team_members(channel_id, "A")
        team_b = db.get_team_members(channel_id, "B")
        embed = build_lobby_embed(lobby, players, team_a, team_b)

        try:
            msg = await channel.fetch_message(lobby["message_id"])
            await msg.edit(embed=embed)
        except Exception:
            pass

    @app_commands.command(name="밸런스팀", description="MMR 기준으로 자동 팀 분배를 합니다.")
    async def balance_team(self, interaction: discord.Interaction):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if lobby["game"] == "pubg":
                await interaction.response.send_message(
                    "배그는 배틀로얄 모집형이라 `/밸런스팀`을 사용하지 않습니다.\n정원이 차면 자동으로 모집 완료 처리됩니다.",
                    ephemeral=True
                )
                return

            players = db.get_lobby_players(interaction.channel_id)
            need = lobby["team_size"] * 2

            if len(players) < need:
                await interaction.response.send_message(
                    f"인원이 부족합니다. 현재 {len(players)} / 필요 {need}",
                    ephemeral=True
                )
                return

            selected = players[:need]
            (team_a, team_b), mode_text = auto_balance_players(lobby["game"], selected, lobby["team_size"])

            db.clear_teams(interaction.channel_id)
            for p in team_a:
                db.add_team_member(interaction.channel_id, "A", p["user_id"])
            for p in team_b:
                db.add_team_member(interaction.channel_id, "B", p["user_id"])

            db.set_lobby_status(interaction.channel_id, "balanced")

            a_sum = sum(p["mmr"] for p in team_a)
            b_sum = sum(p["mmr"] for p in team_b)

            await interaction.response.send_message(
                f"팀 분배 완료 ({mode_text})\n\n"
                f"**A팀 총합:** {a_sum}\n{format_team_block(team_a)}\n\n"
                f"**B팀 총합:** {b_sum}\n{format_team_block(team_b)}\n\n"
                f"차이: {abs(a_sum - b_sum)}"
            )
            await self.refresh_message(interaction.channel, interaction.channel_id)

        except Exception as e:
            print("밸런스팀 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="결과기록", description="경기 결과를 반영하고 ELO를 계산합니다.")
    @app_commands.describe(승리팀="A 또는 B")
    async def record_result(self, interaction: discord.Interaction, 승리팀: str):
        try:
            if not await self._require_plan(interaction, "pro", "결과기록 / ELO 반영"):
                return

            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if lobby["game"] == "pubg":
                await interaction.response.send_message(
                    "배그 배틀로얄 모집형은 현재 `/결과기록`을 지원하지 않습니다.",
                    ephemeral=True
                )
                return

            winner = 승리팀.upper()
            if winner not in ["A", "B"]:
                await interaction.response.send_message("승리팀은 A 또는 B만 가능합니다.", ephemeral=True)
                return

            team_a_ids = db.get_team_members(interaction.channel_id, "A")
            team_b_ids = db.get_team_members(interaction.channel_id, "B")

            if not team_a_ids or not team_b_ids:
                await interaction.response.send_message("먼저 팀 분배를 완료하세요.", ephemeral=True)
                return

            players = db.get_lobby_players(interaction.channel_id)
            mmr_map = {p["user_id"]: p["mmr"] for p in players}
            name_map = {p["user_id"]: p["display_name"] for p in players}

            avg_a = round(sum(mmr_map[uid] for uid in team_a_ids) / len(team_a_ids))
            avg_b = round(sum(mmr_map[uid] for uid in team_b_ids) / len(team_b_ids))

            delta_a, delta_b = calc_elo_delta(avg_a, avg_b, winner)

            if winner == "A":
                apply_match_result(interaction.guild_id, lobby["game"], team_a_ids, team_b_ids, delta_a, delta_b, name_map)
            else:
                apply_match_result(interaction.guild_id, lobby["game"], team_b_ids, team_a_ids, delta_b, delta_a, name_map)

            add_match(interaction.guild_id, interaction.channel_id, lobby["game"], winner, avg_a, avg_b)
            db.set_lobby_status(interaction.channel_id, "finished")

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
                f"승리팀: **{winner}팀**\n"
                f"A팀 평균: {avg_a}\n"
                f"B팀 평균: {avg_b}\n\n"
                f"**ELO/MMR 변동**\n" + "\n".join(lines)
            )
            await self.refresh_message(interaction.channel, interaction.channel_id)

        except Exception as e:
            print("결과기록 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="내전종료", description="통화방 정리 후 현재 채널 로비를 종료합니다.")
    async def close_scrim(self, interaction: discord.Interaction):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if interaction.user.id != lobby["host_id"] and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("호스트 또는 관리자만 종료할 수 있습니다.", ephemeral=True)
                return

            waiting_ch = interaction.guild.get_channel(lobby["waiting_voice_id"]) if lobby["waiting_voice_id"] else None
            team_a_ch = interaction.guild.get_channel(lobby["team_a_voice_id"]) if lobby["team_a_voice_id"] else None
            team_b_ch = interaction.guild.get_channel(lobby["team_b_voice_id"]) if lobby["team_b_voice_id"] else None

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

            db.execute("DELETE FROM lobby_players WHERE channel_id = %s", (interaction.channel_id,))
            db.execute("DELETE FROM lobby_teams WHERE channel_id = %s", (interaction.channel_id,))
            db.execute("DELETE FROM lobby_party_members WHERE channel_id = %s", (interaction.channel_id,))
            db.execute("DELETE FROM lobby_parties WHERE channel_id = %s", (interaction.channel_id,))
            db.execute("DELETE FROM lobbies WHERE channel_id = %s", (interaction.channel_id,))

            if waiting_ch and isinstance(waiting_ch, discord.VoiceChannel):
                await interaction.response.send_message(
                    f"내전 종료 완료\n"
                    f"남은 인원은 {waiting_ch.mention} 에 남아 있습니다.\n"
                    f"대기방 인원이 0명이 되면 자동으로 삭제됩니다."
                )
            else:
                await interaction.response.send_message("내전 종료 완료")

        except Exception as e:
            print("내전종료 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Team(bot))