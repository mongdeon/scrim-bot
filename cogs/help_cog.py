import discord
from discord.ext import commands
from discord import app_commands
from core.db import DB

# DB 인스턴스 생성
db = DB()

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # 웹 전적 대시보드 연결 버튼
        self.add_item(discord.ui.Button(
            label="전적 사이트 확인", 
            url="https://elegant-cooperation-production-03d5.up.railway.app/", 
            style=discord.ButtonStyle.link,
            emoji="🌐"
        ))
        # 프리미엄 패키지 안내 및 후원 버튼
        self.add_item(discord.ui.Button(
            label="프리미엄 패키지 안내", 
            url="https://elegant-cooperation-production-03d5.up.railway.app/support", 
            style=discord.ButtonStyle.link,
            emoji="⭐"
        ))

class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _current_plan_name(self, guild_id: int | None) -> str:
        """현재 서버의 프리미엄 패키지 명칭을 가져옵니다."""
        if not guild_id:
            return "무료"
        info = db.get_premium_info(guild_id)
        return info.get("plan_name", "무료")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """봇이 서버에 추가되었을 때 관리자에게 초기 가이드를 전송합니다."""
        target_channel = guild.system_channel
        if target_channel is None or not target_channel.permissions_for(guild.me).send_messages:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        if target_channel:
            embed = discord.Embed(
                title="👋 스크림봇을 초대해주셔서 감사합니다!",
                description=(
                    f"**{guild.name}** 서버의 공정한 내전을 돕겠습니다.\n"
                    "아래 순서대로 설정을 완료하면 바로 내전을 시작할 수 있습니다."
                ),
                color=discord.Color.blurple()
            )
            embed.add_field(
                name="1️⃣ 관리자 설정 (필수)",
                value="`/설정역할`, `/설정카테고리`, `/설정팀결과채널` 명령어로 환경을 만들어주세요.",
                inline=False
            )
            embed.add_field(
                name="2️⃣ 유저 티어 등록",
                value="서버원들이 `/발로티어등록` 또는 `/옵치티어등록`으로 실력을 등록하게 해주세요.",
                inline=False
            )
            embed.add_field(
                name="3️⃣ 내전 생성",
                value="`/내전생성`으로 모집하고, 인원이 차면 `/밸런스팀`으로 팀을 나눌 수 있습니다.",
                inline=False
            )
            embed.set_footer(text="상세 명령어는 '/도움말'을 입력해 확인하세요.")
            
            await target_channel.send(embed=embed, view=HelpView())

    @app_commands.command(name="도움말", description="스크림봇의 모든 명령어와 사용법을 확인합니다.")
    async def help_command(self, interaction: discord.Interaction):
        """카테고리별 명령어 가이드를 출력합니다."""
        current_plan = self._current_plan_name(interaction.guild_id)
        
        embed = discord.Embed(
            title="💿 스크림봇 가이드",
            description=f"현재 서버 패키지 상태: **{current_plan}**\n상세 전적은 하단 버튼의 웹사이트에서 확인 가능합니다.",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🛠️ 서버 설정 (운영진)",
            value="`/설정역할`, `/설정카테고리`, `/설정팀결과채널`, `/설정공지채널`",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ 내전 운영",
            value="`/내전생성`, `/내전상태`, `/밸런스팀`, `/결과기록`, `/내전종료`",
            inline=False
        )

        embed.add_field(
            name="👤 유저 명령어",
            value="`/발로티어등록`, `/옵치티어등록`, `/롤티어등록`, `/내전전적`",
            inline=False
        )

        embed.add_field(
            name="💎 프리미엄 기능",
            value="`/맵뽑기`, `/시즌확인`, `/시즌랭킹`, `/상세전적안내`",
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))