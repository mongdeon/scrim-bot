import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()

class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="프리미엄켜기", description="프리미엄 서버 활성화 (관리자)")
    @app_commands.checks.has_permissions(administrator=True)
    async def premium_on(self, interaction: discord.Interaction):
        db.set_premium(interaction.guild.id, True)
        await interaction.response.send_message(":white_check_mark: 이 서버는 이제 프리미엄 서버입니다.", ephemeral=True)

    @app_commands.command(name="프리미엄끄기", description="프리미엄 서버 비활성화 (관리자)")
    @app_commands.checks.has_permissions(administrator=True)
    async def premium_off(self, interaction: discord.Interaction):
        db.set_premium(interaction.guild.id, False)
        await interaction.response.send_message(":x: 프리미엄이 해제되었습니다.", ephemeral=True)

    @app_commands.command(name="프리미엄확인", description="프리미엄 상태 확인")
    async def premium_check(self, interaction: discord.Interaction):
        is_premium = db.is_premium_guild(interaction.guild.id)
        if is_premium:
            await interaction.response.send_message(":star: 이 서버는 프리미엄 서버입니다.")
        else:
            await interaction.response.send_message(":white_circle: 이 서버는 무료 서버입니다.")

async def setup(bot):
    await bot.add_cog(Premium(bot))