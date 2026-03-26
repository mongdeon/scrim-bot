from core.db import Database

db = Database()

async def main():
    async with bot:
        await db.connect()   # ⭐⭐⭐ 이거 추가

        await bot.load_extension("cogs.settings_cog")
        await bot.load_extension("cogs.recruit_cog")
        await bot.load_extension("cogs.team_cog")
        await bot.load_extension("cogs.ranking_cog")
        await bot.load_extension("cogs.profile_cog")
        await bot.load_extension("cogs.help_cog")

        await bot.start(TOKEN)