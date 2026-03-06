import asyncio
import asyncpg
import csv
import re

DATABASE_URL = "postgresql://postgres:lXwGOXEmpDGGVOBFvrVDEbHtJvzwfdKA@nozomi.proxy.rlwy.net:22016/railway"

def parse_value(val: str):
    """Convert string to float if possible, else return None."""
    val = val.strip()
    if not val or val in ("-", "#N/A"):
        return None
    try:
        return float(val)
    except ValueError:
        return None

def clean_string(s: str) -> str:
    """Return stripped string or None if empty or placeholder."""
    s = s.strip()
    if not s or s in ("-", "#N/A"):
        return None
    return s

async def import_raw(filepath: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Read the file
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        # Skip the first two junk lines
        data_lines = lines[2:]
        reader = csv.reader(data_lines, delimiter='\t', quotechar='"')

        count = 0
        for row in reader:
            if len(row) < 16:
                continue
            product = row[0].strip()
            if not product or product.replace('.', '').replace(',', '').isdigit():
                continue   # skip numeric lines

            # Insert row
            await conn.execute("""
                INSERT INTO raw_data (
                    product_name, type, categories, class, items, commodity,
                    description, net_rating, uom, allowance, gross_rating,
                    purchase_price, freight, cost, total_cost, detail
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """,
                product,
                clean_string(row[1]) if len(row) > 1 else None,
                clean_string(row[2]) if len(row) > 2 else None,
                clean_string(row[3]) if len(row) > 3 else None,
                clean_string(row[4]) if len(row) > 4 else None,
                clean_string(row[5]) if len(row) > 5 else None,
                clean_string(row[6]) if len(row) > 6 else None,
                parse_value(row[7]) if len(row) > 7 else None,
                clean_string(row[8]) if len(row) > 8 else None,
                parse_value(row[9]) if len(row) > 9 else None,
                parse_value(row[10]) if len(row) > 10 else None,
                parse_value(row[11]) if len(row) > 11 else None,
                parse_value(row[12]) if len(row) > 12 else None,
                parse_value(row[13]) if len(row) > 13 else None,
                parse_value(row[14]) if len(row) > 14 else None,
                clean_string(row[15]) if len(row) > 15 else None
            )
            count += 1
            if count % 1000 == 0:
                print(f"Inserted {count} rows...")

        print(f"Total rows inserted: {count}")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(import_raw("Tips of drink and bakerya.txt"))
