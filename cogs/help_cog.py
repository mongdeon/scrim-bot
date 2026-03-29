import discord
from discord.ext import commands
from discord import app_commands


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="봇 명령어와 사용법을 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="💿 내전봇 도움말",
            description="무료 명령어, 프리미엄 명령어, 배그 내전 생성 방법을 확인할 수 있습니다.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🆓 무료 명령어",
            value=(
                "`/설정역할` - 내전 참여 가능 역할 설정\n"
                "`/설정카테고리` - 내전 음성채널 생성 카테고리 설정\n"
                "`/설정보기` - 현재 서버 설정 확인\n"
                "`/내전생성` - 내전 모집 시작\n"
                "`/내전상태` - 현재 로비 상태 확인\n"
                "`/밸런스팀` - 자동 팀 분배\n"
                "`/내전종료` - 현재 내전 종료\n"
                "`/핑` - 봇 상태 확인\n"
                "`/사이트` - 전적 사이트 / 지원 사이트 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="🎯 배그 내전 생성 방법",
            value=(
                "**배그는 솔로 / 듀오 / 스쿼드 형식으로 생성할 수 있습니다.**\n\n"
                "`/내전생성 게임:PUBG 배그형식:솔로`\n"
                "`/내전생성 게임:PUBG 배그형식:듀오`\n"
                "`/내전생성 게임:PUBG 배그형식:스쿼드`\n\n"
                "형식 기준:\n"
                "- 솔로 = 1 vs 1\n"
                "- 듀오 = 2 vs 2\n"
                "- 스쿼드 = 4 vs 4"
            ),
            inline=False
        )

        embed.add_field(
            name="⭐ 프리미엄 명령어",
            value=(
                "`/결과기록` - 경기 결과 기록 및 ELO/MMR 반영\n"
                "`/시즌생성` - 게임별 시즌 생성\n"
                "`/시즌종료` - 현재 시즌 종료\n"
                "`/시즌확인` - 현재 시즌 확인\n"
                "`/시즌목록` - 시즌 목록 확인\n"
                "`/시즌랭킹` - 현재 시즌 랭킹 확인\n"
                "`/맵뽑기` - 현재 로비 게임 기준 랜덤 맵 선택\n"
                "`/맵뽑기상태` - 현재 맵 뽑기 결과 확인\n"
                "`/맵뽑기초기화` - 맵 뽑기 결과 초기화"
            ),
            inline=False
        )

        embed.add_field(
            name="📌 빠른 시작 순서",
            value=(
                "1. `/설정역할`\n"
                "2. `/설정카테고리`\n"
                "3. `/내전생성`\n"
                "4. `/밸런스팀`\n"
                "5. 필요 시 `/결과기록`"
            ),
            inline=False
        )

        embed.set_footer(text="배그 내전은 배그형식 옵션을 사용하면 솔로 / 듀오 / 스쿼드로 생성할 수 있습니다.")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="프리미엄도움말", description="프리미엄 기능 안내를 확인합니다.")
    async def premium_help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⭐ 프리미엄 기능 안내",
            description="프리미엄 서버에서 사용할 수 있는 기능입니다.",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="프리미엄 기능",
            value=(
                "- 결과기록 / ELO 반영\n"
                "- 상세 전적\n"
                "- 게임별 시즌\n"
                "- 시즌 랭킹 / 시즌 경기 기록\n"
                "- 맵뽑기"
            ),
            inline=False
        )

        embed.add_field(
            name="추가 예정",
            value=(
                "- 드래프트\n"
                "- 고급 통계"
            ),
            inline=False
        )

        embed.set_footer(text="프리미엄 신청은 사이트 또는 지원 페이지에서 확인할 수 있습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))