import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()


PLAN_LABELS = {
    "free": "무료",
    "supporter": "서포터",
    "pro": "프로",
    "clan": "클랜",
}

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

LOL_TIER_SCORES = {
    "아이언4": 100, "아이언3": 150, "아이언2": 200, "아이언1": 250,
    "브론즈4": 300, "브론즈3": 350, "브론즈2": 400, "브론즈1": 450,
    "실버4": 500, "실버3": 550, "실버2": 600, "실버1": 650,
    "골드4": 700, "골드3": 750, "골드2": 800, "골드1": 850,
    "플래티넘4": 900, "플래티넘3": 950, "플래티넘2": 1000, "플래티넘1": 1050,
    "에메랄드4": 1100, "에메랄드3": 1150, "에메랄드2": 1200, "에메랄드1": 1250,
    "다이아4": 1300, "다이아3": 1350, "다이아2": 1400, "다이아1": 1450,
    "마스터": 1550,
    "그랜드마스터": 1700,
    "챌린저": 1900,
}

OVERWATCH_ROLES = [
    app_commands.Choice(name="돌격", value="돌격"),
    app_commands.Choice(name="딜러", value="딜러"),
    app_commands.Choice(name="지원", value="지원"),
]


class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _current_plan_label(self, guild_id: int) -> str:
        info = db.get_premium_info(guild_id)
        return info.get("plan_name") or PLAN_LABELS.get(info.get("plan_key", "free"), "무료")

    def _apply_tier(self, guild_id: int, user_id: int, display_name: str, game: str, mmr: int):
        db.ensure_player(guild_id, user_id, 1000, display_name)
        db.ensure_player_game(guild_id, user_id, game, 1000, display_name)
        db.execute("UPDATE players SET mmr=%s, display_name=COALESCE(%s, display_name) WHERE guild_id=%s AND user_id=%s", (mmr, display_name, guild_id, user_id))
        db.execute("UPDATE player_game_stats SET mmr=%s, display_name=COALESCE(%s, display_name) WHERE guild_id=%s AND user_id=%s AND game=%s", (mmr, display_name, guild_id, user_id, game))

    def _recalc_overwatch_general_mmr(self, guild_id: int, user_id: int, display_name: str):
        role_mmrs = db.get_all_overwatch_role_mmr(guild_id, user_id)
        if not role_mmrs:
            return None
        avg_mmr = round(sum(role_mmrs.values()) / len(role_mmrs))
        self._apply_tier(guild_id, user_id, display_name, "overwatch", avg_mmr)
        return avg_mmr

    def _build_tier_embed(self, title: str, description: str, scores: dict[str, int]) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())
        lines = [f"**{tier}** : `{score}`" for tier, score in scores.items()]
        chunk=[]
        chunks=[]
        for line in lines:
            if sum(len(x)+1 for x in chunk)+len(line)>900:
                chunks.append("\n".join(chunk)); chunk=[line]
            else:
                chunk.append(line)
        if chunk: chunks.append("\n".join(chunk))
        for idx,text in enumerate(chunks, start=1):
            embed.add_field(name="티어 점수표" if idx==1 else f"티어 점수표 {idx}", value=text, inline=False)
        embed.set_footer(text="점수표 메세지는 서버 전체에 공개됩니다.")
        return embed

    @app_commands.command(name="발로티어점수표", description="발로란트 티어 점수표를 보여줍니다.")
    async def valorant_tier_table(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_tier_embed("🎯 발로란트 티어 점수표", "발로란트 티어별 MMR 기준표입니다.", VALORANT_TIER_SCORES))

    @app_commands.command(name="발로티어등록", description="발로란트 티어를 등록하고 MMR로 반영합니다.")
    async def valorant_tier_register(self, interaction: discord.Interaction, 티어: str):
        tier = 티어.strip()
        if tier not in VALORANT_TIER_SCORES:
            await interaction.response.send_message("올바른 발로란트 티어를 입력해주세요.", ephemeral=True)
            return
        mmr = VALORANT_TIER_SCORES[tier]
        self._apply_tier(interaction.guild_id, interaction.user.id, interaction.user.display_name, "valorant", mmr)
        await interaction.response.send_message(f"{interaction.user.mention} 발로란트 티어 등록 완료\n티어: **{tier}**\nMMR: **{mmr}**", ephemeral=True)

    @app_commands.command(name="옵치티어점수표", description="오버워치 티어 점수표를 보여줍니다.")
    async def overwatch_tier_table(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_tier_embed("🛡️ 오버워치 티어 점수표", "오버워치 티어별 MMR 기준표입니다.", OVERWATCH_TIER_SCORES))

    @app_commands.command(name="옵치티어등록", description="오버워치 역할군별 티어를 등록하고 MMR로 반영합니다.")
    @app_commands.describe(역할군="돌격 / 딜러 / 지원", 티어="예: 골드1")
    @app_commands.choices(역할군=OVERWATCH_ROLES)
    async def overwatch_tier_register(self, interaction: discord.Interaction, 역할군: app_commands.Choice[str], 티어: str):
        tier = 티어.strip()
        if tier not in OVERWATCH_TIER_SCORES:
            await interaction.response.send_message("올바른 오버워치 티어를 입력해주세요.", ephemeral=True)
            return
        mmr = OVERWATCH_TIER_SCORES[tier]
        db.set_overwatch_role_mmr(interaction.guild_id, interaction.user.id, 역할군.value, mmr, interaction.user.display_name)
        avg_mmr = self._recalc_overwatch_general_mmr(interaction.guild_id, interaction.user.id, interaction.user.display_name)
        await interaction.response.send_message(
            f"{interaction.user.mention} 오버워치 역할군 티어 등록 완료\n역할군: **{역할군.value}**\n티어: **{tier}**\n역할군 MMR: **{mmr}**\n평균 MMR: **{avg_mmr}**",
            ephemeral=True,
        )

    @app_commands.command(name="옵치역할mmr", description="내 오버워치 역할군별 MMR을 확인합니다.")
    async def overwatch_role_mmr(self, interaction: discord.Interaction):
        data = db.get_all_overwatch_role_mmr(interaction.guild_id, interaction.user.id)
        if not data:
            await interaction.response.send_message("등록된 오버워치 역할군별 MMR이 없습니다.", ephemeral=True)
            return
        embed = discord.Embed(title="🛡️ 오버워치 역할군별 MMR", color=discord.Color.blue())
        for role, mmr in data.items():
            embed.add_field(name=role, value=str(mmr), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="롤티어점수표", description="롤 티어 점수표를 보여줍니다.")
    async def lol_tier_table(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=self._build_tier_embed("🧠 롤 티어 점수표", "리그 오브 레전드 티어별 MMR 기준표입니다.", LOL_TIER_SCORES))

    @app_commands.command(name="롤티어등록", description="롤 티어를 등록하고 MMR로 반영합니다.")
    async def lol_tier_register(self, interaction: discord.Interaction, 티어: str):
        tier = 티어.strip()
        if tier not in LOL_TIER_SCORES:
            await interaction.response.send_message("올바른 롤 티어를 입력해주세요.", ephemeral=True)
            return
        mmr = LOL_TIER_SCORES[tier]
        self._apply_tier(interaction.guild_id, interaction.user.id, interaction.user.display_name, "lol", mmr)
        await interaction.response.send_message(f"{interaction.user.mention} 롤 티어 등록 완료\n티어: **{tier}**\nMMR: **{mmr}**", ephemeral=True)

    @app_commands.command(name="상세전적안내", description="상세 전적/시즌 페이지 패키지 조건을 안내합니다.")
    async def premium_profile_guide(self, interaction: discord.Interaction):
        current_name = self._current_plan_label(interaction.guild_id)
        await interaction.response.send_message(
            "웹사이트 패키지 안내\n"
            f"- 현재 서버 패키지: **{current_name}**\n"
            "- 상세 전적 페이지: **서포터 이상**\n"
            "- 시즌 페이지: **서포터 이상**\n"
            "- 시즌 생성/종료: **프로 이상**\n"
            "- 결과기록 / ELO 반영: **프로 이상**",
            ephemeral=True,
        )


async def setup(bot):
    await bot.add_cog(Profile(bot))
