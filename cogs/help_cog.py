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
            description="사용 가능한 명령어와 배그 파티 시스템 설명입니다.",
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
            name="📢 일반 내전",
            value=(
                "`/내전생성` → 내전 모집 시작\n"
                "`/내전상태` → 모집 상태 확인\n"
                "`/밸런스팀` → 자동 팀 분배\n"
                "`/내전종료` → 내전 종료 및 정리"
            ),
            inline=False
        )

        embed.add_field(
            name="🔥 배그 배틀로얄",
            value=(
                "`/내전생성 게임:PUBG 배그형식:솔로`\n"
                "`/내전생성 게임:PUBG 배그형식:듀오`\n"
                "`/내전생성 게임:PUBG 배그형식:스쿼드`\n\n"
                "- 솔로: 8명 개인 참가\n"
                "- 듀오: 8명, 2인 파티 필요\n"
                "- 스쿼드: 16명, 4인 파티 필요"
            ),
            inline=False
        )

        embed.add_field(
            name="👥 배그 파티 시스템",
            value=(
                "`/파티생성` → 현재 배그 듀오/스쿼드 로비에서 파티 생성\n"
                "`/파티참가 파티코드:XXXXXX` → 파티 코드로 참가\n"
                "`/파티나가기` → 현재 파티에서 나가기\n"
                "`/파티상태` → 현재 파티 목록 확인\n\n"
                "배그 듀오/스쿼드는 파티를 완성한 뒤 각자 `참가` 버튼으로 로비에 들어가면 됩니다."
            ),
            inline=False
        )

        embed.add_field(
            name="⚔️ 결과 기록 / ELO",
            value=(
                "`/결과기록` → 승패 기록 + ELO 반영\n"
                "`/랭킹` → 서버 ELO 랭킹\n"
                "`/내전전적` → 내 전적 확인\n"
                "`/최근전적` → 최근 경기\n\n"
                "※ 현재 `/결과기록`은 팀전 게임 기준입니다.\n"
                "※ 배그 배틀로얄 모집형은 현재 ELO 결과기록 미지원"
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

        embed.set_footer(text="배그 듀오/스쿼드는 실제 파티 단위로 참가할 수 있습니다.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))