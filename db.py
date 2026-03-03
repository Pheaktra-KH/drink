import asyncpg
import os

DATABASE_URL = "postgresql://postgres:lXwGOXEmpDGGVOBFvrVDEbHtJvzwfdKA@nozomi.proxy.rlwy.net:22016/railway"

async def init_db():
    """Create tables and indexes if they don't exist."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # user_favorites table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_favorites (
                user_id BIGINT,
                tip_id TEXT,
                PRIMARY KEY (user_id, tip_id)
            )
        ''')
        # Index on user_id for faster lookups of a user's favorites
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_favorites_user_id
            ON user_favorites (user_id)
        ''')

        # tip_stats table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tip_stats (
                tip_id TEXT PRIMARY KEY,
                views INT DEFAULT 0,
                favorites INT DEFAULT 0,
                shares INT DEFAULT 0
            )
        ''')
        # Index on tip_id already exists as PRIMARY KEY, no extra needed.

        # user_languages table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_languages (
                user_id BIGINT PRIMARY KEY,
                language_code TEXT NOT NULL
            )
        ''')
        # Index on language_code? Not needed unless you query by language.

        # If you ever need to query by language_code, uncomment:
        # await conn.execute('''
        #     CREATE INDEX IF NOT EXISTS idx_user_languages_language_code
        #     ON user_languages (language_code)
        # ''')

        print("Database tables and indexes verified/created.")
    finally:
        await conn.close()
