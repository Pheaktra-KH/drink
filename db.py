import asyncpg
import os
import json  # for storing ingredients as JSON

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

        # user_languages table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_languages (
                user_id BIGINT PRIMARY KEY,
                language_code TEXT NOT NULL
            )
        ''')

        # NEW: categories table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,      -- 'drink' or 'bakery'
                subcategory TEXT NOT NULL,
                UNIQUE(category, subcategory)
            )
        ''')

        # NEW: tips table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tips (
                id TEXT PRIMARY KEY,          -- e.g., 'drink/cafe/iced_latte'
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                ingredients JSONB NOT NULL,   -- store the ingredients array as JSON
                steps JSONB NOT NULL,         -- store steps array as JSON
                picture_file_id TEXT,
                video_url TEXT
            )
        ''')
        # Index on category_id for faster joins
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_tips_category_id
            ON tips (category_id)
        ''')

        print("Database tables and indexes verified/created.")
    finally:
        await conn.close()
