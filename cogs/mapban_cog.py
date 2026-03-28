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

# 오버워치 맵 풀은 여기서 쉽게 수정하면 됨
OVERWATCH_MAPS = [
    "부산",
    "일리오스",
    "리장 타워",
    "네팔",
    "오아시스",
    "남극 반도",
    "사모아",
    "도라도",
    "하바나",
    "정크타운",
    "리알토",
    "루트 66",
    "샴발리 수도원",
    "감시기지: 지브롤터",
    "블리자드 월드",
    "아이헨발데",
    "할리우드",
    "킹스 로우",
    "미드타운",
    "눔바니",
    "파라이소",
    "콜로세오",
    "뉴 퀸 스트리트",
    "에스페란사",
    "서킷 로얄",
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


class MapBan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.init_tables()

    def init_tables(self):
        db.execute("""
            CREATE TABLE IF NOT EXISTS map_ban_sessions (
                channel_id BIGINT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                game VARCHAR(50) NOT NULL,
                current_turn VARCHAR(1) NOT NULL DEFAULT 'A',
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                final_map VARCHAR(100),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS map_ban_entries (
                id BIGSERIAL PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                team VARCHAR(1) NOT NULL,
                map_name VARCHAR(100) NOT NULL,
                banned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
            SELECT channel_id, guild_id, game, current_turn, status, final_map, created_at
            FROM map_ban_sessions
            WHERE channel_id = %s
        """, (channel_id,))

    def _get_bans(self, channel_id: int):
        return db.fetchall("""
            SELECT id, channel_id, team, map_name, banned_at
            FROM map_ban_entries
            WHERE channel_id = %s
            ORDER BY id ASC
        """, (channel_id,))

    def _remaining_maps(self, game: str, bans: list[dict]) -> list[str]:
        pool = get_map_pool(game)
        banned = {row["map_name"] for row in bans}
        return [m for m in pool if m not in banned]

    def _build_status_embed(self, session: dict, bans: list[dict]) -> discord.Embed:
        remaining = self._remaining_maps(session["game"], bans)

        embed = discord.Embed(
            title=f"🗺️ {game_label(session['game'])} 맵밴 상태",
            color=discord.Color.orange() if session["status"] == "active" else discord.Color.green()
        )

        embed.add_field(name="상태", value=session["status"], inline=True)

        if session["status"] == "complete" and session["final_map"]:
            embed.add_field(name="최종 맵", value=session["final_map"], inline=True)
        else:
            embed.add_field(name="현재 차례", value=f"{session['current_turn']}팀", inline=True)

        embed.add_field(name="남은 맵 수", value=str(len(remaining)), inline=True)

        if bans:
            ban_lines = [f"{idx+1}. {row['team']}팀 밴 - {row['map_name']}" for idx, row in enumerate(bans)]
            embed.add_field(name="밴된 맵", value="\n".join(ban_lines[:25]), inline=False)
        else:
            embed.add_field(name="밴된 맵", value="아직 없음", inline=False)

        if remaining:
            embed.add_field(name="남은 맵", value=", ".join(remaining[:25]), inline=False)

        return embed

    @app_commands.command(name="맵밴생성", description="현재 로비 게임으로 맵밴을 생성합니다. (프리미엄)")
    async def create_map_ban(self, interaction: discord.Interaction):
        try:
            if not db.is_premium_guild(interaction.guild_id):
                await interaction.response.send_message("프리미엄 서버만 맵밴 기능을 사용할 수 있습니다.", ephemeral=True)
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
                    "맵밴은 현재 VALORANT / Overwatch 2 로비만 지원합니다.",
                    ephemeral=True
                )
                return

            pool = get_map_pool(lobby["game"])
            if not pool:
                await interaction.response.send_message("맵 풀이 비어 있습니다.", ephemeral=True)
                return

            db.execute("DELETE FROM map_ban_entries WHERE channel_id = %s", (interaction.channel_id,))
            db.execute("DELETE FROM map_ban_sessions WHERE channel_id = %s", (interaction.channel_id,))

            db.execute("""
                INSERT INTO map_ban_sessions (channel_id, guild_id, game, current_turn, status, final_map)
                VALUES (%s, %s, %s, 'A', 'active', NULL)
            """, (interaction.channel_id, interaction.guild_id, lobby["game"]))

            session = self._get_session(interaction.channel_id)
            bans = self._get_bans(interaction.channel_id)
            embed = self._build_status_embed(session, bans)

            await interaction.response.send_message(
                f"{game_label(lobby['game'])} 맵밴을 시작합니다. A팀부터 밴하세요.",
                embed=embed
            )

        except Exception as e:
            print("맵밴생성 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    async def map_autocomplete(self, interaction: discord.Interaction, current: str):
        lobby = db.get_lobby(interaction.channel_id)
        if not lobby:
            return []

        pool = get_map_pool(lobby["game"])
        if not pool:
            return []

        session = self._get_session(interaction.channel_id)
        bans = self._get_bans(interaction.channel_id) if session else []
        remaining = self._remaining_maps(lobby["game"], bans)

        result = []
        keyword = current.strip().lower()

        for name in remaining:
            if keyword in name.lower():
                result.append(app_commands.Choice(name=name, value=name))

        if not keyword:
            result = [app_commands.Choice(name=name, value=name) for name in remaining[:25]]

        return result[:25]

    @app_commands.command(name="맵밴", description="맵을 하나 밴합니다. (프리미엄)")
    @app_commands.describe(팀="현재 밴하는 팀", 맵="밴할 맵 이름")
    @app_commands.choices(팀=[
        app_commands.Choice(name="A팀", value="A"),
        app_commands.Choice(name="B팀", value="B"),
    ])
    @app_commands.autocomplete(맵=map_autocomplete)
    async def ban_map(
        self,
        interaction: discord.Interaction,
        팀: app_commands.Choice[str],
        맵: str
    ):
        try:
            if not db.is_premium_guild(interaction.guild_id):
                await interaction.response.send_message("프리미엄 서버만 맵밴 기능을 사용할 수 있습니다.", ephemeral=True)
                return

            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if not self._is_admin_or_host(interaction, lobby):
                await interaction.response.send_message("호스트 또는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return

            session = self._get_session(interaction.channel_id)
            if not session:
                await interaction.response.send_message("먼저 /맵밴생성 을 해주세요.", ephemeral=True)
                return

            if session["status"] != "active":
                await interaction.response.send_message("이미 맵밴이 완료되었습니다. /맵밴초기화 후 다시 시작하세요.", ephemeral=True)
                return

            if session["game"] != lobby["game"]:
                await interaction.response.send_message("현재 로비 게임과 맵밴 게임이 일치하지 않습니다.", ephemeral=True)
                return

            team_value = 팀.value
            if session["current_turn"] != team_value:
                await interaction.response.send_message(
                    f"지금은 {session['current_turn']}팀 차례입니다.",
                    ephemeral=True
                )
                return

            bans = self._get_bans(interaction.channel_id)
            remaining = self._remaining_maps(session["game"], bans)

            if 맵 not in remaining:
                await interaction.response.send_message("이미 밴되었거나 사용할 수 없는 맵입니다.", ephemeral=True)
                return

            db.execute("""
                INSERT INTO map_ban_entries (channel_id, team, map_name)
                VALUES (%s, %s, %s)
            """, (interaction.channel_id, team_value, 맵))

            bans = self._get_bans(interaction.channel_id)
            remaining = self._remaining_maps(session["game"], bans)

            if len(remaining) == 1:
                final_map = remaining[0]
                db.execute("""
                    UPDATE map_ban_sessions
                    SET status = 'complete',
                        final_map = %s
                    WHERE channel_id = %s
                """, (final_map, interaction.channel_id))

                session = self._get_session(interaction.channel_id)
                embed = self._build_status_embed(session, bans)

                await interaction.response.send_message(
                    f"✅ {team_value}팀이 **{맵}** 을(를) 밴했습니다.\n"
                    f"🎯 최종 맵은 **{final_map}** 입니다.",
                    embed=embed
                )
                return

            next_turn = "B" if team_value == "A" else "A"
            db.execute("""
                UPDATE map_ban_sessions
                SET current_turn = %s
                WHERE channel_id = %s
            """, (next_turn, interaction.channel_id))

            session = self._get_session(interaction.channel_id)
            embed = self._build_status_embed(session, bans)

            await interaction.response.send_message(
                f"✅ {team_value}팀이 **{맵}** 을(를) 밴했습니다.\n"
                f"이제 **{next_turn}팀** 차례입니다.",
                embed=embed
            )

        except Exception as e:
            print("맵밴 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="맵밴상태", description="현재 맵밴 상태를 확인합니다.")
    async def map_ban_status(self, interaction: discord.Interaction):
        try:
            session = self._get_session(interaction.channel_id)
            if not session:
                await interaction.response.send_message("현재 채널에 진행 중인 맵밴이 없습니다.", ephemeral=True)
                return

            bans = self._get_bans(interaction.channel_id)
            embed = self._build_status_embed(session, bans)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            print("맵밴상태 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)

    @app_commands.command(name="맵밴초기화", description="현재 채널의 맵밴을 초기화합니다.")
    async def reset_map_ban(self, interaction: discord.Interaction):
        try:
            lobby = db.get_lobby(interaction.channel_id)
            if not lobby:
                await interaction.response.send_message("이 채널에 로비가 없습니다.", ephemeral=True)
                return

            if not self._is_admin_or_host(interaction, lobby):
                await interaction.response.send_message("호스트 또는 관리자만 사용할 수 있습니다.", ephemeral=True)
                return

            db.execute("DELETE FROM map_ban_entries WHERE channel_id = %s", (interaction.channel_id,))
            db.execute("DELETE FROM map_ban_sessions WHERE channel_id = %s", (interaction.channel_id,))

            await interaction.response.send_message("현재 채널의 맵밴이 초기화되었습니다.", ephemeral=True)

        except Exception as e:
            print("맵밴초기화 오류:", e)
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {e}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MapBan(bot))