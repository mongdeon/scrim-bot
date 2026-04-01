import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


def _mention_channel(guild: discord.Guild, channel_id):
    if not channel_id:
        return "미설정"
    ch = guild.get_channel(channel_id)
    return ch.mention if ch else f"<#{channel_id}>"


def _mention_role(guild: discord.Guild, role_id):
    if not role_id:
        return "미설정"
    role = guild.get_role(role_id)
    return role.mention if role else f"<@&{role_id}>"


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_log(self, guild: discord.Guild, title: str, description: str):
        try:
            settings = db.get_settings(guild.id)
            log_channel_id = settings.get("log_channel_id") if settings else None
            if not log_channel_id:
                return
            channel = guild.get_channel(log_channel_id)
            if not isinstance(channel, discord.TextChannel):
                return
            embed = discord.Embed(title=title, description=description, color=discord.Color.dark_teal())
            await channel.send(embed=embed)
        except Exception:
            pass

    @app_commands.command(name="설정역할", description="내전 참여 인증 역할을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_role(self, interaction: discord.Interaction, 역할: discord.Role):
        db.update_settings(interaction.guild.id, recruit_role_id=역할.id)
        await interaction.response.send_message(f"인증 역할을 {역할.mention} 로 설정했습니다.", ephemeral=True)
        await self._send_log(interaction.guild, "설정 변경", f"인증 역할 변경: {역할.mention}")

    @app_commands.command(name="설정카테고리", description="내전 음성채널이 생성될 카테고리를 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_category(self, interaction: discord.Interaction, 카테고리: discord.CategoryChannel):
        db.update_settings(interaction.guild.id, category_id=카테고리.id)
        await interaction.response.send_message(f"내전 카테고리를 {카테고리.name} 로 설정했습니다.", ephemeral=True)
        await self._send_log(interaction.guild, "설정 변경", f"내전 카테고리 변경: **{카테고리.name}**")

    @app_commands.command(name="설정공지채널", description="공지 채널을 설정합니다. 결과 채널도 함께 동일하게 설정됩니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_announcement_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(
            interaction.guild.id,
            announcement_channel_id=채널.id,
            result_channel_id=채널.id
        )
        await interaction.response.send_message(
            f"공지 채널을 {채널.mention} 로 설정했습니다.\n팀 결과 채널도 동일하게 설정되었습니다.",
            ephemeral=True
        )
        await self._send_log(interaction.guild, "설정 변경", f"공지 채널 변경: {채널.mention}")

    @app_commands.command(name="설정팀결과채널", description="팀 자동 분배 결과가 올라갈 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_result_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild.id, result_channel_id=채널.id)
        await interaction.response.send_message(
            f"팀 자동 분배 결과 채널을 {채널.mention} 로 설정했습니다.",
            ephemeral=True
        )
        await self._send_log(interaction.guild, "설정 변경", f"팀 결과 채널 변경: {채널.mention}")

    @app_commands.command(name="설정로그채널", description="운영 로그 채널을 설정합니다.")
    @app_commands.checks.has_permissions(administrator=True)
    async def set_log_channel(self, interaction: discord.Interaction, 채널: discord.TextChannel):
        db.update_settings(interaction.guild.id, log_channel_id=채널.id)
        await interaction.response.send_message(f"운영 로그 채널을 {채널.mention} 로 설정했습니다.", ephemeral=True)
        await self._send_log(interaction.guild, "설정 변경", f"운영 로그 채널 변경: {채널.mention}")

    @app_commands.command(name="설정보기", description="현재 서버 설정을 확인합니다.")
    async def show_settings(self, interaction: discord.Interaction):
        try:
            settings = db.get_settings(interaction.guild.id)
            premium = db.get_premium_info(interaction.guild.id)

            embed = discord.Embed(
                title="⚙️ 현재 서버 설정",
                description=f"현재 서버 패키지: **{premium.get('plan_name', '무료')}**",
                color=discord.Color.blurple()
            )

            embed.add_field(name="인증 역할", value=_mention_role(interaction.guild, settings.get("recruit_role_id")), inline=False)
            embed.add_field(name="내전 카테고리", value=_mention_channel(interaction.guild, settings.get("category_id")), inline=False)
            embed.add_field(name="공지 채널", value=_mention_channel(interaction.guild, settings.get("announcement_channel_id")), inline=False)
            embed.add_field(name="팀 결과 채널", value=_mention_channel(interaction.guild, settings.get("result_channel_id")), inline=False)
            embed.add_field(name="운영 로그 채널", value=_mention_channel(interaction.guild, settings.get("log_channel_id")), inline=False)

            if "clan_brand_name" in settings:
                brand_name = settings.get("clan_brand_name") or "미설정"
                brand_color = settings.get("clan_brand_color") or "미설정"
                badge_text = settings.get("clan_badge_text") or "미설정"
                intro_text = settings.get("clan_intro_text") or "미설정"
                embed.add_field(
                    name="클랜 브랜딩",
                    value=(
                        f"브랜드 이름: {brand_name}\n"
                        f"브랜드 색상: {brand_color}\n"
                        f"배지 문구: {badge_text}\n"
                        f"소개 문구: {intro_text[:200]}"
                    ),
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"설정을 불러오는 중 오류가 발생했습니다: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"설정을 불러오는 중 오류가 발생했습니다: {e}", ephemeral=True)

    @set_role.error
    @set_category.error
    @set_announcement_channel.error
    @set_result_channel.error
    @set_log_channel.error
    async def admin_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            msg = "관리자 권한이 필요합니다."
        else:
            msg = f"오류가 발생했습니다: {error}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
