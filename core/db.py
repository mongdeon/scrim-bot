import sqlite3


class DB:
    def __init__(self):
        self.conn = sqlite3.connect("scrim.db", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create()

    def create(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS guild_settings(
            guild_id INTEGER PRIMARY KEY,
            role_id INTEGER,
            category_id INTEGER
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS lobbies(
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            host_id INTEGER,
            game TEXT,
            team_size INTEGER,
            status TEXT,
            message_id INTEGER,
            waiting_voice_id INTEGER,
            team_a_voice_id INTEGER,
            team_b_voice_id INTEGER
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS lobby_players(
            channel_id INTEGER,
            user_id INTEGER,
            display_name TEXT,
            mmr INTEGER,
            position TEXT,
            PRIMARY KEY(channel_id, user_id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS team_members(
            channel_id INTEGER,
            team_name TEXT,
            user_id INTEGER,
            PRIMARY KEY(channel_id, team_name, user_id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS players(
            guild_id INTEGER,
            user_id INTEGER,
            mmr INTEGER DEFAULT 1000,
            win INTEGER DEFAULT 0,
            lose INTEGER DEFAULT 0,
            PRIMARY KEY(guild_id, user_id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS matches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            channel_id INTEGER,
            game TEXT,
            winner_team TEXT,
            team_a_avg INTEGER,
            team_b_avg INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        self.conn.commit()

    # ---------------- guild settings ----------------
    def set_role(self, guild_id, role_id):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO guild_settings(guild_id, role_id)
        VALUES(?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET role_id=excluded.role_id
        """, (guild_id, role_id))
        self.conn.commit()

    def set_category(self, guild_id, category_id):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO guild_settings(guild_id, category_id)
        VALUES(?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET category_id=excluded.category_id
        """, (guild_id, category_id))
        self.conn.commit()

    def get_settings(self, guild_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM guild_settings WHERE guild_id=?", (guild_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    # ---------------- lobby ----------------
    def create_lobby(self, channel_id, guild_id, host_id, game, team_size):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO lobbies(
            channel_id, guild_id, host_id, game, team_size, status,
            message_id, waiting_voice_id, team_a_voice_id, team_b_voice_id
        )
        VALUES(?, ?, ?, ?, ?, 'open', NULL, NULL, NULL, NULL)
        """, (channel_id, guild_id, host_id, game, team_size))
        self.conn.commit()

    def get_lobby(self, channel_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM lobbies WHERE channel_id=?", (channel_id,))
        row = cur.fetchone()
        return dict(row) if row else None

    def set_lobby_message(self, channel_id, message_id):
        cur = self.conn.cursor()
        cur.execute("UPDATE lobbies SET message_id=? WHERE channel_id=?", (message_id, channel_id))
        self.conn.commit()

    def set_lobby_status(self, channel_id, status):
        cur = self.conn.cursor()
        cur.execute("UPDATE lobbies SET status=? WHERE channel_id=?", (status, channel_id))
        self.conn.commit()

    def set_voice_channels(self, channel_id, waiting_id, team_a_id, team_b_id):
        cur = self.conn.cursor()
        cur.execute("""
        UPDATE lobbies
        SET waiting_voice_id=?, team_a_voice_id=?, team_b_voice_id=?
        WHERE channel_id=?
        """, (waiting_id, team_a_id, team_b_id, channel_id))
        self.conn.commit()

    def delete_lobby(self, channel_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM lobby_players WHERE channel_id=?", (channel_id,))
        cur.execute("DELETE FROM team_members WHERE channel_id=?", (channel_id,))
        cur.execute("DELETE FROM lobbies WHERE channel_id=?", (channel_id,))
        self.conn.commit()

    # ---------------- lobby players ----------------
    def add_lobby_player(self, channel_id, user_id, display_name, mmr, position):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO lobby_players(channel_id, user_id, display_name, mmr, position)
        VALUES(?, ?, ?, ?, ?)
        """, (channel_id, user_id, display_name, mmr, position))
        self.conn.commit()

    def remove_lobby_player(self, channel_id, user_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM lobby_players WHERE channel_id=? AND user_id=?", (channel_id, user_id))
        self.conn.commit()

    def get_lobby_players(self, channel_id):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM lobby_players
        WHERE channel_id=?
        ORDER BY mmr DESC, user_id ASC
        """, (channel_id,))
        return [dict(row) for row in cur.fetchall()]

    def has_lobby_player(self, channel_id, user_id):
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM lobby_players WHERE channel_id=? AND user_id=?", (channel_id, user_id))
        return cur.fetchone() is not None

    # ---------------- teams ----------------
    def clear_teams(self, channel_id):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM team_members WHERE channel_id=?", (channel_id,))
        self.conn.commit()

    def add_team_member(self, channel_id, team_name, user_id):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO team_members(channel_id, team_name, user_id)
        VALUES(?, ?, ?)
        """, (channel_id, team_name, user_id))
        self.conn.commit()

    def get_team_members(self, channel_id, team_name):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT user_id FROM team_members
        WHERE channel_id=? AND team_name=?
        ORDER BY user_id ASC
        """, (channel_id, team_name))
        return [row["user_id"] for row in cur.fetchall()]

    # ---------------- persistent player mmr ----------------
    def ensure_player(self, guild_id, user_id, mmr=1000):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT OR IGNORE INTO players(guild_id, user_id, mmr, win, lose)
        VALUES(?, ?, ?, 0, 0)
        """, (guild_id, user_id, mmr))
        self.conn.commit()

    def set_player_mmr(self, guild_id, user_id, mmr):
        self.ensure_player(guild_id, user_id, mmr)
        cur = self.conn.cursor()
        cur.execute("""
        UPDATE players
        SET mmr=?
        WHERE guild_id=? AND user_id=?
        """, (mmr, guild_id, user_id))
        self.conn.commit()

    def apply_match_result(self, guild_id, winners, losers, winner_delta, loser_delta):
        cur = self.conn.cursor()

        for user_id in winners:
            self.ensure_player(guild_id, user_id)
            cur.execute("""
            UPDATE players
            SET mmr = CASE WHEN mmr + ? < 100 THEN 100 ELSE mmr + ? END,
                win = win + 1
            WHERE guild_id=? AND user_id=?
            """, (winner_delta, winner_delta, guild_id, user_id))

        for user_id in losers:
            self.ensure_player(guild_id, user_id)
            cur.execute("""
            UPDATE players
            SET mmr = CASE WHEN mmr + ? < 100 THEN 100 ELSE mmr + ? END,
                lose = lose + 1
            WHERE guild_id=? AND user_id=?
            """, (loser_delta, loser_delta, guild_id, user_id))

        self.conn.commit()

    def get_player(self, guild_id, user_id):
        self.ensure_player(guild_id, user_id)
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM players
        WHERE guild_id=? AND user_id=?
        """, (guild_id, user_id))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_ranking(self, guild_id, limit=10):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT *,
               CASE
                   WHEN (win + lose) = 0 THEN 0
                   ELSE ROUND((CAST(win AS REAL) / (win + lose)) * 100, 1)
               END AS winrate
        FROM players
        WHERE guild_id=?
        ORDER BY mmr DESC, winrate DESC, win DESC
        LIMIT ?
        """, (guild_id, limit))
        return [dict(row) for row in cur.fetchall()]

    # ---------------- matches ----------------
    def add_match(self, guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg):
        cur = self.conn.cursor()
        cur.execute("""
        INSERT INTO matches(guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg)
        VALUES(?, ?, ?, ?, ?, ?)
        """, (guild_id, channel_id, game, winner_team, team_a_avg, team_b_avg))
        self.conn.commit()

    def get_recent_matches(self, guild_id, limit=10):
        cur = self.conn.cursor()
        cur.execute("""
        SELECT * FROM matches
        WHERE guild_id=?
        ORDER BY id DESC
        LIMIT ?
        """, (guild_id, limit))
        return [dict(row) for row in cur.fetchall()]