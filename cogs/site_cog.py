import discord
from discord.ext import commands
from discord import app_commands

from core.config import WEBSITE_URL


class Site(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="사이트", description="전적 사이트와 지원 페이지 링크를 보여줍니다.")
    async def site(self, interaction: discord.Interaction):
        if not WEBSITE_URL:
            await interaction.response.send_message(
                "웹사이트 주소가 아직 설정되지 않았습니다.",
                ephemeral=True
            )
            return

        support_url = f"{WEBSITE_URL}/support"

        embed = discord.Embed(
            title="🌐 내전봇 사이트",
            description="아래 버튼을 눌러 전적 사이트 또는 지원 페이지로 이동하세요.",
            color=discord.Color.blue()
        )
        embed.add_field(name="전적 사이트", value=WEBSITE_URL, inline=False)
        embed.add_field(name="지원 페이지", value=support_url, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="ELO 랭킹 사이트 열기",
                style=discord.ButtonStyle.link,
                url=WEBSITE_URL
            )
        )
        view.add_item(
            discord.ui.Button(
                label="사용법 / 지원",
                style=discord.ButtonStyle.link,
                url=support_url
            )
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Site(bot))