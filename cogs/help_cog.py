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
            description="사용 가능한 명령어 목록입니다.",
            color=discord.Color.green()
        )

        embed.add_field(
            name="⚙️ 서버 설정",
            value=(
                "`/설정역할` → 내전 참여 역할 설정\n"
                "`/설정카테고리` → 내전 생성 카테고리\n"
                "`/설정보기` → 현재 설정 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="📢 내전",
            value=(
                "`/내전생성` → 내전 모집 시작\n"
                "`/내전상태` → 모집 상태 확인\n"
                "`/내전종료` → 내전 종료 및 정리"
            ),
            inline=False
        )

        embed.add_field(
            name="⚔️ 팀 / 진행",
            value=(
                "`/밸런스팀` → 자동 팀 분배\n"
                "`/내전시작` → 음성 채널 자동 이동\n"
                "`/결과기록` → 승패 기록 + ELO 반영"
            ),
            inline=False
        )

        embed.add_field(
            name="📊 전적 / 랭킹 / 안내",
            value=(
                "`/랭킹` → 서버 ELO 랭킹\n"
                "`/내전전적` → 내 전적 확인\n"
                "`/최근전적` → 최근 경기\n"
                "`/사이트` → 전적 사이트 / 지원 페이지\n"
                "`/초대` → 봇 초대 링크\n"
                "`/지원서버` → 지원 링크\n"
                "`/소개` → 봇 소개"
            ),
            inline=False
        )

        embed.add_field(
            name="🎯 티어 등록 / 점수표",
            value=(
                "**발로란트**\n"
                "`/발로티어등록`\n"
                "`/티어점수표`\n\n"
                "**오버워치**\n"
                "`/옵치티어등록`\n"
                "`/옵치티어점수표`\n\n"
                "**리그 오브 레전드**\n"
                "`/롤티어등록`\n"
                "`/롤티어점수표`"
            ),
            inline=False
        )

        embed.add_field(
            name="⭐ 프리미엄",
            value=(
                "`/프리미엄확인`\n"
                "`/프리미엄추가` (오너)\n"
                "`/프리미엄30일` (오너)\n"
                "`/프리미엄90일` (오너)\n"
                "`/프리미엄끄기` (오너)"
            ),
            inline=False
        )

        embed.add_field(
            name="💖 기타",
            value=(
                "`/핑`\n"
                "`/도움말`\n"
                "`/후원`"
            ),
            inline=False
        )

        embed.set_footer(text="내전 운영을 더 쉽고 편하게!")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))