import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


def build_help_embed(guild_id: int | None = None) -> discord.Embed:
    premium_info = db.get_premium_info(guild_id) if guild_id else {
        "plan_key": "free",
        "plan_name": "무료",
        "is_premium": False,
    }

    current_plan = premium_info.get("plan_name", "무료")

    embed = discord.Embed(
        title="💿 명령어 / 프리미엄 소개",
        description=(
            "스크림봇 명령어와 패키지형 프리미엄 안내입니다.\n"
            f"현재 서버 패키지: **{current_plan}**"
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🆓 무료 기본 기능",
        value=(
            "**서버 설정**\n"
            "`/설정역할` ` /설정카테고리` ` /설정팀결과채널` ` /설정로그채널` ` /설정보기`\n\n"
            "**내전 운영**\n"
            "`/내전생성` ` /내전상태` ` /밸런스팀` ` /내전종료`\n\n"
            "**배그 모집**\n"
            "PUBG 배틀로얄 모집형, 솔로/듀오/스쿼드 규칙, 파티 시스템, 예약 시간 자동 진행\n\n"
            "**기본 프로필 기능**\n"
            "`/발로티어등록` ` /옵치티어등록` ` /롤티어등록`"
        ),
        inline=False
    )

    embed.add_field(
        name="⭐ 패키지형 프리미엄",
        value=(
            "**서포터**\n"
            "`/맵뽑기` ` /시즌확인` ` /시즌목록` ` /시즌랭킹`\n"
            "웹 상세 전적 페이지 / 시즌 페이지 조회 가능\n\n"
            "**프로**\n"
            "서포터 기능 포함\n"
            "`/결과기록` ` /시즌생성` ` /시즌종료`\n\n"
            "**클랜**\n"
            "프로 기능 포함\n"
            "반복 예약 / 시작 전 알림 / 운영 로그 / 웹 브랜딩 / 공지 템플릿 / 웹 공지 미리보기"
        ),
        inline=False
    )

    embed.add_field(
        name="📦 패키지 빠른 정리",
        value=(
            "무료: 기본 모집 / 기본 팀분배 / 배그 파티 / 티어등록\n"
            "서포터: 맵뽑기 / 시즌 조회 / 웹 상세 전적\n"
            "프로: 결과기록 / 시즌 생성·종료\n"
            "클랜: 프로 포함 + 반복 예약 + 공지 자동화 + 웹 브랜딩"
        ),
        inline=False
    )

    embed.set_footer(text="후원 및 패키지 신청은 지원 사이트에서 진행할 수 있습니다.")
    return embed


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="스크림봇 명령어와 패키지형 프리미엄 안내를 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):
        embed = build_help_embed(interaction.guild_id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="명령어", description="스크림봇 명령어와 패키지형 프리미엄 안내를 확인합니다.")
    async def command_guide(self, interaction: discord.Interaction):
        embed = build_help_embed(interaction.guild_id)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="프리미엄소개", description="패키지형 프리미엄 구성을 확인합니다.")
    async def premium_guide(self, interaction: discord.Interaction):
        embed = build_help_embed(interaction.guild_id)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
