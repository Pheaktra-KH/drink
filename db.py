import asyncpg
from main import DATABASE_URL  # or import from config

async def init_db():
    """Create the user_favorites table if it doesn't exist."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_favorites (
                user_id BIGINT,
                tip_id TEXT,
                PRIMARY KEY (user_id, tip_id)
            )
        ''')
    finally:
        await conn.close()
