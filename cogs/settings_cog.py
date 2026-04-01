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

    @app_commands.command(name="설정팀결과채널", description="예약된 내전 팀 분배 결과를 보낼 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def result_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild_id, result_channel_id=채널.id)
        await interaction.response.send_message(f"팀 결과 채널 설정 완료: {채널.mention}", ephemeral=True)

    @app_commands.command(name="설정공지채널", description="예약 알림/자동 생성 공지 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def announcement_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild_id, announcement_channel_id=채널.id)
        await interaction.response.send_message(f"공지 채널 설정 완료: {채널.mention}", ephemeral=True)

    @app_commands.command(name="설정로그채널", description="클랜 운영 로그 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def log_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild_id, log_channel_id=채널.id)
        await interaction.response.send_message(f"로그 채널 설정 완료: {채널.mention}", ephemeral=True)

    @app_commands.command(name="클랜시작템플릿", description="클랜 패키지 시작 공지 템플릿을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clan_start_template(self, interaction: discord.Interaction, 내용: str):
        db.update_settings(interaction.guild_id, custom_start_template=내용)
        await interaction.response.send_message("클랜 시작 공지 템플릿 저장 완료", ephemeral=True)

    @app_commands.command(name="클랜알림템플릿", description="클랜 패키지 알림 템플릿을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clan_reminder_template(self, interaction: discord.Interaction, 내용: str):
        db.update_settings(interaction.guild_id, custom_reminder_template=내용)
        await interaction.response.send_message("클랜 알림 템플릿 저장 완료", ephemeral=True)

    @app_commands.command(name="클랜결과템플릿", description="클랜 패키지 결과 템플릿을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clan_result_template(self, interaction: discord.Interaction, 내용: str):
        db.update_settings(interaction.guild_id, custom_result_template=내용)
        await interaction.response.send_message("클랜 결과 템플릿 저장 완료", ephemeral=True)

    @app_commands.command(name="설정보기", description="현재 서버 설정을 확인합니다.")
    async def show(self, interaction: discord.Interaction):
        data = db.get_settings(interaction.guild_id)
        if not data:
            await interaction.response.send_message("설정이 없습니다.", ephemeral=True)
            return

        role = interaction.guild.get_role(data["recruit_role_id"]) if data["recruit_role_id"] else None
        category = interaction.guild.get_channel(data["category_id"]) if data["category_id"] else None
        result_channel = interaction.guild.get_channel(data["result_channel_id"]) if data["result_channel_id"] else None

        await interaction.response.send_message(
            f"인증 역할: {role.mention if role else '미설정'}\n"
            f"내전 카테고리: {category.mention if category else '미설정'}\n"
            f"팀 결과 채널: {result_channel.mention if result_channel else '미설정'}",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Settings(bot))
