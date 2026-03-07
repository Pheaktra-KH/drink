import asyncio
import asyncpg

DATABASE_URL = "postgresql://postgres:lXwGOXEmpDGGVOBFvrVDEbHtJvzwfdKA@nozomi.proxy.rlwy.net:22016/railway"

# Keywords for drink detection (same as before)
DRINK_TYPE_KEYWORDS = {"Hot", "Ice", "Frappe", "Cold"}

def is_ascii(s: str) -> bool:
    """Check if string contains only ASCII characters."""
    try:
        s.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

async def update_raw_data():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Fetch all rows
        rows = await conn.fetch('SELECT id, type, description, detail FROM raw_data')

        for row in rows:
            rid = row['id']
            typ = row['type'] or ""

            # Determine main_category
            if any(k in typ for k in DRINK_TYPE_KEYWORDS):
                main_cat = "drink"
            else:
                main_cat = "bakery"

            # Split description (very simple: if text contains non‑ASCII, put in km, otherwise en)
            desc = row['description'] or ""
            if is_ascii(desc):
                desc_en = desc
                desc_km = ""
            else:
                desc_en = ""
                desc_km = desc

            # Same for detail
            det = row['detail'] or ""
            if is_ascii(det):
                det_en = det
                det_km = ""
            else:
                det_en = ""
                det_km = det

            await conn.execute("""
                UPDATE raw_data
                SET main_category = $1,
                    description_en = $2,
                    description_km = $3,
                    detail_en = $4,
                    detail_km = $5
                WHERE id = $6
            """, main_cat, desc_en, desc_km, det_en, det_km, rid)

        print("Update complete.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_raw_data())
