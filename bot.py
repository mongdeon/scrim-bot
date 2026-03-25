import discord
from discord.ext import commands
import asyncio
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


# ⭐ 봇 상태 확인 명령어
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
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())