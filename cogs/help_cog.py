import discord
from discord.ext import commands
from discord import app_commands


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="도움말", description="내전봇 명령어 목록과 패키지별 기능을 보여줍니다.")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 내전봇 도움말",
            description="사용 가능한 명령어와 패키지형 프리미엄 기능 안내입니다.",
            color=discord.Color.green()
        )

        embed.add_field(
            name="⚙️ 서버 설정 / 무료",
            value=(
                "`/설정역할` → 내전 참여 역할 설정\n"
                "`/설정카테고리` → 내전 생성 카테고리\n"
                "`/설정팀결과채널` → 자동 팀분배 결과 채널 설정\n"
                "`/설정보기` → 현재 설정 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="📢 내전 운영 / 무료",
            value=(
                "`/내전생성` → 내전 모집 시작\n"
                "`/내전상태` → 모집 상태 확인\n"
                "`/밸런스팀` → 기본 자동 팀 분배\n"
                "`/내전종료` → 내전 종료 및 정리"
            ),
            inline=False
        )

        embed.add_field(
            name="🔥 배그 배틀로얄 / 무료",
            value=(
                "`/내전생성 게임:PUBG 배그형식:솔로 모집인원:20`\n"
                "`/내전생성 게임:PUBG 배그형식:듀오 모집인원:10`\n"
                "`/내전생성 게임:PUBG 배그형식:스쿼드 모집인원:20`\n\n"
                "- 솔로 : 2 ~ 100\n"
                "- 듀오 : 4 ~ 100, 2의 배수\n"
                "- 스쿼드 : 8 ~ 100, 4의 배수"
            ),
            inline=False
        )

        embed.add_field(
            name="👥 배그 파티 시스템 / 무료",
            value=(
                "`/파티생성` → 현재 배그 듀오/스쿼드 로비에서 파티 생성\n"
                "`/파티참가 파티코드:XXXXXX` → 파티 코드로 참가\n"
                "`/파티나가기` → 현재 파티에서 나가기\n"
                "`/파티상태` → 현재 파티 목록 확인"
            ),
            inline=False
        )

        embed.add_field(
            name="🧾 프로필 / 무료",
            value=(
                "`/발로티어등록`, `/옵치티어등록`, `/롤티어등록`\n"
                "`/티어점수표`, `/옵치티어점수표`, `/롤티어점수표`"
            ),
            inline=False
        )

        embed.add_field(
            name="⭐ 서포터 패키지",
            value=(
                "`/맵뽑기`\n"
                "`/시즌확인`, `/시즌목록`, `/시즌랭킹`\n"
                "웹 상세 전적 페이지 / 웹 시즌 페이지 조회"
            ),
            inline=False
        )

        embed.add_field(
            name="💎 프로 패키지",
            value=(
                "서포터 기능 포함\n"
                "`/결과기록` → 승패 기록 + ELO 반영\n"
                "`/시즌생성`, `/시즌종료`"
            ),
            inline=False
        )

        embed.add_field(
            name="👑 클랜 패키지",
            value=(
                "프로 기능 포함\n"
                "서버 단위 확장 운영 / 상위 패키지 안내용 단계"
            ),
            inline=False
        )

        embed.add_field(
            name="💖 프리미엄 명령어",
            value=(
                "`/프리미엄확인`\n"
                "`/프리미엄추가` (오너)\n"
                "`/프리미엄끄기` (오너)"
            ),
            inline=False
        )

        embed.set_footer(text="무료 / 서포터 / 프로 / 클랜 패키지 기준으로 기능이 구분됩니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
