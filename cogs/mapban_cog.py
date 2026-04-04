import random
import discord
from discord.ext import commands
from discord import app_commands

from core.db import DB
from cogs.recruit_cog import build_lobby_list_embed

PLAN_LABELS = {"free": "무료", "supporter": "서포터", "pro": "프로", "clan": "클랜"}

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

    def _current_plan_label(self, guild_id: int) -> str:
        info = db.get_premium_info(guild_id)
        return info.get("plan_name") or PLAN_LABELS.get(info.get("plan_key", "free"), "무료")

    def _has_supporter_or_higher(self, guild_id: int) -> bool:
        return db.has_premium_plan(guild_id, "supporter")

    def init_tables(self):
        db.execute("""
            CREATE TABLE IF NOT EXISTS scrim_map_pick_sessions (
                lobby_id BIGINT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                selected_map VARCHAR(100),
                status VARCHAR(20) NOT NULL DEFAULT 'ready',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS map_pick_history (
                id BIGSERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                channel_id BIGINT NOT NULL,
                selected_map VARCHAR(100) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("ALTER TABLE map_pick_history ADD COLUMN IF NOT EXISTS lobby_id BIGINT")

    def _is_admin_or_host(self, interaction: discord.Interaction, lobby: dict | None) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if lobby and interaction.user.id == lobby["host_id"]:
            return True
        return False

    def _get_session(self, lobby_id: int):
        return db.fetchone("""
            SELECT
                lobby_id,
                guild_id,
                channel_id,
                game,
                selected_map,
                status,
                created_at,
                updated_at
            FROM scrim_map_pick_sessions
            WHERE lobby_id = %s
        """, (lobby_id,))

    def _upsert_session(self, lobby: dict, selected_map: str | None, status: str):
        existing = self._get_session(lobby["lobby_id"])
        if existing:
            db.execute("""
                UPDATE scrim_map_pick_sessions
                SET
                    guild_id = %s,
                    channel_id = %s,
                    game = %s,
                    selected_map = %s,
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE lobby_id = %s
            """, (
                lobby["guild_id"],
                lobby["channel_id"],
                lobby["game"],
                selected_map,
                status,
                lobby["lobby_id"],
            ))
        else:
            db.execute("""
                INSERT INTO scrim_map_pick_sessions (
                    lobby_id,
                    guild_id,
                    channel_id,
                    game,
                    selected_map,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                lobby["lobby_id"],
                lobby["guild_id"],
                lobby["channel_id"],
                lobby["game"],
                selected_map,
                status,
            ))

    def _get_last_picked_map(self, guild_id: int, game: str):
        row = db.fetchone("""
            SELECT selected_map, created_at
            FROM map_pick_history
            WHERE guild_id = %s AND game = %s
            ORDER BY id DESC
            LIMIT 1
        """, (guild_id, game))
        return row

    def _pick_random_map(self, guild_id: int, game: str) -> tuple[str, str | None]:
        pool = get_map_pool(game)
        if not pool:
            raise ValueError("맵 풀이 비어 있습니다.")

        last_row = self._get_last_picked_map(guild_id, game)
        blocked_map = last_row["selected_map"] if last_row else None

        candidate_pool = [m for m in pool if m != blocked_map] if blocked_map else pool[:]
        if not candidate_pool:
            candidate_pool = pool[:]

        selected = random.choice(candidate_pool)
        return selected, blocked_map

    def _build_embed(self, lobby: dict, session: dict, pool: list[str], blocked_map: str | None = None) -> discord.Embed:
        color = discord.Color.green() if session.get("selected_map") else discord.Color.blurple()

        embed = discord.Embed(
            title=f"🗺️ {game_label(session['game'])} 맵 뽑기",
            color=color,
        )
        embed.add_field(name="로비 ID", value=str(lobby["lobby_id"]), inline=True)
        embed.add_field(name="상태", value=session["status"], inline=True)
        embed.add_field(name="채널", value=f"<#{lobby['channel_id']}>", inline=True)

        if session.get("selected_map"):
            embed.add_field(name="선택된 맵", value=session["selected_map"], inline=False)
        else:
            embed.add_field(name="선택된 맵", value="아직 없음", inline=False)

        if blocked_map:
            embed.add_field(name="연속 방지 제외 맵", value=blocked_map, inline=False)

        embed.add_field(
            name="맵 풀",
            value=", ".join(pool[:25]) if pool else "없음",
            inline=False,
        )
        return embed

    async def resolve_lobby(self, interaction: discord.Interaction, lobby_id: int | None):
        if lobby_id is not None:
            lobby = db.get_lobby_by_id(lobby_id)
            if not lobby:
                await interaction.response.send_message("해당 로비 ID를 찾을 수 없습니다.", ephemeral=True)
                return None
            if lobby["guild_id"] != interaction.guild_id or lobby["channel_id"] != interaction.channel_id:
                await interaction.response.send_message("해당 로비는 현재 채널의 로비가 아닙니다.", ephemeral=True)
                return None
            return lobby

        lobbies = db.get_channel_lobbies(interaction.channel_id, guild_id=interaction.guild_id, active_only=True)
        if not lobbies:
            lobbies = db.get_channel_lobbies(interaction.channel_id, guild_id=interaction.guild_id, active_only=False)

        if not lobbies:
            await interaction.response.send_message("현재 채널에 로비가 없습니다.", ephemeral=True)
            return None

        if len(lobbies) == 1:
            return lobbies[0]

        if isinstance(interaction.channel, discord.TextChannel):
            embed = build_lobby_list_embed(interaction.channel, lobbies)
            await interaction.response.send_message(
                content="같은 채널에 여러 로비가 있습니다. `로비ID`를 함께 입력해주세요.",
                embed=embed,
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "같은 채널에 여러 로비가 있습니다. `로비ID`를 함께 입력해주세요.",
                ephemeral=True,
            )
        return None

    @app_commands.command(name="맵뽑기", description="현재 로비 게임 기준으로 맵을 랜덤 뽑기합니다. (프리미엄)")
    @app_commands.describe(로비ID="맵을 뽑을 로비 ID")
    async def pick_map(self, interaction: discord.Interaction, 로비ID: int | None = None):
        try:
            if not self._has_supporter_or_higher(interaction.guild_id):
                current_name = self._current_plan_label(interaction.guild_id)
                await interaction.response.send_message(
                    f"맵 뽑기 기능은 **서포터 패키지 이상**에서 사용할 수 있습니다.\n현재 서버 패키지: **{current_name}**",
                    ephemeral=True,
                )
                return

            lobby = await self.resolve_lobby(interaction, 로비ID)
            if not lobby:
                return

            if not self._is_admin_or_host(interaction, lobby):
                await interaction.response.send_message("호스트 또는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return

            if lobby["game"] not in ["valorant", "overwatch"]:
                await interaction.response.send_message(
                    "맵 뽑기는 현재 VALORANT / Overwatch 2 로비만 지원합니다.",
                    ephemeral=True,
                )
                return

            pool = get_map_pool(lobby["game"])
            selected_map, blocked_map = self._pick_random_map(interaction.guild_id, lobby["game"])
            self._upsert_session(lobby, selected_map, "picked")

            db.execute("""
                INSERT INTO map_pick_history (guild_id, game, channel_id, lobby_id, selected_map)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                interaction.guild_id,
                lobby["game"],
                lobby["channel_id"],
                lobby["lobby_id"],
                selected_map,
            ))

            session = self._get_session(lobby["lobby_id"])
            embed = self._build_embed(lobby, session, pool, blocked_map)

            if blocked_map:
                text = (
                    f"🎯 랜덤 맵이 선택되었습니다: **{selected_map}**\n"
                    f"로비 ID: **{lobby['lobby_id']}**\n"
                    f"(직전 맵 **{blocked_map}** 은 연속 방지를 위해 제외됨)"
                )
            else:
                text = (
                    f"🎯 랜덤 맵이 선택되었습니다: **{selected_map}**\n"
                    f"로비 ID: **{lobby['lobby_id']}**"
                )

            await interaction.response.send_message(text, embed=embed)

        except Exception as e:
            print("맵뽑기 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="맵뽑기상태", description="현재 로비의 맵 뽑기 결과를 확인합니다.")
    @app_commands.describe(로비ID="확인할 로비 ID")
    async def map_pick_status(self, interaction: discord.Interaction, 로비ID: int | None = None):
        try:
            lobby = await self.resolve_lobby(interaction, 로비ID)
            if not lobby:
                return

            session = self._get_session(lobby["lobby_id"])
            if not session:
                await interaction.response.send_message("해당 로비에 저장된 맵 뽑기 결과가 없습니다.", ephemeral=True)
                return

            pool = get_map_pool(session["game"])
            last_row = self._get_last_picked_map(session["guild_id"], session["game"])
            blocked_map = last_row["selected_map"] if last_row else None

            embed = self._build_embed(lobby, session, pool, blocked_map)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print("맵뽑기상태 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="맵뽑기초기화", description="현재 로비의 맵 뽑기 결과를 초기화합니다.")
    @app_commands.describe(로비ID="초기화할 로비 ID")
    async def reset_map_pick(self, interaction: discord.Interaction, 로비ID: int | None = None):
        try:
            lobby = await self.resolve_lobby(interaction, 로비ID)
            if not lobby:
                return

            if not self._is_admin_or_host(interaction, lobby):
                await interaction.response.send_message("호스트 또는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return

            db.execute("DELETE FROM scrim_map_pick_sessions WHERE lobby_id = %s", (lobby["lobby_id"],))
            db.execute("DELETE FROM map_pick_sessions WHERE channel_id = %s", (lobby["channel_id"],))

            await interaction.response.send_message(
                f"로비 ID **{lobby['lobby_id']}** 의 맵 뽑기 결과가 초기화되었습니다.",
                ephemeral=True,
            )

        except Exception as e:
            print("맵뽑기초기화 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MapPick(bot))
