import discord
from discord.ext import commands
from discord import app_commands

class GuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 웹 대시보드로 바로 이동할 수 있는 버튼 추가
        # 실제 운영하시는 도메인으로 URL을 변경해주세요.
        self.add_item(discord.ui.Button(
            label="웹 대시보드 (전적 및 랭킹)", 
            url="https://your-domain.com/", 
            style=discord.ButtonStyle.link
        ))
        self.add_item(discord.ui.Button(
            label="프리미엄 후원 안내", 
            url="https://your-domain.com/support", 
            style=discord.ButtonStyle.link
        ))

class GuideCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """봇이 새로운 서버에 초대되었을 때 실행되는 이벤트"""
        # 메시지를 보낼 수 있는 첫 번째 텍스트 채널을 찾습니다.
        target_channel = guild.system_channel
        if target_channel is None or not target_channel.permissions_for(guild.me).send_messages:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        if target_channel:
            embed = discord.Embed(
                title="내전봇이 서버에 추가되었습니다!",
                description=(
                    "초대해 주셔서 감사합니다. 공정한 팀 분배와 전적 관리를 시작해 보세요.\n\n"
                    "**[초기 설정 방법]**\n"
                    "원활한 사용을 위해 관리자 분은 아래 명령어로 서버를 세팅해 주세요."
                ),
                color=0x2563eb # 브랜드 컬러 (파란색 계열)
            )
            embed.add_field(
                name="1. 기본 채널 설정",
                value="`/설정역할`, `/설정카테고리`, `/설정팀결과채널` 등을 통해 봇이 작동할 환경을 지정합니다.",
                inline=False
            )
            embed.add_field(
                name="2. 유저 티어 등록",
                value="서버원들은 `/옵치티어등록`, `/발로티어등록` 등으로 자신의 실력을 등록해야 밸런스가 맞춰집니다.",
                inline=False
            )
            embed.add_field(
                name="3. 내전 시작",
                value="`/내전생성` 명령어를 입력해 참가자를 모집하고 팀을 분배할 수 있습니다.",
                inline=False
            )
            embed.set_footer(text="자세한 내용은 '/도움말' 명령어를 입력해 확인하세요.")

            await target_channel.send(embed=embed, view=GuideView())

    @app_commands.command(name="도움말", description="내전봇의 사용 방법과 전체 명령어 목록을 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):
        """사용자가 언제든 호출할 수 있는 도움말 명령어"""
        embed = discord.Embed(
            title="내전봇 사용 가이드",
            description="아래 카테고리별 명령어를 확인하시고, 상세 전적은 웹사이트에서 확인하세요.",
            color=0x2563eb
        )
        
        embed.add_field(
            name="운영 명령어",
            value="`/내전생성` : 새로운 내전을 시작합니다.\n"
                  "`/내전상태` : 현재 진행 중인 내전 정보를 봅니다.\n"
                  "`/밸런스팀` : 등록된 티어를 기반으로 공평하게 팀을 나눕니다.\n"
                  "`/내전종료` : 게임 결과를 기록하고 MMR을 갱신합니다.",
            inline=False
        )
        
        embed.add_field(
            name="유저 명령어",
            value="`/발로티어등록` / `/옵치티어등록` : 게임별 티어를 등록합니다.\n"
                  "`/발로티어점수표` : 티어별 환산 MMR을 확인합니다.",
            inline=False
        )
        
        embed.add_field(
            name="프리미엄 (서포터 이상)",
            value="`/맵뽑기` : 무작위로 맵을 추첨합니다.\n"
                  "`/시즌확인` / `/시즌랭킹` : 서버의 시즌 전적을 조회합니다.",
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=GuideView(), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GuideCog(bot))