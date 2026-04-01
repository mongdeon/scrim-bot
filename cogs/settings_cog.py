import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


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


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="설정역할", description="내전 참여 가능 역할을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def role(self, interaction: discord.Interaction, 역할: discord.Role):
        db.update_settings(interaction.guild_id, recruit_role_id=역할.id)
        await interaction.response.send_message("인증 역할 설정 완료", ephemeral=True)
        await send_operation_log(
            interaction.guild,
            "운영 설정 변경",
            f"관리자: {interaction.user.mention}\n설정 항목: 인증 역할\n값: {역할.mention}",
            discord.Color.green()
        )

    @app_commands.command(name="설정카테고리", description="내전 음성채널 생성 카테고리를 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def cat(self, interaction: discord.Interaction, 카테고리: discord.CategoryChannel):
        db.update_settings(interaction.guild_id, category_id=카테고리.id)
        await interaction.response.send_message("내전 카테고리 설정 완료", ephemeral=True)
        await send_operation_log(
            interaction.guild,
            "운영 설정 변경",
            f"관리자: {interaction.user.mention}\n설정 항목: 내전 카테고리\n값: {카테고리.name}",
            discord.Color.green()
        )

    @app_commands.command(name="설정로그채널", description="운영 로그가 올라갈 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def log_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild_id, log_channel_id=채널.id)
        await interaction.response.send_message(f"운영 로그 채널을 {채널.mention} 로 설정했습니다.", ephemeral=True)

        embed = discord.Embed(
            title="운영 로그 채널 설정 완료",
            description=f"관리자: {interaction.user.mention}\n이 채널이 운영 로그 채널로 설정되었습니다.",
            color=discord.Color.green()
        )
        try:
            await 채널.send(embed=embed)
        except Exception:
            pass

    @app_commands.command(name="설정보기", description="현재 서버 설정을 확인합니다.")
    async def show(self, interaction: discord.Interaction):
        data = db.get_settings(interaction.guild_id)
        if not data:
            await interaction.response.send_message("설정이 없습니다.", ephemeral=True)
            return

        role = interaction.guild.get_role(data["recruit_role_id"]) if data["recruit_role_id"] else None
        category = interaction.guild.get_channel(data["category_id"]) if data["category_id"] else None
        log_channel = interaction.guild.get_channel(data["log_channel_id"]) if data.get("log_channel_id") else None

        await interaction.response.send_message(
            f"인증 역할: {role.mention if role else '미설정'}\n"
            f"내전 카테고리: {category.mention if category else '미설정'}\n"
            f"운영 로그 채널: {log_channel.mention if log_channel else '미설정'}",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Settings(bot))
