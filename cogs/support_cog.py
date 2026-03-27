import discord
from discord.ext import commands
from discord import app_commands


DONATION_URL = "https://toss.me/여기에_후원링크_넣기"


class SupportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="후원", description="봇 개발 후원 링크를 보여줍니다.")
    async def support(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💖 개발 후원",
            description="이 봇이 도움이 되었다면 후원으로 개발을 응원해주세요.",
            color=discord.Color.pink()
        )
        embed.add_field(
            name="후원 링크",
            value=f"[여기를 눌러 후원하기]({DONATION_URL})",
            inline=False
        )
        embed.add_field(
            name="안내",
            value="후원금은 서버비와 기능 업데이트에 사용됩니다.",
            inline=False
        )
        embed.set_footer(text="후원은 선택입니다. 사용만 해줘도 큰 힘이 됩니다.")

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="후원하러 가기",
                style=discord.ButtonStyle.link,
                url=DONATION_URL
            )
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SupportCog(bot))