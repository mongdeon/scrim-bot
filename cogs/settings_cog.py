import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="설정역할", description="내전 참여 가능 역할을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def role(self, interaction: discord.Interaction, 역할: discord.Role):
        db.update_settings(interaction.guild_id, recruit_role_id=역할.id)
        await interaction.response.send_message("인증 역할 설정 완료", ephemeral=True)

    @app_commands.command(name="설정카테고리", description="내전 음성채널 생성 카테고리를 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def cat(self, interaction: discord.Interaction, 카테고리: discord.CategoryChannel):
        db.update_settings(interaction.guild_id, category_id=카테고리.id)
        await interaction.response.send_message("내전 카테고리 설정 완료", ephemeral=True)

    @app_commands.command(name="설정보기", description="현재 서버 설정을 확인합니다.")
    async def show(self, interaction: discord.Interaction):
        data = db.get_settings(interaction.guild_id)
        if not data:
            await interaction.response.send_message("설정이 없습니다.", ephemeral=True)
            return

        role = interaction.guild.get_role(data["recruit_role_id"]) if data["recruit_role_id"] else None
        category = interaction.guild.get_channel(data["category_id"]) if data["category_id"] else None

        await interaction.response.send_message(
            f"인증 역할: {role.mention if role else '미설정'}\n"
            f"내전 카테고리: {category.mention if category else '미설정'}",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Settings(bot))