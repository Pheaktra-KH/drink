import asyncpg
import os

DATABASE_URL = os.getenv("DATABASE_URL")

async def get_connection():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_connection()
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS user_favorites (
            user_id BIGINT NOT NULL,
            tip_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (user_id, tip_id)
        )
    ''')
    await conn.close()
