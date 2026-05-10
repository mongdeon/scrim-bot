import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from core.db import DB

db = DB()

# 기존에 있던 옵션 값들
GAME_OPTIONS = [
    app_commands.Choice(name="VALORANT", value="valorant"),
    app_commands.Choice(name="League of Legends", value="lol"),
    app_commands.Choice(name="PUBG", value="pubg"),
    app_commands.Choice(name="Overwatch 2", value="overwatch"),
]

class RecruitModal(discord.ui.Modal):
    """내전 생성을 위한 직관적인 팝업창 (Modal) UI"""
    def __init__(self, game_name: str, game_value: str, cog: commands.Cog):
        # 유저가 선택한 게임 이름이 팝업창 제목에 나타납니다.
        super().__init__(title=f"🎮 {game_name} 내전 생성")
        self.game_value = game_value
        self.cog = cog

    # 1. 시간 입력칸 (필수 해제 - 생략 시 현재 시간 적용)
    time_input = discord.ui.TextInput(
        label="⏰ 시작 시간 (생략 시 '지금'으로 자동 설정)",
        style=discord.TextStyle.short,
        placeholder="예: 20:00 (입력하지 않고 바로 넘어가도 됩니다!)",
        required=False
    )
    
    # 2. 메모 입력칸 (생략 가능)
    memo_input = discord.ui.TextInput(
        label="📝 내전 설명 또는 규칙 (선택)",
        style=discord.TextStyle.paragraph,
        placeholder="디코 마이크 필수, 즐겜 위주 등 (생략 가능)",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        """팝업창에서 '제출'을 눌렀을 때 실행되는 로직"""
        time_str = self.time_input.value.strip()
        memo_str = self.memo_input.value.strip() or "특별한 규칙 없음"
        
        # 시간을 비워두면 파이썬의 datetime을 사용해 현재 시간을 할당합니다.
        if not time_str:
            target_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            target_time = time_str

        # TODO: 여기에 기존 db.create_lobby 등 데이터베이스 연동 및 임베드 생성 로직이 들어갑니다.
        # 예시로 모집 완료 메시지를 띄웁니다.
        embed = discord.Embed(
            title=f"⚔️ {self.title} 모집 시작!",
            description=f"방장: {interaction.user.mention}\n\n**시작 시간:** {target_time}\n**설명:** {memo_str}",
            color=discord.Color.green()
        )
        embed.set_footer(text="버튼을 눌러 참가하세요!")
        
        await interaction.response.send_message(embed=embed)


class RecruitCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # 슬래시 명령어 자체에 Choices를 주어 사용자가 명령어를 칠 때 드롭다운 UI가 생성되게 유도합니다.
    @app_commands.command(name="내전생성", description="클릭 몇 번으로 간편하게 내전을 모집합니다.")
    @app_commands.choices(게임=GAME_OPTIONS)
    async def create_recruit(self, interaction: discord.Interaction, 게임: app_commands.Choice[str]):
        """명령어 입력 시 팝업창을 띄워줍니다."""
        # 선택한 게임 정보를 모달에 전달합니다.
        modal = RecruitModal(game_name=게임.name, game_value=게임.value, cog=self)
        await interaction.response.send_modal(modal)

async def setup(bot: commands.Bot):
    await bot.add_cog(RecruitCog(bot))