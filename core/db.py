import asyncpg
import os

class Database:

    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            os.getenv("DATABASE_URL")
        )

        await self.create_tables()

    async def create_tables(self):

        async with self.pool.acquire() as conn:

            await conn.execute("""

            CREATE TABLE IF NOT EXISTS guild_settings(
                guild_id BIGINT PRIMARY KEY,
                recruit_channel BIGINT,
                role_id BIGINT,
                category_id BIGINT
            );

            CREATE TABLE IF NOT EXISTS players(
                user_id BIGINT,
                guild_id BIGINT,
                mmr INT DEFAULT 1000,
                win INT DEFAULT 0,
                lose INT DEFAULT 0,
                PRIMARY KEY(user_id, guild_id)
            );

            CREATE TABLE IF NOT EXISTS matches(
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                game TEXT,
                team_a TEXT,
                team_b TEXT,
                winner TEXT,
                created TIMESTAMP DEFAULT NOW()
            );

            """)