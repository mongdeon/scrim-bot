import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB
from cogs.recruit_cog import build_lobby_embed
from core.matchmaking import auto_balance_players, calc_elo_delta

db = DB()


def format_team_block(team: list[dict]):
    return "\n".join(
        f"{p['display_name']} ({p['mmr']}, {p['position']})"
        for p in team
    )


class Team(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            if not db.is_premium_guild(interaction.guild_id):
                await interaction.response.send_message(
                    "⚠️ ELO 기능은 프리미엄 서버 전용입니다.",
                    ephemeral=True
                )
                return

            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
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
                db.apply_match_result(interaction.guild_id, lobby["game"], team_a_ids, team_b_ids, delta_a, delta_b, name_map)
            else:
                db.apply_match_result(interaction.guild_id, lobby["game"], team_b_ids, team_a_ids, delta_b, delta_a, name_map)

            db.add_match(interaction.guild_id, interaction.channel_id, lobby["game"], winner, avg_a, avg_b)
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

            db.delete_lobby(interaction.channel_id)

            if waiting_ch and isinstance(waiting_ch, discord.VoiceChannel):
                await interaction.response.send_message(
                    f"내전 종료 완료\n"
                    f"A팀/B팀 채널을 정리했고, 남은 인원은 {waiting_ch.mention} 으로 이동했습니다.\n"
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