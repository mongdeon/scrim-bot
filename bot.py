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
    synced = await bot.tree.sync()
    print(f"슬래시 동기화: {len(synced)}")
    print("봇 로그인 완료")


@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and isinstance(before.channel, discord.VoiceChannel):
        channel = before.channel
        if channel.name.endswith("대기방") and len(channel.members) == 0:
            try:
                await channel.delete()
            except Exception:
                pass


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