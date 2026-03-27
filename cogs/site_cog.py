import discord
from discord.ext import commands
from discord import app_commands

from core.config import WEBSITE_URL


class SiteButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        if WEBSITE_URL:
            self.add_item(
                discord.ui.Button(
                    label="ELO 랭킹 사이트 열기",
                    style=discord.ButtonStyle.link,
                    url=WEBSITE_URL
                )
            )


class Site(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="사이트", description="ELO 랭킹 사이트 링크를 보여줍니다.")
    async def site(self, interaction: discord.Interaction):
        if not WEBSITE_URL:
            await interaction.response.send_message(
                "웹사이트 주소가 아직 설정되지 않았습니다.\nRailway Variables에 `WEBSITE_URL`을 넣어주세요.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🌐 ELO 랭킹 사이트",
            description="아래 버튼을 눌러 전적 / 랭킹 사이트로 이동하세요.",
            color=discord.Color.blue()
        )
        embed.add_field(name="웹사이트 주소", value=WEBSITE_URL, inline=False)

        await interaction.response.send_message(
            embed=embed,
            view=SiteButtonView(),
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Site(bot))