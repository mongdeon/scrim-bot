import discord
from discord.ext import commands
from discord import app_commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="봇 명령어 목록을 보여줍니다.")
    async def help_command(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title=":video_game: 내전봇 명령어 도움말",
            description="사용 가능한 명령어 목록입니다.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name=":gear: 설정",
            value="""
            /설정역할
            /설정카테고리
            /설정보기
            """,
            inline=False
        )

        embed.add_field(
            name=":loudspeaker: 내전",
            value="""
            /내전생성
            /내전종료
            /내전상태
            """,
            inline=False
        )

        embed.add_field(
            name=":busts_in_silhouette: 팀 관련",
            value="""
            /밸런스팀
            /팀장뽑기
            """,
            inline=False
        )

        embed.add_field(
            name=":bar_chart: 전적 / 랭킹",
            value="""
            /랭킹
            /최근전적
            """,
            inline=False
        )

        embed.add_field(
            name=":brain: 프로필",
            value="""
            /발로티어등록
            /옵치티어등록
            """,
            inline=False
        )

        embed.add_field(
            name=":robot: 기타",
            value="""
            /핑
            """,
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Help(bot))