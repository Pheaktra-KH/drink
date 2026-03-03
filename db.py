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

        # Search table for full‑text search
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tips_search (
                tip_id TEXT PRIMARY KEY REFERENCES tips(id) ON DELETE CASCADE,
                tsv tsvector
            )
        ''')
        
        # Create a trigger to update tips_search when tips changes
        await conn.execute('''
            CREATE OR REPLACE FUNCTION tips_search_update() RETURNS trigger AS $$
            BEGIN
                -- Insert or update the search row with tsvector built from tip and its category
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
        
        await conn.execute('''
            DROP TRIGGER IF EXISTS search_trigger ON tips;
            CREATE TRIGGER search_trigger AFTER INSERT OR UPDATE
            ON tips FOR EACH ROW EXECUTE FUNCTION tips_search_update();
        ''')
        
        # Populate initial data
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

        
        # Index on category_id for faster joins
        await conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_tips_category_id
            ON tips (category_id)
        ''')

        # Add tsvector column for full‑text search
        await conn.execute('''
            ALTER TABLE tips ADD COLUMN IF NOT EXISTS tsv tsvector
        ''')
        
        # Create or replace the trigger function
        await conn.execute('''
            CREATE OR REPLACE FUNCTION tips_tsv_trigger() RETURNS trigger AS $$
            begin
                new.tsv :=
                    setweight(to_tsvector('english', coalesce(new.title,'')), 'A') ||
                    setweight(to_tsvector('english', coalesce(new.category,'')), 'B') ||
                    setweight(to_tsvector('english', coalesce(new.subcategory,'')), 'B') ||
                    setweight(to_tsvector('english', coalesce(
                        (SELECT string_agg(value->>'ingredient', ' ') FROM jsonb_array_elements(new.ingredients)), ''
                    )), 'C');
                return new;
            end
            $$ LANGUAGE plpgsql;
        ''')
        
        # Create trigger (if not exists)
        await conn.execute('''
            DROP TRIGGER IF EXISTS tsvector_update ON tips;
            CREATE TRIGGER tsvector_update BEFORE INSERT OR UPDATE
            ON tips FOR EACH ROW EXECUTE FUNCTION tips_tsv_trigger();
        ''')
        
        # Update existing rows to populate tsv
        await conn.execute('''
            UPDATE tips SET tsv = NULL  -- trigger will fill it
        ''')

        print("Database tables and indexes verified/created.")
    finally:
        await conn.close()

async def migrate_data(data: dict):
    """Insert initial tip data into database if tables are empty."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check if categories already exist
        count = await conn.fetchval('SELECT COUNT(*) FROM categories')
        if count > 0:
            print("Data already migrated, skipping.")
            return

        # Insert categories and tips
        for category_name, subcats in data.items():   # category_name: 'drink' or 'bakery'
            for subcat_name, tips_list in subcats.items():
                # Insert category
                cat_id = await conn.fetchval('''
                    INSERT INTO categories (category, subcategory)
                    VALUES ($1, $2)
                    RETURNING id
                ''', category_name, subcat_name)

                # Insert each tip
                for tip in tips_list:
                    # Convert ingredients and steps to JSON
                    ingredients_json = json.dumps(tip.get("ingredients", []))
                    steps_json = json.dumps(tip.get("steps", []))

                    await conn.execute('''
                        INSERT INTO tips (
                            id, category_id, title,
                            ingredients, steps,
                            picture_file_id, video_url
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ''',
                        tip["id"],
                        cat_id,
                        tip["title"],
                        ingredients_json,
                        steps_json,
                        tip.get("picture_file_id", ""),
                        tip.get("video_url", "")
                    )
        print("Initial data migrated to database.")
    finally:
        await conn.close()
