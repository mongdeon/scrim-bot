import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.db import DB


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
GUILD_ID_RAW = os.getenv("GUILD_ID", "").strip()

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = DB()


async def load_extensions():
    cogs = [
        "cogs.help_cog",
        "cogs.settings_cog",
        "cogs.recruit_cog",
        "cogs.team_cog",
        "cogs.profile_cog",
        "cogs.mapban_cog",
        "cogs.season_cog",
        "cogs.premium_cog",
    ]

    for ext in cogs:
        try:
            await bot.load_extension(ext)
            print(f"[LOAD OK] {ext}")
        except commands.ExtensionAlreadyLoaded:
            print(f"[SKIP] already loaded: {ext}")
        except Exception as e:
            print(f"[LOAD FAIL] {ext}: {e}")


async def sync_commands():
    try:
        if GUILD_ID_RAW.isdigit():
            guild = discord.Object(id=int(GUILD_ID_RAW))
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"[SYNC] guild sync 완료: {len(synced)}개 (guild_id={GUILD_ID_RAW})")
        else:
            synced = await bot.tree.sync()
            print(f"[SYNC] global sync 완료: {len(synced)}개")
    except Exception as e:
        print(f"[SYNC ERROR] {e}")


@bot.event
async def on_ready():
    print(f"로그인 완료: {bot.user} ({bot.user.id})")
    await sync_commands()


@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        db.register_guild(guild.id, guild.name)
        print(f"[GUILD JOIN] {guild.name} ({guild.id})")
    except Exception as e:
        print(f"[GUILD JOIN ERROR] {e}")


@bot.event
async def on_guild_remove(guild: discord.Guild):
    try:
        db.deactivate_guild(guild.id)
        print(f"[GUILD REMOVE] {guild.name} ({guild.id})")
    except Exception as e:
        print(f"[GUILD REMOVE ERROR] {e}")


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")

    db.init_tables()

    async with bot:
        await load_extensions()
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
