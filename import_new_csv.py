import asyncio
import asyncpg
import csv
import os

DATABASE_URL = "postgresql://postgres:lXwGOXEmpDGGVOBFvrVDEbHtJvzwfdKA@nozomi.proxy.rlwy.net:22016/railway"

async def import_csv(filepath: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Read CSV
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        print(f"Found {len(rows)} rows to import.")

        for row in rows:
            # Map columns
            product_name = row['Items']
            main_category = row['bakery/drink']
            typ = row['Type']
            categories = row['Categories']
            class_ = row['Class']
            commodity = row['Comodity']
            description = row['Description']
            amount = row['amount']
            uom = row['UOM']
            price = row['price']
            total_cost = row['total cost']

            # Convert numeric values (handle empty)
            def to_float(val):
                if val and val.strip():
                    try:
                        return float(val)
                    except:
                        return None
                return None

            amount_float = to_float(amount)
            price_float = to_float(price)
            total_cost_float = to_float(total_cost)

            # For bilingual support, use same text for both languages
            description_en = description
            description_km = description
            detail_en = f"Price: {price}" if price else ""
            detail_km = detail_en

            await conn.execute("""
                INSERT INTO raw_data (
                    product_name, type, categories, class, items, commodity,
                    description, net_rating, uom, purchase_price, total_cost,
                    created_at, main_category,
                    description_en, description_km, detail_en, detail_km
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), $12, $13, $14, $15, $16)
            """,
                product_name,
                typ,
                categories,
                class_,
                None,  # items column (not used, but keep as None)
                commodity,
                description,
                amount_float,
                uom,
                price_float,
                total_cost_float,
                main_category,
                description_en,
                description_km,
                detail_en,
                detail_km
            )

        print("Import completed successfully.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(import_csv("new raw data.csv"))
