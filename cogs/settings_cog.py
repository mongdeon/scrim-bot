import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_clan_guild(self, guild_id: int) -> bool:
        return db.has_premium_plan(guild_id, "clan")

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

    @app_commands.command(name="설정로그채널", description="운영 로그가 올라갈 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild_id, log_channel_id=채널.id)
        await interaction.response.send_message(f"운영 로그 채널을 {채널.mention} 로 설정했습니다.", ephemeral=True)


    @app_commands.command(name="설정공지채널", description="클랜 공지/결과 안내가 올라갈 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_announcement_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild_id, announcement_channel_id=채널.id, result_channel_id=채널.id)
        await interaction.response.send_message(f"공지 채널과 결과 채널을 {채널.mention} 로 설정했습니다.", ephemeral=True)

    @app_commands.command(name="설정브랜드이름", description="클랜 패키지 서버의 웹사이트 브랜드 이름을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_brand_name(self, interaction: discord.Interaction, 이름: str):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, brand_name=이름[:100])
        await interaction.response.send_message(f"브랜드 이름을 `{brand['brand_name']}` 로 설정했습니다.", ephemeral=True)

    @app_commands.command(name="설정브랜드색상", description="클랜 패키지 서버의 웹사이트 대표 색상을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_brand_color(self, interaction: discord.Interaction, 색상코드: str):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, brand_color=색상코드)
        await interaction.response.send_message(f"브랜드 색상을 `{brand['brand_color']}` 로 설정했습니다.", ephemeral=True)

    @app_commands.command(name="설정브랜드배지", description="클랜 패키지 서버의 웹사이트 배지 문구를 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_brand_badge(self, interaction: discord.Interaction, 배지문구: str):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, badge_text=배지문구[:50])
        await interaction.response.send_message(f"브랜드 배지를 `{brand['badge_text']}` 로 설정했습니다.", ephemeral=True)

    @app_commands.command(name="브랜드초기화", description="클랜 패키지 서버의 웹사이트 브랜딩을 기본값으로 되돌립니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_brand(self, interaction: discord.Interaction):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.clear_clan_branding(interaction.guild_id)
        await interaction.response.send_message(
            f"브랜딩을 초기화했습니다.\n기본 이름: `{brand['brand_name']}`\n기본 배지: `{brand['badge_text']}`\n기본 색상: `{brand['brand_color']}`",
            ephemeral=True,
        )


    @app_commands.command(name="클랜소개문구", description="클랜 패키지 서버의 소개 문구를 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_clan_intro(self, interaction: discord.Interaction, 문구: str):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, intro_text=문구[:500])
        await interaction.response.send_message(
            f"클랜 소개 문구를 설정했습니다.\n`{brand['intro_text']}`",
            ephemeral=True
        )

    @app_commands.command(name="클랜시작템플릿", description="클랜 패키지 서버의 시작 공지 템플릿을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_clan_start_template(self, interaction: discord.Interaction, 템플릿: str):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, start_template=템플릿[:1000])
        await interaction.response.send_message(
            "시작 공지 템플릿을 설정했습니다.\n"
            "사용 가능 변수: {badge}, {brand_name}, {game}, {channel}, {mode_text}, {team_a}, {team_b}, {difference}\n\n"
            f"현재 템플릿:\n```\n{brand['start_template']}\n```",
            ephemeral=True
        )

    @app_commands.command(name="클랜결과템플릿", description="클랜 패키지 서버의 결과 공지 템플릿을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_clan_result_template(self, interaction: discord.Interaction, 템플릿: str):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, result_template=템플릿[:1000])
        await interaction.response.send_message(
            "결과 공지 템플릿을 설정했습니다.\n"
            "사용 가능 변수: {badge}, {brand_name}, {game}, {winner_team}, {avg_a}, {avg_b}, {channel}\n\n"
            f"현재 템플릿:\n```\n{brand['result_template']}\n```",
            ephemeral=True
        )

    @app_commands.command(name="클랜공지초기화", description="클랜 소개/시작/결과 공지 템플릿을 기본값으로 초기화합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_clan_templates(self, interaction: discord.Interaction):
        if not self.is_clan_guild(interaction.guild_id):
            await interaction.response.send_message("이 기능은 클랜 패키지 서버 전용입니다.", ephemeral=True)
            return
        brand = db.update_clan_branding(interaction.guild_id, intro_text="", start_template="", result_template="")
        await interaction.response.send_message(
            f"클랜 공지 템플릿을 초기화했습니다.\n소개: `{brand['intro_text']}`",
            ephemeral=True
        )

    @app_commands.command(name="설정보기", description="현재 서버 설정을 확인합니다.")
    async def show(self, interaction: discord.Interaction):
        data = db.get_settings(interaction.guild_id)
        if not data:
            await interaction.response.send_message("설정이 없습니다.", ephemeral=True)
            return

        role = interaction.guild.get_role(data["recruit_role_id"]) if data["recruit_role_id"] else None
        category = interaction.guild.get_channel(data["category_id"]) if data["category_id"] else None
        log_channel = interaction.guild.get_channel(data["log_channel_id"]) if data["log_channel_id"] else None
        announcement_channel = interaction.guild.get_channel(data["announcement_channel_id"]) if data["announcement_channel_id"] else None
        premium = db.get_premium_info(interaction.guild_id)
        brand = db.get_clan_branding(interaction.guild_id)

        lines = [
            f"인증 역할: {role.mention if role else '미설정'}",
            f"내전 카테고리: {category.mention if category else '미설정'}",
            f"운영 로그 채널: {log_channel.mention if log_channel else '미설정'}",
            f"공지/결과 채널: {announcement_channel.mention if announcement_channel else '미설정'}",
            f"프리미엄 상태: {premium.get('plan_name', '무료') if premium else '무료'}",
        ]

        if brand["is_clan"]:
            lines.extend([
                f"브랜드 이름: {brand['brand_name']}",
                f"브랜드 색상: {brand['brand_color']}",
                f"브랜드 배지: {brand['badge_text']}",
                f"클랜 소개 문구: {brand['intro_text']}",
                f"시작 공지 템플릿: {brand['start_template']}",
                f"결과 공지 템플릿: {brand['result_template']}",
            ])

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))
