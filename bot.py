import asyncio
import discord
from discord.ext import commands

from core.config import TOKEN

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"글로벌 슬래시 동기화 완료: {len(synced)}개")
    except Exception as e:
        print(f"슬래시 동기화 오류: {e}")

    print(f"{bot.user} 온라인")


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
    async with bot:
        await bot.load_extension("cogs.settings_cog")
        await bot.load_extension("cogs.recruit_cog")
        await bot.load_extension("cogs.team_cog")
        await bot.load_extension("cogs.ranking_cog")
        await bot.load_extension("cogs.profile_cog")
        await bot.load_extension("cogs.help_cog")
        await bot.load_extension("cogs.premium_cog")
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    asyncio.run(main())