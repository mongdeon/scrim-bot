import asyncio
import discord
from discord.ext import commands

from core.config import TOKEN
from core.db import DB

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = DB()


async def try_send_welcome_message(guild: discord.Guild):
    message = (
        "안녕하세요. 내전봇이 서버에 추가되었습니다.\n\n"
        "먼저 아래 순서대로 설정해주세요.\n"
        "1. /설정역할\n"
        "2. /설정카테고리\n"
        "3. /내전생성\n\n"
        "프리미엄 기능은 /사이트 또는 지원 페이지에서 확인할 수 있습니다."
    )

    target_channel = None

    if guild.system_channel:
        perms = guild.system_channel.permissions_for(guild.me)
        if perms.view_channel and perms.send_messages:
            target_channel = guild.system_channel

    if target_channel is None:
        for channel in guild.text_channels:
            perms = channel.permissions_for(guild.me)
            if perms.view_channel and perms.send_messages:
                target_channel = channel
                break

    if target_channel is not None:
        try:
            await target_channel.send(message)
        except Exception as e:
            print(f"환영 메시지 전송 실패 ({guild.id}): {e}")


@bot.event
async def on_ready():
    try:
        DB.init_tables()
        synced = await bot.tree.sync()
        print(f"글로벌 슬래시 동기화 완료: {len(synced)}개")
    except Exception as e:
        print(f"슬래시 동기화 오류: {e}")

    print(f"{bot.user} 온라인")


@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        print(f"새 서버 추가됨: {guild.name} ({guild.id})")

        # 전체 테이블 보장
        DB.init_tables()

        # 서버 기본 설정 생성
        db.ensure_guild_settings(guild.id)

        # 프리미엄 기본값 생성
        db.set_premium(guild.id, False)

        print(f"서버 자동 초기화 완료: {guild.name} ({guild.id})")

        await try_send_welcome_message(guild)

    except Exception as e:
        print(f"on_guild_join 자동 초기화 오류 ({guild.id}): {e}")


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and isinstance(before.channel, discord.VoiceChannel):
        channel = before.channel

        if channel.name.endswith("대기방"):
            await asyncio.sleep(1)

            refreshed_channel = member.guild.get_channel(channel.id)
            if refreshed_channel and isinstance(refreshed_channel, discord.VoiceChannel):
                if len(refreshed_channel.members) == 0:
                    try:
                        await refreshed_channel.delete(reason="대기방 인원 0명 자동 삭제")
                        print(f"대기방 자동 삭제: {refreshed_channel.name}")
                    except Exception as e:
                        print(f"대기방 삭제 실패: {e}")


@bot.tree.command(name="핑", description="봇 상태 확인")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("퐁 🏓")


async def main():
    DB.init_tables()

    async with bot:
        await bot.load_extension("cogs.settings_cog")
        await bot.load_extension("cogs.recruit_cog")
        await bot.load_extension("cogs.team_cog")
        await bot.load_extension("cogs.season_cog")
        await bot.load_extension("cogs.mapban_cog")
        await bot.load_extension("cogs.ranking_cog")
        await bot.load_extension("cogs.profile_cog")
        await bot.load_extension("cogs.help_cog")
        await bot.load_extension("cogs.premium_cog")
        await bot.load_extension("cogs.site_cog")
        await bot.load_extension("cogs.support_cog")
        await bot.load_extension("cogs.growth_cog")
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    asyncio.run(main())