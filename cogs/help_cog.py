import discord
from discord.ext import commands
from discord import app_commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="내전봇 명령어 목록을 보여줍니다.")
    async def help_cmd(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎮 내전봇 도움말",
            description="사용 가능한 명령어 목록",
            color=discord.Color.green()
        )

        embed.add_field(
            name="⚙️ 서버 설정",
            value="""
`/설정역할` → 내전 참여 가능한 역할 설정
`/설정카테고리` → 내전 생성 카테고리 설정
`/설정보기` → 현재 설정 확인
""",
            inline=False
        )

        embed.add_field(
            name="📢 내전",
            value="""
`/내전생성` → 내전 모집 시작
`/내전상태` → 현재 모집 상태
`/내전종료` → 내전 종료 및 통화방 정리
""",
            inline=False
        )

        embed.add_field(
            name="⚔️ 팀 / 결과",
            value="""
`/밸런스팀` → 자동 팀 분배
`/내전시작` → 자동 음성 이동 후 진행
`/결과기록` → 승패 기록 + ELO 반영 (프리미엄 전용)
""",
            inline=False
        )

        embed.add_field(
            name="📊 전적 / 랭킹",
            value="""
`/랭킹` → 서버 ELO 랭킹
`/내전전적` → 내 전적 확인
`/최근전적` → 최근 경기
`/사이트` → ELO 랭킹 사이트 버튼
""",
            inline=False
        )

        embed.add_field(
            name="🎯 게임별 티어 등록 / 점수표",
            value="""
**발로란트**
`/발로티어등록`
`/티어점수표`

**오버워치**
`/옵치티어등록`
`/옵치티어점수표`

**리그 오브 레전드**
`/롤티어등록`
`/롤티어점수표`
""",
            inline=False
        )

        embed.add_field(
            name="⭐ 프리미엄",
            value="""
`/프리미엄확인`
`/프리미엄켜기` → 오너 전용
`/프리미엄끄기` → 오너 전용
""",
            inline=False
        )

        embed.add_field(
            name="🤖 기타",
            value="""
`/핑`
`/도움말`
""",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))