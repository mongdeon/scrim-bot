import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()
db.init_season_tables()

GAME_OPTIONS = [
    app_commands.Choice(name="VALORANT", value="valorant"),
    app_commands.Choice(name="League of Legends", value="lol"),
    app_commands.Choice(name="PUBG", value="pubg"),
    app_commands.Choice(name="Overwatch 2", value="overwatch"),
]


def season_text(season: dict | None) -> str:
    if not season:
        return "활성 시즌 없음"

    ended_at = str(season["ended_at"]) if season.get("ended_at") else "진행 중"
    return (
        f"시즌명: {season['season_name']}\n"
        f"게임: {season['game']}\n"
        f"상태: {'진행 중' if season['is_active'] else '종료됨'}\n"
        f"시작일: {season['started_at']}\n"
        f"종료일: {ended_at}"
    )


class Season(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _check_premium(self, interaction: discord.Interaction) -> bool:
        return db.is_premium_guild(interaction.guild_id)

    def _check_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    @app_commands.command(name="시즌생성", description="게임별 시즌을 생성합니다. (프리미엄)")
    @app_commands.choices(게임=GAME_OPTIONS)
    @app_commands.describe(시즌명="예: 시즌1, 2026_Spring")
    async def create_season_cmd(
        self,
        interaction: discord.Interaction,
        게임: app_commands.Choice[str],
        시즌명: str
    ):
        if not self._check_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        if not self._check_premium(interaction):
            await interaction.response.send_message("프리미엄 서버만 시즌 기능을 사용할 수 있습니다.", ephemeral=True)
            return

        season_name = 시즌명.strip()
        if not season_name:
            await interaction.response.send_message("시즌명을 입력해주세요.", ephemeral=True)
            return

        try:
            row = db.create_season(interaction.guild_id, 게임.value, season_name)
            await interaction.response.send_message(
                f"✅ 시즌 생성 완료\n{season_text(row)}",
                ephemeral=True
            )
        except Exception as e:
            print("시즌생성 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="시즌종료", description="현재 활성 시즌을 종료합니다. (프리미엄)")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def end_season_cmd(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        if not self._check_admin(interaction):
            await interaction.response.send_message("관리자만 사용할 수 있습니다.", ephemeral=True)
            return

        if not self._check_premium(interaction):
            await interaction.response.send_message("프리미엄 서버만 시즌 기능을 사용할 수 있습니다.", ephemeral=True)
            return

        try:
            row = db.end_active_season(interaction.guild_id, 게임.value)
            if not row:
                await interaction.response.send_message("현재 활성 시즌이 없습니다.", ephemeral=True)
                return

            await interaction.response.send_message(
                f"🛑 시즌 종료 완료\n{season_text(row)}",
                ephemeral=True
            )
        except Exception as e:
            print("시즌종료 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="시즌확인", description="현재 활성 시즌을 확인합니다.")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def check_season_cmd(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        try:
            row = db.get_active_season(interaction.guild_id, 게임.value)
            if not row:
                await interaction.response.send_message("현재 활성 시즌이 없습니다.", ephemeral=True)
                return

            await interaction.response.send_message(
                f"📘 현재 시즌 정보\n{season_text(row)}",
                ephemeral=True
            )
        except Exception as e:
            print("시즌확인 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="시즌목록", description="해당 게임의 시즌 목록을 확인합니다.")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def season_list_cmd(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        try:
            rows = db.get_seasons(interaction.guild_id, 게임.value, limit=10)
            if not rows:
                await interaction.response.send_message("시즌 목록이 없습니다.", ephemeral=True)
                return

            lines = []
            for row in rows:
                status = "진행 중" if row["is_active"] else "종료"
                lines.append(f"#{row['id']} | {row['season_name']} | {status}")

            await interaction.response.send_message(
                "📚 시즌 목록\n" + "\n".join(lines),
                ephemeral=True
            )
        except Exception as e:
            print("시즌목록 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="시즌랭킹", description="현재 활성 시즌 랭킹을 확인합니다.")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def season_ranking_cmd(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        try:
            season = db.get_active_season(interaction.guild_id, 게임.value)
            if not season:
                await interaction.response.send_message("현재 활성 시즌이 없습니다.", ephemeral=True)
                return

            ranking = db.get_season_ranking(interaction.guild_id, 게임.value, season["id"], limit=10)
            if not ranking:
                await interaction.response.send_message("아직 시즌 전적이 없습니다.", ephemeral=True)
                return

            lines = []
            for idx, row in enumerate(ranking, start=1):
                lines.append(
                    f"{idx}. {row['display_name'] or row['user_id']} | "
                    f"MMR {row['mmr']} | {row['win']}승 {row['lose']}패 | {row['winrate']}%"
                )

            await interaction.response.send_message(
                f"🏆 {게임.name} {season['season_name']} 랭킹\n" + "\n".join(lines),
                ephemeral=True
            )
        except Exception as e:
            print("시즌랭킹 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Season(bot))