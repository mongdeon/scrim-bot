import os
import json
import asyncio
import asyncpg
from datetime import datetime, timedelta

# 전역 커넥션 풀 (DB 연결 유지)
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL")
        
        if not db_url:
            print("❌ DATABASE_URL 환경 변수가 없습니다. Railway 설정을 확인하세요.")
            return None

        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        try:
            _pool = await asyncpg.create_pool(db_url)
            await _create_tables()
            print("✅ PostgreSQL 데이터베이스 연결 및 테이블 셋업 완료!")
        except Exception as e:
            print(f"❌ DB 연결 실패: {e}")
            
    return _pool

async def _create_tables():
    pool = await get_pool()
    if not pool:
        return
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS guilds (
                id BIGINT PRIMARY KEY,
                data JSONB NOT NULL DEFAULT '{}'::jsonb
            );
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                data JSONB NOT NULL DEFAULT '{}'::jsonb
            );
        ''')

async def get_guild_data(guild_id: int) -> dict:
    pool = await get_pool()
    if not pool: 
        return {}
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT data FROM guilds WHERE id = $1', guild_id)
        if row and row['data']:
            data = json.loads(row['data'])
            data['_id'] = guild_id
            return data
        return {'_id': guild_id}

async def update_guild_data(guild_id: int, data: dict):
    pool = await get_pool()
    if not pool: 
        return
    
    if '_id' in data:
        del data['_id']
        
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO guilds (id, data)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (id) DO UPDATE
            SET data = EXCLUDED.data;
        ''', guild_id, json.dumps(data))

async def get_user_data(user_id: int) -> dict:
    pool = await get_pool()
    if not pool: 
        return {}
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow('SELECT data FROM users WHERE id = $1', user_id)
        if row and row['data']:
            data = json.loads(row['data'])
            data['_id'] = user_id
            return data
        return {'_id': user_id}

async def update_user_data(user_id: int, data: dict):
    pool = await get_pool()
    if not pool: 
        return
    
    if '_id' in data:
        del data['_id']
        
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (id, data)
            VALUES ($1, $2::jsonb)
            ON CONFLICT (id) DO UPDATE
            SET data = EXCLUDED.data;
        ''', user_id, json.dumps(data))

async def set_premium_days(guild_id: int, days: int, plan_key: str):
    guild_data = await get_guild_data(guild_id)
    
    current_time = datetime.now()
    expire_time = current_time + timedelta(days=days)
    
    guild_data['premium_plan'] = plan_key
    guild_data['premium_expire'] = expire_time.isoformat()
    
    await update_guild_data(guild_id, guild_data)
    print(f"서버[{guild_id}] 프리미엄 부여 완료: {plan_key} (만료일: {expire_time})")
    return True