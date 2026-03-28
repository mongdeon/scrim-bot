import discord
from discord.ext import commands
from discord import app_commands


SUPPORT_SITE_URL = "https://elegant-cooperation-production-03d5.up.railway.app/"


class SupportSiteButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="지원 사이트",
                style=discord.ButtonStyle.link,
                url=SUPPORT_SITE_URL,
                emoji="🛟"
            )
        )


class Site(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="사이트", description="지원 사이트 링크를 확인합니다.")
    async def site(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🌐 내전봇 사이트",
            description="아래 버튼을 통해 지원 페이지로 이동할 수 있습니다.",
            color=discord.Color.blue()
        )

        await interaction.response.send_message(
            embed=embed,
            view=SupportSiteButton(),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Site(bot))