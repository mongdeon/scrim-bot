import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="랭킹", description="MMR 랭킹 TOP 10")
    async def ranking(self, interaction: discord.Interaction):
        rows = db.get_ranking(interaction.guild_id, 10)
        if not rows:
            await interaction.response.send_message("랭킹 데이터가 없습니다.", ephemeral=True)
            return

        lines = []
        for i, row in enumerate(rows, start=1):
            total = row["win"] + row["lose"]
            winrate = round((row["win"] / total) * 100, 1) if total > 0 else 0.0
            lines.append(
                f"{i}. <@{row['user_id']}> | MMR {row['mmr']} | {row['win']}승 {row['lose']}패 | 승률 {winrate}%"
            )

        await interaction.response.send_message("**MMR 랭킹 TOP 10**\n" + "\n".join(lines))

    @app_commands.command(name="내전전적", description="내 전적을 확인합니다.")
    async def my_record(self, interaction: discord.Interaction, 유저: discord.Member | None = None):
        target = 유저 or interaction.user
        row = db.get_player(interaction.guild_id, target.id)

        total = row["win"] + row["lose"]
        winrate = round((row["win"] / total) * 100, 1) if total > 0 else 0.0

        await interaction.response.send_message(
            f"**{target.display_name} 전적**\n"
            f"MMR: {row['mmr']}\n"
            f"승: {row['win']}\n"
            f"패: {row['lose']}\n"
            f"총판수: {total}\n"
            f"승률: {winrate}%"
        )

    @app_commands.command(name="최근전적", description="최근 경기 기록을 확인합니다.")
    async def recent(self, interaction: discord.Interaction):
        rows = db.get_recent_matches(interaction.guild_id, 10)
        if not rows:
            await interaction.response.send_message("최근 경기 기록이 없습니다.", ephemeral=True)
            return

        lines = []
        for row in rows:
            lines.append(
                f"#{row['id']} | {row['game']} | 승리팀 {row['winner_team']} | "
                f"A평균 {row['team_a_avg']} / B평균 {row['team_b_avg']} | {row['created_at']}"
            )

        await interaction.response.send_message("**최근 전적**\n" + "\n".join(lines))


async def setup(bot):
    await bot.add_cog(Ranking(bot))