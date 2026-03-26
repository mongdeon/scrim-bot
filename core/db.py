import psycopg2
from psycopg2.extras import RealDictCursor

from core.config import DATABASE_URL


class DB:
    def __init__(self):
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다.")

        self.conn = psycopg2.connect(DATABASE_URL)
        self.conn.autocommit = True
        self.create()

    def create(self):
        with self.conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS guild_settings(
                guild_id BIGINT PRIMARY KEY,
                role_id BIGINT,
                category_id BIGINT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS premium_guilds(
                guild_id BIGINT PRIMARY KEY,
                is_premium BOOLEAN DEFAULT FALSE
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS lobbies(
                channel_id BIGINT PRIMARY KEY,
                guild_id BIGINT,
                host_id BIGINT,
                game TEXT,
                team_size INT,
                status TEXT,
                message_id BIGINT,
                waiting_voice_id BIGINT,
                team_a_voice_id BIGINT,
                team_b_voice_id BIGINT
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS lobby_players(
                channel_id BIGINT,
                user_id BIGINT,
                display_name TEXT,
                mmr INT,
                position TEXT,
                PRIMARY KEY(channel_id, user_id)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS team_members(
                channel_id BIGINT,
                team_name TEXT,
                user_id BIGINT,
                PRIMARY KEY(channel_id, team_name, user_id)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS players(
                guild_id BIGINT,
                user_id BIGINT,
                display_name TEXT,
                mmr INT DEFAULT 1000,
                win INT DEFAULT 0,
                lose INT DEFAULT 0,
                PRIMARY KEY(guild_id, user_id)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS player_game_stats(
                guild_id BIGINT,
                user_id BIGINT,
                game TEXT,
                display_name TEXT,
                mmr INT DEFAULT 1000,
                win INT DEFAULT 0,
                lose INT DEFAULT 0,
                PRIMARY KEY(guild_id, user_id, game)
            )
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS matches(
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                channel_id BIGINT,
                game TEXT,
                winner_team TEXT,
                team_a_avg INT,
                team_b_avg INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cur.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS display_name TEXT")
            cur.execute("ALTER TABLE player_game_stats ADD COLUMN IF NOT EXISTS display_name TEXT")

    # ---------------- premium ----------------
    def set_premium(self, guild_id, is_premium: bool):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO premium_guilds(guild_id, is_premium)
            VALUES(%s, %s)
            ON CONFLICT(guild_id)
            DO UPDATE SET is_premium=EXCLUDED.is_premium
            """, (guild_id, is_premium))

    def is_premium_guild(self, guild_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT is_premium FROM premium_guilds WHERE guild_id=%s", (guild_id,))
            row = cur.fetchone()
            return bool(row["is_premium"]) if row else False

    # ---------------- guild settings ----------------
    def set_role(self, guild_id, role_id):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO guild_settings(guild_id, role_id)
            VALUES(%s, %s)
            ON CONFLICT(guild_id)
            DO UPDATE SET role_id=EXCLUDED.role_id
            """, (guild_id, role_id))

    def set_category(self, guild_id, category_id):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO guild_settings(guild_id, category_id)
            VALUES(%s, %s)
            ON CONFLICT(guild_id)
            DO UPDATE SET category_id=EXCLUDED.category_id
            """, (guild_id, category_id))

    def get_settings(self, guild_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM guild_settings WHERE guild_id=%s", (guild_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    # ---------------- lobby ----------------
    def create_lobby(self, channel_id, guild_id, host_id, game, team_size):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO lobbies(
                channel_id, guild_id, host_id, game, team_size, status,
                message_id, waiting_voice_id, team_a_voice_id, team_b_voice_id
            )
            VALUES(%s, %s, %s, %s, %s, 'open', NULL, NULL, NULL, NULL)
            ON CONFLICT(channel_id)
            DO UPDATE SET
                guild_id=EXCLUDED.guild_id,
                host_id=EXCLUDED.host_id,
                game=EXCLUDED.game,
                team_size=EXCLUDED.team_size,
                status='open',
                message_id=NULL,
                waiting_voice_id=NULL,
                team_a_voice_id=NULL,
                team_b_voice_id=NULL
            """, (channel_id, guild_id, host_id, game, team_size))

    def get_lobby(self, channel_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM lobbies WHERE channel_id=%s", (channel_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def set_lobby_message(self, channel_id, message_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE lobbies SET message_id=%s WHERE channel_id=%s",
                (message_id, channel_id)
            )

    def set_lobby_status(self, channel_id, status):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE lobbies SET status=%s WHERE channel_id=%s",
                (status, channel_id)
            )

    def set_voice_channels(self, channel_id, waiting_id, team_a_id, team_b_id):
        with self.conn.cursor() as cur:
            cur.execute("""
            UPDATE lobbies
            SET waiting_voice_id=%s, team_a_voice_id=%s, team_b_voice_id=%s
            WHERE channel_id=%s
            """, (waiting_id, team_a_id, team_b_id, channel_id))

    def delete_lobby(self, channel_id):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM lobby_players WHERE channel_id=%s", (channel_id,))
            cur.execute("DELETE FROM team_members WHERE channel_id=%s", (channel_id,))
            cur.execute("DELETE FROM lobbies WHERE channel_id=%s", (channel_id,))

    # ---------------- lobby players ----------------
    def add_lobby_player(self, channel_id, user_id, display_name, mmr, position):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO lobby_players(channel_id, user_id, display_name, mmr, position)
            VALUES(%s, %s, %s, %s, %s)
            ON CONFLICT(channel_id, user_id)
            DO UPDATE SET
                display_name=EXCLUDED.display_name,
                mmr=EXCLUDED.mmr,
                position=EXCLUDED.position
            """, (channel_id, user_id, display_name, mmr, position))

    def remove_lobby_player(self, channel_id, user_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "DELETE FROM lobby_players WHERE channel_id=%s AND user_id=%s",
                (channel_id, user_id)
            )

    def get_lobby_players(self, channel_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT * FROM lobby_players
            WHERE channel_id=%s
            ORDER BY mmr DESC, user_id ASC
            """, (channel_id,))
            return [dict(row) for row in cur.fetchall()]

    def has_lobby_player(self, channel_id, user_id):
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM lobby_players WHERE channel_id=%s AND user_id=%s",
                (channel_id, user_id)
            )
            return cur.fetchone() is not None

    # ---------------- teams ----------------
    def clear_teams(self, channel_id):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM team_members WHERE channel_id=%s", (channel_id,))

    def add_team_member(self, channel_id, team_name, user_id):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO team_members(channel_id, team_name, user_id)
            VALUES(%s, %s, %s)
            ON CONFLICT(channel_id, team_name, user_id)
            DO NOTHING
            """, (channel_id, team_name, user_id))

    def get_team_members(self, channel_id, team_name):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT user_id FROM team_members
            WHERE channel_id=%s AND team_name=%s
            ORDER BY user_id ASC
            """, (channel_id, team_name))
            return [row["user_id"] for row in cur.fetchall()]

    # ---------------- global player stats ----------------
    def ensure_player(self, guild_id, user_id, mmr=1000, display_name=None):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO players(guild_id, user_id, display_name, mmr, win, lose)
            VALUES(%s, %s, %s, %s, 0, 0)
            ON CONFLICT(guild_id, user_id)
            DO NOTHING
            """, (guild_id, user_id, display_name, mmr))

            if display_name:
                cur.execute("""
                UPDATE players
                SET display_name=%s
                WHERE guild_id=%s AND user_id=%s
                """, (display_name, guild_id, user_id))

    def set_player_mmr(self, guild_id, user_id, mmr, display_name=None):
        self.ensure_player(guild_id, user_id, mmr, display_name)
        with self.conn.cursor() as cur:
            cur.execute("""
            UPDATE players
            SET mmr=%s,
                display_name=COALESCE(%s, display_name)
            WHERE guild_id=%s AND user_id=%s
            """, (mmr, display_name, guild_id, user_id))

    # ---------------- per-game stats ----------------
    def ensure_player_game(self, guild_id, user_id, game, mmr=1000, display_name=None):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO player_game_stats(guild_id, user_id, game, display_name, mmr, win, lose)
            VALUES(%s, %s, %s, %s, %s, 0, 0)
            ON CONFLICT(guild_id, user_id, game)
            DO NOTHING
            """, (guild_id, user_id, game, display_name, mmr))

            if display_name:
                cur.execute("""
                UPDATE player_game_stats
                SET display_name=%s
                WHERE guild_id=%s AND user_id=%s AND game=%s
                """, (display_name, guild_id, user_id, game))

    def set_player_game_mmr(self, guild_id, user_id, game, mmr, display_name=None):
        self.ensure_player_game(guild_id, user_id, game, mmr, display_name)
        with self.conn.cursor() as cur:
            cur.execute("""
            UPDATE player_game_stats
            SET mmr=%s,
                display_name=COALESCE(%s, display_name)
            WHERE guild_id=%s AND user_id=%s AND game=%s
            """, (mmr, display_name, guild_id, user_id, game))

    def apply_match_result(self, guild_id, game, winners, losers, winner_delta, loser_delta, name_map=None):
        name_map = name_map or {}

        with self.conn.cursor() as cur:
            for user_id in winners:
                display_name = name_map.get(user_id)
                self.ensure_player(guild_id, user_id, 1000, display_name)
                self.ensure_player_game(guild_id, user_id, game, 1000, display_name)

                cur.execute("""
                UPDATE players
                SET mmr = GREATEST(100, mmr + %s),
                    win = win + 1,
                    display_name = COALESCE(%s, display_name)
                WHERE guild_id=%s AND user_id=%s
                """, (winner_delta, display_name, guild_id, user_id))

                cur.execute("""
                UPDATE player_game_stats
                SET mmr = GREATEST(100, mmr + %s),
                    win = win + 1,
                    display_name = COALESCE(%s, display_name)
                WHERE guild_id=%s AND user_id=%s AND game=%s
                """, (winner_delta, display_name, guild_id, user_id, game))

            for user_id in losers:
                display_name = name_map.get(user_id)
                self.ensure_player(guild_id, user_id, 1000, display_name)
                self.ensure_player_game(guild_id, user_id, game, 1000, display_name)

                cur.execute("""
                UPDATE players
                SET mmr = GREATEST(100, mmr + %s),
                    lose = lose + 1,
                    display_name = COALESCE(%s, display_name)
                WHERE guild_id=%s AND user_id=%s
                """, (loser_delta, display_name, guild_id, user_id))

                cur.execute("""
                UPDATE player_game_stats
                SET mmr = GREATEST(100, mmr + %s),
                    lose = lose + 1,
                    display_name = COALESCE(%s, display_name)
                WHERE guild_id=%s AND user_id=%s AND game=%s
                """, (loser_delta, display_name, guild_id, user_id, game))

    def get_player(self, guild_id, user_id):
        self.ensure_player(guild_id, user_id)
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT * FROM players
            WHERE guild_id=%s AND user_id=%s
            """, (guild_id, user_id))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_ranking(self, guild_id, limit=10):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT *,
                   CASE
                       WHEN (win + lose) = 0 THEN 0
                       ELSE ROUND((CAST(win AS NUMERIC) / (win + lose)) * 100, 1)
                   END AS winrate
            FROM players
            WHERE guild_id=%s
            ORDER BY mmr DESC, winrate DESC, win DESC
            LIMIT %s
            """, (guild_id, limit))
            return [dict(row) for row in cur.fetchall()]

    # ---------------- matches ----------------
    def add_match(self, guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg):
        with self.conn.cursor() as cur:
            cur.execute("""
            INSERT INTO matches(guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg)
            VALUES(%s, %s, %s, %s, %s, %s)
            """, (guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg))

    def get_recent_matches(self, guild_id, limit=10):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
            SELECT * FROM matches
            WHERE guild_id=%s
            ORDER BY id DESC
            LIMIT %s
            """, (guild_id, limit))
            return [dict(row) for row in cur.fetchall()]