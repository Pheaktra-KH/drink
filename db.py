import asyncpg
import os
import json

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
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_favorites_tip_id
            ON user_favorites (tip_id)
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
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_languages_language_code
            ON user_languages (language_code)
        ''')

        # categories table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                UNIQUE(category, subcategory)
            )
        ''')

        # --- Add display_order column if not exists ---
        await conn.execute('''
            ALTER TABLE categories ADD COLUMN IF NOT EXISTS display_order INTEGER DEFAULT 0;
        ''')

        # Now create the index that uses display_order
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_categories_order
            ON categories (category, display_order, subcategory);
        ''')

        # tips table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tips (
                id TEXT PRIMARY KEY,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                ingredients JSONB NOT NULL,
                steps JSONB NOT NULL,
                picture_file_id TEXT,
                video_url TEXT
            )
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_tips_category_id
            ON tips (category_id)
        ''')

        # tips_search table for full‑text search
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tips_search (
                tip_id TEXT PRIMARY KEY REFERENCES tips(id) ON DELETE CASCADE,
                tsv tsvector
            )
        ''')

        # Function to update tips_search when tips change
        await conn.execute('''
            CREATE OR REPLACE FUNCTION tips_search_update() RETURNS trigger AS $$
            BEGIN
                INSERT INTO tips_search (tip_id, tsv)
                SELECT NEW.id,
                       setweight(to_tsvector('english', coalesce(NEW.title,'')), 'A') ||
                       setweight(to_tsvector('english', coalesce(c.category,'')), 'B') ||
                       setweight(to_tsvector('english', coalesce(c.subcategory,'')), 'B') ||
                       setweight(to_tsvector('english', coalesce(
                           (SELECT string_agg(value->>'ingredient', ' ') FROM jsonb_array_elements(NEW.ingredients)), ''
                       )), 'C')
                FROM categories c WHERE c.id = NEW.category_id
                ON CONFLICT (tip_id) DO UPDATE SET tsv = EXCLUDED.tsv;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        ''')

        # user_views table for tracking user tip views
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_views (
                user_id BIGINT,
                tip_id TEXT,
                viewed_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (user_id, tip_id)
            )
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_views_user_id
            ON user_views (user_id)
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_views_tip_id
            ON user_views (tip_id)
        ''')
        
        # Trigger on tips
        await conn.execute('''
            DROP TRIGGER IF EXISTS search_trigger ON tips;
            CREATE TRIGGER search_trigger AFTER INSERT OR UPDATE
            ON tips FOR EACH ROW EXECUTE FUNCTION tips_search_update();
        ''')

        # Add timestamp columns to existing tables (if not exist)
        await conn.execute('''
            ALTER TABLE tips ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
            ALTER TABLE tips ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
        ''')
        await conn.execute('''
            ALTER TABLE categories ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
            ALTER TABLE categories ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
        ''')
        await conn.execute('''
            ALTER TABLE user_favorites ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
        ''')
        await conn.execute('''
            ALTER TABLE user_languages ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
        ''')

        # Initial population of tips_search (after ensuring all tables exist)
        await conn.execute('''
            INSERT INTO tips_search (tip_id, tsv)
            SELECT t.id,
                   setweight(to_tsvector('english', coalesce(t.title,'')), 'A') ||
                   setweight(to_tsvector('english', coalesce(c.category,'')), 'B') ||
                   setweight(to_tsvector('english', coalesce(c.subcategory,'')), 'B') ||
                   setweight(to_tsvector('english', coalesce(
                       (SELECT string_agg(value->>'ingredient', ' ') FROM jsonb_array_elements(t.ingredients)), ''
                   )), 'C')
            FROM tips t
            JOIN categories c ON t.category_id = c.id
            ON CONFLICT (tip_id) DO NOTHING;
        ''')

        # GIN index for full‑text search
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_tips_search_tsv ON tips_search USING GIN (tsv);')

        # Composite indexes for common queries
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_favorites_user_created
            ON user_favorites (user_id, created_at);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_views_user_viewed
            ON user_views (user_id, viewed_at);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_views_viewed_at
            ON user_views (viewed_at);
        ''')

        # User activity log table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS user_activity_log (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                action TEXT NOT NULL,
                tip_id TEXT,
                search_query TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_activity_user_id
            ON user_activity_log (user_id);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_activity_created
            ON user_activity_log (created_at);
        ''')
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_activity_action
            ON user_activity_log (action);
        ''')

        print("Database tables, indexes, timestamp columns, and new analytics table verified/created.")
    finally:
        await conn.close()

async def migrate_data(data: dict):
    """Insert initial tip data into database if tables are empty."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        count = await conn.fetchval('SELECT COUNT(*) FROM categories')
        if count > 0:
            print("Data already migrated, skipping.")
            return

        for category_name, subcats in data.items():
            order = 0
            for subcat_name, tips_list in subcats.items():
                cat_id = await conn.fetchval('''
                    INSERT INTO categories (category, subcategory, display_order, created_at, updated_at)
                    VALUES ($1, $2, $3, NOW(), NOW())
                    RETURNING id
                ''', category_name, subcat_name, order)
                order += 1

                for tip in tips_list:
                    ingredients_json = json.dumps(tip.get("ingredients", []))
                    steps_json = json.dumps(tip.get("steps", []))

                    await conn.execute('''
                        INSERT INTO tips (
                            id, category_id, title,
                            ingredients, steps,
                            picture_file_id, video_url,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ''',
                        tip["id"],
                        cat_id,
                        tip["title"],
                        ingredients_json,
                        steps_json,
                        tip.get("picture_file_id", ""),
                        tip.get("video_url", "")
                    )
        print("Initial data migrated to database (with timestamps and order).")
    finally:
        await conn.close()
