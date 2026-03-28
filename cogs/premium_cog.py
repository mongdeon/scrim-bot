import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta

from core.db import DB
from core.config import OWNER_ID

db = DB()
db.init_premium_tables()


def is_owner(user_id: int) -> bool:
    return OWNER_ID != 0 and user_id == OWNER_ID


def get_premium_info(guild_id: int) -> dict | None:
    db.cleanup_expired_premium_guilds()
    row = db.fetchone("""
        SELECT guild_id, is_premium, premium_until, updated_at
        FROM premium_guilds
        WHERE guild_id = %s
    """, (guild_id,))

    if not row:
        return None

    return row


def set_premium(guild_id: int, enabled: bool):
    db.init_premium_tables()

    if enabled:
        db.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, updated_at)
            VALUES (%s, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                is_premium = TRUE,
                updated_at = CURRENT_TIMESTAMP
        """, (guild_id,))
    else:
        db.execute("""
            INSERT INTO premium_guilds (guild_id, is_premium, premium_until, updated_at)
            VALUES (%s, FALSE, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                is_premium = FALSE,
                premium_until = NULL,
                updated_at = CURRENT_TIMESTAMP
        """, (guild_id,))


def set_premium_days(guild_id: int, days: int):
    db.init_premium_tables()
    current = get_premium_info(guild_id)

    now = datetime.now(timezone.utc)
    base_time = now

    if current and current.get("is_premium") and current.get("premium_until"):
        premium_until = current["premium_until"]
        if premium_until.tzinfo is None:
            premium_until = premium_until.replace(tzinfo=timezone.utc)
        if premium_until > now:
            base_time = premium_until

    new_until = base_time + timedelta(days=days)

    db.execute("""
        INSERT INTO premium_guilds (guild_id, is_premium, premium_until, updated_at)
        VALUES (%s, TRUE, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (guild_id)
        DO UPDATE SET
            is_premium = TRUE,
            premium_until = %s,
            updated_at = CURRENT_TIMESTAMP
    """, (guild_id, new_until, new_until))


def format_expire_text(info: dict) -> str:
    if not info:
        return "무료 서버"

    if not info.get("is_premium"):
        return "무료 서버"

    expires_at = info.get("premium_until")
    if not expires_at:
        return "프리미엄 서버 (만료일 없음)"

    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    remain = expires_at - now
    if remain.total_seconds() < 0:
        return "무료 서버"

    days_left = remain.days
    hours_left = remain.seconds // 3600

    return f"프리미엄 서버 (약 {days_left}일 {hours_left}시간 남음)"


class Premium(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="프리미엄추가", description="프리미엄 기간 추가 (오너 전용)")
    @app_commands.describe(일수="추가할 프리미엄 일수")
    async def premium_add(self, interaction: discord.Interaction, 일수: int):
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

            set_premium_days(interaction.guild.id, 일수)
            info = get_premium_info(interaction.guild.id)

            await interaction.response.send_message(
                f"✅ 프리미엄이 {일수}일 추가되었습니다.\n현재 상태: {format_expire_text(info)}",
                ephemeral=True
            )
        except Exception as e:
            print("프리미엄추가 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="프리미엄30일", description="프리미엄 30일 활성화 (오너 전용)")
    async def premium_30(self, interaction: discord.Interaction):
        try:
            if not is_owner(interaction.user.id):
                await interaction.response.send_message(
                    "⛔ 이 명령어는 봇 오너만 사용할 수 있습니다.",
                    ephemeral=True
                )
                return

            set_premium_days(interaction.guild.id, 30)
            info = get_premium_info(interaction.guild.id)

            await interaction.response.send_message(
                f"✅ 프리미엄 30일이 적용되었습니다.\n현재 상태: {format_expire_text(info)}",
                ephemeral=True
            )
        except Exception as e:
            print("프리미엄30일 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="프리미엄90일", description="프리미엄 90일 활성화 (오너 전용)")
    async def premium_90(self, interaction: discord.Interaction):
        try:
            if not is_owner(interaction.user.id):
                await interaction.response.send_message(
                    "⛔ 이 명령어는 봇 오너만 사용할 수 있습니다.",
                    ephemeral=True
                )
                return

            set_premium_days(interaction.guild.id, 90)
            info = get_premium_info(interaction.guild.id)

            await interaction.response.send_message(
                f"✅ 프리미엄 90일이 적용되었습니다.\n현재 상태: {format_expire_text(info)}",
                ephemeral=True
            )
        except Exception as e:
            print("프리미엄90일 오류:", e)
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

            set_premium(interaction.guild.id, False)
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

    @app_commands.command(name="프리미엄확인", description="프리미엄 상태 확인")
    async def premium_check(self, interaction: discord.Interaction):
        try:
            info = get_premium_info(interaction.guild.id)
            text = format_expire_text(info)

            if info and info.get("is_premium"):
                await interaction.response.send_message(f"⭐ 이 서버는 {text} 입니다.")
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