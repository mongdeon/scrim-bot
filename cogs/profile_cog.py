import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()

VALORANT_TIER_SCORES = {
    "아이언1": 100, "아이언2": 150, "아이언3": 200,
    "브론즈1": 250, "브론즈2": 300, "브론즈3": 350,
    "실버1": 400, "실버2": 450, "실버3": 500,
    "골드1": 550, "골드2": 600, "골드3": 650,
    "플래티넘1": 700, "플래티넘2": 750, "플래티넘3": 800,
    "다이아1": 850, "다이아2": 900, "다이아3": 950,
    "초월자1": 1000, "초월자2": 1050, "초월자3": 1100,
    "불멸1": 1150, "불멸2": 1200, "불멸3": 1250,
    "레디언트": 1350,
}

OVERWATCH_TIER_SCORES = {
    "브론즈5": 200, "브론즈4": 250, "브론즈3": 300, "브론즈2": 350, "브론즈1": 400,
    "실버5": 450, "실버4": 500, "실버3": 550, "실버2": 600, "실버1": 650,
    "골드5": 700, "골드4": 750, "골드3": 800, "골드2": 850, "골드1": 900,
    "플래티넘5": 950, "플래티넘4": 1000, "플래티넘3": 1050, "플래티넘2": 1100, "플래티넘1": 1150,
    "다이아5": 1200, "다이아4": 1250, "다이아3": 1300, "다이아2": 1350, "다이아1": 1400,
    "마스터5": 1450, "마스터4": 1500, "마스터3": 1550, "마스터2": 1600, "마스터1": 1650,
    "그랜드마스터5": 1700, "그랜드마스터4": 1750, "그랜드마스터3": 1800, "그랜드마스터2": 1850, "그랜드마스터1": 1900,
    "챔피언": 2000,
}


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="티어점수표", description="발로란트 티어 점수표를 보여줍니다.")
    async def tier_table(self, interaction: discord.Interaction):
        text = "\n".join([f"{k}: {v}" for k, v in VALORANT_TIER_SCORES.items()])
        await interaction.response.send_message(f"```{text}```", ephemeral=True)

    @app_commands.command(name="발로티어등록", description="발로란트 티어를 등록하고 MMR로 반영합니다.")
    async def valorant_tier_register(self, interaction: discord.Interaction, 티어: str):
        tier = 티어.strip()

        if tier not in VALORANT_TIER_SCORES:
            await interaction.response.send_message(
                "올바른 티어를 입력해주세요.\n"
                "예: 아이언1, 실버2, 골드3, 플래티넘1, 다이아2, 초월자3, 불멸1, 레디언트",
                ephemeral=True
            )
            return

        mmr = VALORANT_TIER_SCORES[tier]
        db.ensure_player(interaction.guild_id, interaction.user.id, mmr)
        db.set_player_mmr(interaction.guild_id, interaction.user.id, mmr)

        await interaction.response.send_message(
            f"{interaction.user.mention} 발로란트 티어 등록 완료\n"
            f"티어: **{tier}**\n"
            f"MMR: **{mmr}**",
            ephemeral=True
        )

    @app_commands.command(name="옵치티어점수표", description="오버워치 티어 점수표를 보여줍니다.")
    async def overwatch_tier_table(self, interaction: discord.Interaction):
        text = "\n".join([f"{k}: {v}" for k, v in OVERWATCH_TIER_SCORES.items()])
        await interaction.response.send_message(f"```{text}```", ephemeral=True)

    @app_commands.command(name="옵치티어등록", description="오버워치 티어를 등록하고 MMR로 반영합니다.")
    async def overwatch_tier_register(self, interaction: discord.Interaction, 티어: str):
        tier = 티어.strip()

        if tier not in OVERWATCH_TIER_SCORES:
            await interaction.response.send_message(
                "올바른 오버워치 티어를 입력해주세요.\n"
                "예: 브론즈5, 실버3, 골드1, 플래티넘2, 다이아4, 마스터1, 그랜드마스터3, 챔피언",
                ephemeral=True
            )
            return

        mmr = OVERWATCH_TIER_SCORES[tier]
        db.ensure_player(interaction.guild_id, interaction.user.id, mmr)
        db.set_player_mmr(interaction.guild_id, interaction.user.id, mmr)

        await interaction.response.send_message(
            f"{interaction.user.mention} 오버워치 티어 등록 완료\n"
            f"티어: **{tier}**\n"
            f"MMR: **{mmr}**",
            ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Profile(bot))