import discord
from discord.ext import commands
from discord import app_commands


BANK_NAME = "토스뱅크"
ACCOUNT_NUMBER = "1000-0103-2111"
ACCOUNT_HOLDER = "김태용"


class SupportCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="후원", description="봇 개발 후원 안내를 보여줍니다.")
    async def support(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=":sparkling_heart: 개발 후원",
            description="이 봇이 도움이 되었다면 후원으로 개발을 응원해주세요.",
            color=discord.Color.pink()
        )

        embed.add_field(name="후원 방법", value="계좌이체", inline=False)
        embed.add_field(name="은행", value=BANK_NAME, inline=True)
        embed.add_field(name="계좌번호", value=ACCOUNT_NUMBER, inline=True)
        embed.add_field(name="예금주", value=ACCOUNT_HOLDER, inline=True)
        embed.add_field(
            name="안내",
            value="후원금은 서버비와 기능 업데이트에 사용됩니다.",
            inline=False
        )
        embed.set_footer(text="후원은 선택입니다. 사용만 해줘도 큰 힘이 됩니다.")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SupportCog(bot))