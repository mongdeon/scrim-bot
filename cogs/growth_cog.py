import discord
from discord.ext import commands
from discord import app_commands

BOT_INVITE_URL = "여기에_봇_초대링크_넣기"
SUPPORT_SERVER_URL = "여기에_지원서버_링크_넣기"
WEBSITE_URL = "여기에_전적사이트_링크_넣기"


class GrowthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="초대", description="봇 초대 링크를 보여줍니다.")
    async def invite(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📨 봇 초대",
            description="아래 버튼으로 다른 서버에도 봇을 초대할 수 있어요.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="초대 링크", value=BOT_INVITE_URL, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="봇 초대하기",
                style=discord.ButtonStyle.link,
                url=BOT_INVITE_URL
            )
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="지원서버", description="지원 서버 링크를 보여줍니다.")
    async def support_server(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛟 지원 서버",
            description="문의, 버그 제보, 업데이트 소식은 지원 서버에서 확인할 수 있어요.",
            color=discord.Color.green()
        )
        embed.add_field(name="지원 서버 링크", value=SUPPORT_SERVER_URL, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="지원 서버 들어가기",
                style=discord.ButtonStyle.link,
                url=SUPPORT_SERVER_URL
            )
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="소개", description="봇 소개를 보여줍니다.")
    async def intro(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎮 내전봇 소개",
            description="내전 모집부터 팀 분배, ELO, 전적 웹사이트까지 지원하는 디스코드 내전봇입니다.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="주요 기능",
            value=(
                "• 자동 내전 모집 메시지\n"
                "• 버튼 참가 / 포지션 / MMR 입력\n"
                "• 자동 팀 분배\n"
                "• 자동 음성 채널 이동\n"
                "• ELO 랭킹\n"
                "• 전적 웹사이트"
            ),
            inline=False
        )
        embed.add_field(name="전적 사이트", value=WEBSITE_URL, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="전적 사이트 열기",
                style=discord.ButtonStyle.link,
                url=WEBSITE_URL
            )
        )
        view.add_item(
            discord.ui.Button(
                label="봇 초대하기",
                style=discord.ButtonStyle.link,
                url=BOT_INVITE_URL
            )
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        owner = guild.owner
        if owner is None:
            return

        embed = discord.Embed(
            title="👋 내전봇을 추가해주셔서 감사합니다!",
            description="빠르게 시작하려면 아래 순서대로 해주세요.",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="빠른 시작",
            value=(
                "1. `/설정역할`\n"
                "2. `/설정카테고리`\n"
                "3. `/내전생성`\n"
                "4. `/도움말`\n"
                "5. `/사이트`"
            ),
            inline=False
        )
        embed.add_field(name="전적 사이트", value=WEBSITE_URL, inline=False)
        embed.add_field(name="지원 서버", value=SUPPORT_SERVER_URL, inline=False)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="지원 서버",
                style=discord.ButtonStyle.link,
                url=SUPPORT_SERVER_URL
            )
        )
        view.add_item(
            discord.ui.Button(
                label="전적 사이트",
                style=discord.ButtonStyle.link,
                url=WEBSITE_URL
            )
        )

        try:
            await owner.send(embed=embed, view=view)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(GrowthCog(bot))