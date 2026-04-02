import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _current_plan_name(self, guild_id: int | None) -> str:
        if not guild_id:
            return "무료"
        info = db.get_premium_info(guild_id)
        return info.get("plan_name", "무료")

    def _build_embed(self, guild_id: int | None) -> discord.Embed:
        current_plan = self._current_plan_name(guild_id)

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
                "`/설정역할`, `/설정카테고리`, `/설정팀결과채널`, `/설정공지채널`, `/설정로그채널`, `/설정보기`\n\n"
                "**기본 내전 운영**\n"
                "`/내전생성`, `/내전상태`, `/밸런스팀`, `/내전종료`, 내전 시간 / 날짜 설정 가능\n\n"
                "**배그 모집**\n"
                "PUBG 배틀로얄 모집형, 솔로/듀오/스쿼드 규칙 지원\n\n"
                "**기본 프로필 기능**\n"
                "`/발로티어등록`, `/옵치티어등록`, `/롤티어등록`, `/발로티어점수표`, `/옵치티어점수표`, `/롤티어점수표`"
            ),
            inline=False
        )

        embed.add_field(
            name="⭐ 패키지형 프리미엄",
            value=(
                "**서포터 패키지 · 3,000원**\n"
                "`/맵뽑기`, `/시즌확인`, `/시즌목록`, `/시즌랭킹` 사용 가능\n"
                "웹 상세 전적 페이지와 시즌 페이지 조회 가능\n\n"
                "**프로 패키지 · 4,990원**\n"
                "서포터 기능 포함\n"
                "`/결과기록`, `/시즌생성`, `/시즌종료` 사용 가능\n\n"
                "**클랜 패키지 · 7,990원**\n"
                "프로 기능 포함\n"
                "반복 예약, 시작 전 알림, 운영 로그, 웹 브랜딩, 공지 템플릿, 독립 클랜 페이지 지원"
            ),
            inline=False
        )

        embed.add_field(
            name="📌 빠른 정리",
            value=(
                "무료: 기본 모집 / 기본 팀분배 / 티어등록\n"
                "서포터: 맵뽑기 / 시즌 조회 / 웹 상세 전적\n"
                "프로: 결과기록 / 시즌 생성·종료\n"
                "클랜: 프로 포함 + 반복 예약 + 공지 자동화 + 웹 브랜딩"
            ),
            inline=False
        )

        embed.set_footer(text="후원 및 패키지 신청은 지원 사이트에서 진행할 수 있습니다.")
        return embed

    @app_commands.command(name="도움말", description="스크림봇 명령어와 패키지형 프리미엄 안내를 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_embed(interaction.guild_id), ephemeral=True)

    @app_commands.command(name="명령어", description="스크림봇 명령어와 패키지형 프리미엄 안내를 확인합니다.")
    async def command_guide(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_embed(interaction.guild_id), ephemeral=True)

    @app_commands.command(name="프리미엄소개", description="패키지형 프리미엄 구성을 확인합니다.")
    async def premium_guide(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_embed(interaction.guild_id), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
