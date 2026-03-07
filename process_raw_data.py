import asyncio
import asyncpg
import json
import re
from typing import Dict, List, Any

DATABASE_URL = "postgresql://postgres:lXwGOXEmpDGGVOBFvrVDEbHtJvzwfdKA@nozomi.proxy.rlwy.net:22016/railway"

# Keywords to identify drink products (based on the "type" column)
DRINK_TYPE_KEYWORDS = {"Hot", "Ice", "Frappe", "Cold"}

def slugify(text: str) -> str:
    """Convert product name to a safe ID."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text

def extract_ingredient_name(desc: str) -> str:
    """Extract ingredient name from description (part before dash)."""
    if not desc:
        return ""
    parts = desc.split(" - ")
    if len(parts) > 1:
        first = parts[0].split(" ", 1)
        return first[1].strip() if len(first) > 1 else first[0].strip()
    first = desc.split(" ", 1)
    return first[1].strip() if len(first) > 1 else first[0].strip()

async def process_raw_data():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # ---- 1. Clear existing tip data (keep user languages) ----
        print("Truncating old tip data...")
        await conn.execute("TRUNCATE tips, tips_search, categories, subcategory_translations, tip_stats, user_favorites, user_views CASCADE")
        print("Done.")

        # ---- 2. Fetch all raw rows, grouped by product name ----
        rows = await conn.fetch('SELECT * FROM raw_data ORDER BY product_name, id')
        products: Dict[str, List[Dict]] = {}
        for r in rows:
            prod = r['product_name']
            products.setdefault(prod, []).append(dict(r))

        print(f"Found {len(products)} products in raw_data.")

        # ---- 3. Insert categories and tips ----
        category_cache = {}   # (main_cat, subcat) -> category_id
        tip_count = 0

        for prod_name, components in products.items():
            first = components[0]
            prod_type = first['type'] or ""

            # Determine main category
            if any(k in prod_type for k in DRINK_TYPE_KEYWORDS):
                main_cat = "drink"
            else:
                main_cat = "bakery"

            subcat = first['categories'] or "uncategorized"
            key = (main_cat, subcat)

            if key not in category_cache:
                # Insert category
                cat_id = await conn.fetchval("""
                    INSERT INTO categories (category, subcategory, created_at, updated_at)
                    VALUES ($1, $2, NOW(), NOW())
                    ON CONFLICT (category, subcategory) DO UPDATE SET updated_at = NOW()
                    RETURNING id
                """, main_cat, subcat)
                category_cache[key] = cat_id

                # Insert translations (same name for both languages)
                await conn.execute("""
                    INSERT INTO subcategory_translations (category_id, language_code, display_name)
                    VALUES ($1, 'en', $2), ($1, 'km', $3)
                    ON CONFLICT (category_id, language_code) DO NOTHING
                """, cat_id, subcat, subcat)

            cat_id = category_cache[key]

            # Build ingredients list
            ingredients = []
            for i, comp in enumerate(components, start=1):
                ing_name = extract_ingredient_name(comp['description'])
                if not ing_name:
                    ing_name = comp['commodity'] or "Ingredient"
                amount = comp['net_rating']
                uom = comp['uom'] or ""
                remark_parts = []
                if comp['commodity']:
                    remark_parts.append(f"Code: {comp['commodity']}")
                if comp['purchase_price'] is not None:
                    remark_parts.append(f"Price: {comp['purchase_price']}")
                if comp['cost'] is not None:
                    remark_parts.append(f"Cost: {comp['cost']}")
                if comp['total_cost'] is not None:
                    remark_parts.append(f"Total: {comp['total_cost']}")
                remark = " | ".join(remark_parts)

                ingredients.append({
                    "no": i,
                    "ingredient": ing_name,
                    "amount": amount if amount is not None else "",
                    "uom": uom,
                    "remark": remark
                })

            # Create steps – one per ingredient if amounts exist, else generic
            steps = [f"Add {ing['ingredient']} {ing['amount']}{ing['uom']}" for ing in ingredients if ing['amount']]
            if not steps:
                steps = ["Combine all ingredients as per standard recipe."]

            tip_id = slugify(prod_name)

            # Insert tip
            try:
                await conn.execute("""
                    INSERT INTO tips (
                        id, category_id, title, ingredients, steps,
                        picture_file_id, video_url, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        category_id = EXCLUDED.category_id,
                        title = EXCLUDED.title,
                        ingredients = EXCLUDED.ingredients,
                        steps = EXCLUDED.steps,
                        updated_at = NOW()
                """,
                    tip_id,
                    cat_id,
                    prod_name,
                    json.dumps(ingredients),
                    json.dumps(steps),
                    "",   # picture_file_id
                    ""    # video_url
                )
                tip_count += 1
            except Exception as e:
                print(f"Error inserting {tip_id}: {e}")

        print(f"Inserted/updated {tip_count} tips.")

        # ---- 4. Initialize tip_stats for all tips ----
        await conn.execute("""
            INSERT INTO tip_stats (tip_id)
            SELECT id FROM tips
            ON CONFLICT (tip_id) DO NOTHING
        """)
        print("Tip stats initialized.")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(process_raw_data())
