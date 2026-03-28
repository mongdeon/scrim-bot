import os
import discord
from discord.ext import commands
from discord import app_commands


def get_site_urls() -> tuple[str, str]:
    site_url = os.getenv("SITE_URL", "").strip()
    support_url = os.getenv("SUPPORT_SITE_URL", "").strip()

    if site_url.endswith("/"):
        site_url = site_url[:-1]

    if not support_url and site_url:
        support_url = f"{site_url}/support"

    return site_url, support_url


class SupportSiteButton(discord.ui.View):
    def __init__(self, support_url: str):
        super().__init__(timeout=None)

        if support_url:
            self.add_item(
                discord.ui.Button(
                    label="지원 사이트",
                    style=discord.ButtonStyle.link,
                    url=support_url,
                    emoji="🛟"
                )
            )


class Site(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="사이트", description="전적 사이트 및 지원 페이지 링크를 확인합니다.")
    async def site(self, interaction: discord.Interaction):
        site_url, support_url = get_site_urls()

        if not site_url:
            await interaction.response.send_message(
                "사이트 주소가 설정되지 않았습니다. `SITE_URL` 환경변수를 먼저 설정해주세요.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🌐 내전봇 사이트",
            description="아래 링크를 통해 전적 사이트 또는 지원 페이지로 이동할 수 있습니다.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="전적 사이트",
            value=site_url,
            inline=False
        )

        if support_url:
            embed.add_field(
                name="지원 페이지",
                value=support_url,
                inline=False
            )
        else:
            embed.add_field(
                name="지원 페이지",
                value="지원 페이지 주소가 설정되지 않았습니다.",
                inline=False
            )

        view = SupportSiteButton(support_url) if support_url else None

        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Site(bot))