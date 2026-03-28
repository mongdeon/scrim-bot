import random
import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB

db = DB()

VALORANT_MAPS = [
    "헤이븐",
    "스플릿",
    "어센트",
    "아이스박스",
    "바인드",
    "브리즈",
    "프랙처",
    "펄",
    "로터스",
    "선셋",
    "어비스",
    "코로드",
]

OVERWATCH_MAPS = [
    "66번국도",
    "감시 기지: 지브롤터",
    "도라도",
    "리알토",
    "샴발리 수도원",
    "서킷 로얄",
    "쓰레기촌",
    "하바나",
    "눔바니",
    "미드타운",
    "블리자드 월드",
    "아이헨발데",
    "왕의 길",
    "파라이수",
    "할리우드",
    "남극 반도",
    "네팔",
    "리장 타워",
    "사모아",
    "부산",
    "오아시스",
    "일리오스",
    "뉴 퀸 스트리트",
    "루나사피",
    "이스페란사",
    "콜로세오",
    "뉴 정크 시티",
    "수라바사",
    "아틀리스",
]


def game_label(game: str) -> str:
    return {
        "valorant": "VALORANT",
        "overwatch": "Overwatch 2",
    }.get(game, game)


def get_map_pool(game: str) -> list[str]:
    if game == "valorant":
        return VALORANT_MAPS[:]
    if game == "overwatch":
        return OVERWATCH_MAPS[:]
    return []


class MapPick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_tables()

    def init_tables(self):
        db.execute("""
            CREATE TABLE IF NOT EXISTS map_pick_sessions (
                channel_id BIGINT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                selected_map VARCHAR(100),
                status VARCHAR(20) NOT NULL DEFAULT 'ready',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def _is_admin_or_host(self, interaction: discord.Interaction, lobby: dict | None) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if lobby and interaction.user.id == lobby["host_id"]:
            return True
        return False

    def _get_session(self, channel_id: int):
        return db.fetchone("""
            SELECT
                channel_id,
                guild_id,
                game,
                selected_map,
                status,
                created_at,
                updated_at
            FROM map_pick_sessions
            WHERE channel_id = %s
        """, (channel_id,))

    def _build_embed(self, session: dict, pool: list[str]) -> discord.Embed:
        color = discord.Color.green() if session.get("selected_map") else discord.Color.blurple()

        embed = discord.Embed(
            title=f"🗺️ {game_label(session['game'])} 맵 뽑기",
            color=color
        )

        embed.add_field(name="상태", value=session["status"], inline=True)
        embed.add_field(name="맵 수", value=str(len(pool)), inline=True)

        if session.get("selected_map"):
            embed.add_field(name="선택된 맵", value=session["selected_map"], inline=False)
        else:
            embed.add_field(name="선택된 맵", value="아직 없음", inline=False)

        embed.add_field(
            name="맵 풀",
            value=", ".join(pool[:25]) if pool else "없음",
            inline=False
        )

        return embed

    @app_commands.command(name="맵뽑기", description="현재 로비 게임 기준으로 맵을 랜덤 뽑기합니다. (프리미엄)")
    async def pick_map(self, interaction: discord.Interaction):
        try:
            if not db.is_premium_guild(interaction.guild_id):
                await interaction.response.send_message("프리미엄 서버만 맵 뽑기 기능을 사용할 수 있습니다.", ephemeral=True)
                return

            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if not self._is_admin_or_host(interaction, lobby):
                await interaction.response.send_message("호스트 또는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return

            if lobby["game"] not in ["valorant", "overwatch"]:
                await interaction.response.send_message(
                    "맵 뽑기는 현재 VALORANT / Overwatch 2 로비만 지원합니다.",
                    ephemeral=True
                )
                return

            pool = get_map_pool(lobby["game"])
            if not pool:
                await interaction.response.send_message("맵 풀이 비어 있습니다.", ephemeral=True)
                return

            selected_map = random.choice(pool)

            existing = self._get_session(interaction.channel_id)
            if existing:
                db.execute("""
                    UPDATE map_pick_sessions
                    SET
                        guild_id = %s,
                        game = %s,
                        selected_map = %s,
                        status = 'picked',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE channel_id = %s
                """, (
                    interaction.guild_id,
                    lobby["game"],
                    selected_map,
                    interaction.channel_id
                ))
            else:
                db.execute("""
                    INSERT INTO map_pick_sessions (
                        channel_id,
                        guild_id,
                        game,
                        selected_map,
                        status
                    )
                    VALUES (%s, %s, %s, %s, 'picked')
                """, (
                    interaction.channel_id,
                    interaction.guild_id,
                    lobby["game"],
                    selected_map
                ))

            session = self._get_session(interaction.channel_id)
            embed = self._build_embed(session, pool)

            await interaction.response.send_message(
                f"🎯 랜덤 맵이 선택되었습니다: **{selected_map}**",
                embed=embed
            )

        except Exception as e:
            print("맵뽑기 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="맵뽑기상태", description="현재 채널의 맵 뽑기 결과를 확인합니다.")
    async def map_pick_status(self, interaction: discord.Interaction):
        try:
            session = self._get_session(interaction.channel_id)
            if not session:
                await interaction.response.send_message("현재 채널에 저장된 맵 뽑기 결과가 없습니다.", ephemeral=True)
                return

            pool = get_map_pool(session["game"])
            embed = self._build_embed(session, pool)

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print("맵뽑기상태 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="맵뽑기초기화", description="현재 채널의 맵 뽑기 결과를 초기화합니다.")
    async def reset_map_pick(self, interaction: discord.Interaction):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if not self._is_admin_or_host(interaction, lobby):
                await interaction.response.send_message("호스트 또는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return

            db.execute("DELETE FROM map_pick_sessions WHERE channel_id = %s", (interaction.channel_id,))

            await interaction.response.send_message("현재 채널의 맵 뽑기 결과가 초기화되었습니다.", ephemeral=True)

        except Exception as e:
            print("맵뽑기초기화 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MapPick(bot))