import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB
from core.config import OWNER_ID

db = DB()


def is_owner(user_id: int) -> bool:
    return OWNER_ID != 0 and user_id == OWNER_ID


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="프리미엄켜기", description="프리미엄 서버 활성화 (오너 전용)")
    async def premium_on(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "⛔ 이 명령어는 봇 오너만 사용할 수 있습니다.",
                ephemeral=True
            )
            return

        db.set_premium(interaction.guild.id, True)
        await interaction.response.send_message(
            f"✅ 이 서버는 이제 프리미엄 서버입니다.\n서버 ID: `{interaction.guild.id}`",
            ephemeral=True
        )

    @app_commands.command(name="프리미엄끄기", description="프리미엄 서버 비활성화 (오너 전용)")
    async def premium_off(self, interaction: discord.Interaction):
        if not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "⛔ 이 명령어는 봇 오너만 사용할 수 있습니다.",
                ephemeral=True
            )
            return

        db.set_premium(interaction.guild.id, False)
        await interaction.response.send_message(
            f"❌ 프리미엄이 해제되었습니다.\n서버 ID: `{interaction.guild.id}`",
            ephemeral=True
        )

    @app_commands.command(name="프리미엄확인", description="프리미엄 상태 확인")
    async def premium_check(self, interaction: discord.Interaction):
        is_premium = db.is_premium_guild(interaction.guild.id)
        if is_premium:
            await interaction.response.send_message("⭐ 이 서버는 프리미엄 서버입니다.")
        else:
            await interaction.response.send_message("⚪ 이 서버는 무료 서버입니다.")


async def setup(bot):
    await bot.add_cog(Premium(bot))