import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

from core.db import DB
from core.config import OWNER_ID

db = DB()

PLAN_CHOICES = [
    app_commands.Choice(name="서포터", value="supporter"),
    app_commands.Choice(name="프로", value="pro"),
    app_commands.Choice(name="클랜", value="clan"),
]


def is_owner(user_id: int) -> bool:
    return OWNER_ID != 0 and user_id == OWNER_ID


def format_expire_text(info: dict) -> str:
    if not info or not info.get("is_premium"):
        return "무료 서버"

    plan_name = info.get("plan_name") or "프리미엄"
    expires_at = info.get("premium_until")

    if not expires_at:
        return f"{plan_name} 패키지 (만료일 없음)"

    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    remain = expires_at - now
    if remain.total_seconds() < 0:
        return "무료 서버"

    days_left = remain.days
    hours_left = remain.seconds // 3600
    return f"{plan_name} 패키지 (약 {days_left}일 {hours_left}시간 남음)"


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="프리미엄추가", description="패키지형 프리미엄 기간 추가 (오너 전용)")
    @app_commands.describe(패키지="적용할 패키지", 일수="추가할 프리미엄 일수")
    @app_commands.choices(패키지=PLAN_CHOICES)
    async def premium_add(self, interaction: discord.Interaction, 패키지: app_commands.Choice[str], 일수: int):
        try:
            if not is_owner(interaction.user.id):
                await interaction.response.send_message(
                    "⛔ 이 명령어는 봇 오너만 사용할 수 있습니다.",
                    ephemeral=True
                )
                return

            if 일수 <= 0:
                await interaction.response.send_message("일수는 1 이상이어야 합니다.", ephemeral=True)
                return

            info = db.set_premium_days(interaction.guild.id, 일수, 패키지.value)

            await interaction.response.send_message(
                f"✅ {info.get('plan_name')} 패키지가 {일수}일 적용되었습니다.\n현재 상태: {format_expire_text(info)}",
                ephemeral=True
            )

        except Exception as e:
            print("프리미엄추가 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="프리미엄끄기", description="프리미엄 해제 (오너 전용)")
    async def premium_off(self, interaction: discord.Interaction):
        try:
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

        except Exception as e:
            print("프리미엄끄기 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="프리미엄확인", description="현재 패키지형 프리미엄 상태 확인")
    async def premium_check(self, interaction: discord.Interaction):
        try:
            info = db.get_premium_info(interaction.guild.id)
            text = format_expire_text(info)

            if info and info.get("is_premium"):
                await interaction.response.send_message(
                    f"⭐ 이 서버는 현재 **{info.get('plan_name', '프리미엄')} 패키지** 입니다.\n상태: {text}"
                )
            else:
                await interaction.response.send_message("⚪ 이 서버는 무료 서버입니다.")

        except Exception as e:
            print("프리미엄확인 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Premium(bot))
