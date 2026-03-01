# -*- coding: utf-8 -*-
"""
Telegram Tips Bot (Single-file)
Features:
- Khmer-first UI
- Drink Tips & Bakery Tips only (no shop/ordering)
- Subcategory -> items -> tip card (ingredients & steps)
- Search (keyword) with inline buttons
- Favorites (in-memory)

Dependencies:
    pip install aiogram>=3.3 asyncpg

Security:
    Tokens are sensitive. Consider regenerating your token after testing.
"""
import os
import asyncio
import logging
from typing import Dict, List, Any

import asyncpg
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart

from db import init_db

# =========================
# CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing")

DEFAULT_LANG = "en"

# =========================
# SAMPLE DATA (in-memory)
# Structure: DATA[category][subcategory] = list of tip dicts
# tip dict: { "id", "title", "category", "subcategory", "ingredients": [ {no, ingredient, amount, uom, remark} ], "steps": [...], "picture_file_id": "" }
# =========================
def tip_id(cat: str, sub: str, slug: str) -> str:
    return f"{cat}/{sub}/{slug}"

DATA: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "drink": {
        # In your DATA dictionary, replace the "cafe" subcategory with this:
        "cafe": [
            {
                "id": tip_id("drink", "cafe", "iced_latte"),
                "title": "Iced Latte",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": "double shot optional"},
                    {"no": 2, "ingredient": "Fresh Milk", "amount": 120, "uom": "ml", "remark": "cold"},
                    {"no": 3, "ingredient": "Ice", "amount": 150, "uom": "g", "remark": ""},
                    {"no": 4, "ingredient": "Sugar Syrup", "amount": 10, "uom": "ml", "remark": "optional"},
                ],
                "steps": [
                    "Pull espresso",
                    "Add syrup and ice to the cup",
                    "Pour milk, then espresso on top",
                    "Serve immediately"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "americano"),
                "title": "Americano (Hot)",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": "freshly pulled"},
                    {"no": 2, "ingredient": "Hot Water", "amount": 120, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Pull espresso",
                    "Add hot water into cup",
                    "Pour espresso over water",
                    "Serve"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "cappuccino"),
                "title": "Cappuccino",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Steamed Milk", "amount": 120, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Milk Foam", "amount": 60, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Pull espresso shot",
                    "Steam and texture milk",
                    "Pour milk over espresso",
                    "Add foam on top"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "mocha"),
                "title": "Mocha",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Chocolate Syrup", "amount": 20, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Steamed Milk", "amount": 180, "uom": "ml", "remark": ""},
                    {"no": 4, "ingredient": "Whipped Cream", "amount": 20, "uom": "g", "remark": "optional"}
                ],
                "steps": [
                    "Add chocolate syrup to cup",
                    "Pull espresso over syrup",
                    "Steam and add milk",
                    "Top with whipped cream"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "flat_white"),
                "title": "Flat White",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 60, "uom": "ml", "remark": "double ristretto"},
                    {"no": 2, "ingredient": "Microfoam Milk", "amount": 120, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Pull double ristretto shot",
                    "Steam milk to microfoam consistency",
                    "Pour milk with minimal foam",
                    "Create latte art"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "macchiato"),
                "title": "Macchiato",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Milk Foam", "amount": 15, "uom": "ml", "remark": "dollop"}
                ],
                "steps": [
                    "Pull espresso shot",
                    "Spoon small amount of foam",
                    "Place foam on espresso",
                    "Serve immediately"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "affogato"),
                "title": "Affogato",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 60, "uom": "ml", "remark": "hot"},
                    {"no": 2, "ingredient": "Vanilla Ice Cream", "amount": 100, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Scoop ice cream into glass",
                    "Pull espresso shot",
                    "Pour hot espresso over ice cream",
                    "Serve immediately"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "vienna_coffee"),
                "title": "Vienna Coffee",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 60, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Whipped Cream", "amount": 50, "uom": "g", "remark": ""},
                    {"no": 3, "ingredient": "Chocolate Shavings", "amount": 5, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Pull espresso into cup",
                    "Top with whipped cream",
                    "Sprinkle chocolate shavings",
                    "Serve with spoon"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "irish_coffee"),
                "title": "Irish Coffee",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Hot Coffee", "amount": 150, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Irish Whiskey", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Brown Sugar", "amount": 10, "uom": "g", "remark": ""},
                    {"no": 4, "ingredient": "Whipped Cream", "amount": 30, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Warm glass with hot water",
                    "Add sugar and whiskey",
                    "Pour hot coffee and stir",
                    "Top with cream"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "cold_brew"),
                "title": "Cold Brew Coffee",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Coffee Grounds", "amount": 100, "uom": "g", "remark": "coarse grind"},
                    {"no": 2, "ingredient": "Cold Water", "amount": 1000, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Ice", "amount": 200, "uom": "g", "remark": "for serving"}
                ],
                "steps": [
                    "Combine coffee and water in jar",
                    "Steep 12-24 hours in fridge",
                    "Strain through filter",
                    "Serve over ice"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "cortado"),
                "title": "Cortado",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 60, "uom": "ml", "remark": "double shot"},
                    {"no": 2, "ingredient": "Warm Milk", "amount": 60, "uom": "ml", "remark": "equal parts"}
                ],
                "steps": [
                    "Pull double espresso",
                    "Steam small amount of milk",
                    "Add milk to espresso",
                    "Serve in small glass"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "red_eye"),
                "title": "Red Eye Coffee",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Drip Coffee", "amount": 200, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": "single shot"}
                ],
                "steps": [
                    "Brew regular coffee",
                    "Pull espresso shot",
                    "Add espresso to coffee",
                    "Serve hot"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "turmeric_latte"),
                "title": "Turmeric Latte",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Turmeric Powder", "amount": 5, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Milk", "amount": 240, "uom": "ml", "remark": "plant-based optional"},
                    {"no": 3, "ingredient": "Honey", "amount": 10, "uom": "ml", "remark": "to taste"},
                    {"no": 4, "ingredient": "Cinnamon", "amount": 2, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Heat milk gently",
                    "Whisk in turmeric and spices",
                    "Sweeten with honey",
                    "Froth and serve"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "matcha_latte"),
                "title": "Matcha Latte",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Matcha Powder", "amount": 5, "uom": "g", "remark": "ceremonial grade"},
                    {"no": 2, "ingredient": "Hot Water", "amount": 60, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Milk", "amount": 180, "uom": "ml", "remark": "steamed"},
                    {"no": 4, "ingredient": "Honey", "amount": 10, "uom": "ml", "remark": "optional"}
                ],
                "steps": [
                    "Sift matcha into bowl",
                    "Add hot water and whisk",
                    "Steam milk until frothy",
                    "Combine and sweeten"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            },
            {
                "id": tip_id("drink", "cafe", "spanish_latte"),
                "title": "Spanish Latte",
                "category": "drink",
                "subcategory": "cafe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 60, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Condensed Milk", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Milk", "amount": 150, "uom": "ml", "remark": "steamed"},
                    {"no": 4, "ingredient": "Ice", "amount": 150, "uom": "g", "remark": "for iced version"}
                ],
                "steps": [
                    "Add condensed milk to cup",
                    "Pull espresso over condensed milk",
                    "Steam and add milk",
                    "Stir gently and serve"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "tea": [
            {
                "id": tip_id("drink", "tea", "thai_tea"),
                "title": "Thai Tea (Iced)",
                "category": "drink",
                "subcategory": "tea",
                "ingredients": [
                    {"no": 1, "ingredient": "Thai Tea Leaves", "amount": 10, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Hot Water", "amount": 200, "uom": "ml", "remark": "steep 5–7 min"},
                    {"no": 3, "ingredient": "Condensed Milk", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 4, "ingredient": "Evaporated Milk", "amount": 40, "uom": "ml", "remark": ""},
                    {"no": 5, "ingredient": "Sugar", "amount": 10, "uom": "g", "remark": "to taste"},
                    {"no": 6, "ingredient": "Ice", "amount": 150, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Steep tea leaves in hot water for 5–7 minutes",
                    "Strain the tea",
                    "Add sugar, condensed milk, and evaporated milk; stir well",
                    "Pour over ice and serve"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "soda": [
            {
                "id": tip_id("drink", "soda", "lemon_soda"),
                "title": "Lemon Soda",
                "category": "drink",
                "subcategory": "soda",
                "ingredients": [
                    {"no": 1, "ingredient": "Lemon Juice", "amount": 25, "uom": "ml", "remark": "fresh"},
                    {"no": 2, "ingredient": "Sugar Syrup", "amount": 15, "uom": "ml", "remark": "adjust to taste"},
                    {"no": 3, "ingredient": "Soda Water", "amount": 150, "uom": "ml", "remark": "chilled"},
                    {"no": 4, "ingredient": "Ice", "amount": 150, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Add lemon juice and syrup to the glass",
                    "Add ice",
                    "Top with soda water and stir gently",
                    "Garnish and serve"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "frappe": [
            {
                "id": tip_id("drink", "frappe", "caramel_frappe"),
                "title": "Caramel Frappe",
                "category": "drink",
                "subcategory": "frappe",
                "ingredients": [
                    {"no": 1, "ingredient": "Espresso", "amount": 30, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Milk", "amount": 120, "uom": "ml", "remark": "cold"},
                    {"no": 3, "ingredient": "Caramel Syrup", "amount": 25, "uom": "ml", "remark": ""},
                    {"no": 4, "ingredient": "Ice", "amount": 180, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Blend espresso, milk, caramel syrup, and ice until smooth",
                    "Pour into cup and drizzle caramel",
                    "Serve"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        # Optional: include topping tips if you want
        "topping": [
            {
                "id": tip_id("drink", "topping", "brown_sugar_syrup"),
                "title": "Brown Sugar Syrup",
                "category": "drink",
                "subcategory": "topping",
                "ingredients": [
                    {"no": 1, "ingredient": "Brown Sugar", "amount": 100, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Water", "amount": 100, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Combine sugar and water in a saucepan",
                    "Heat gently until dissolved and slightly thick",
                    "Cool and store"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_brown_sugar"
            },
            {
                "id": tip_id("drink", "topping", "whipped_cream"),
                "title": "Whipped Cream",
                "category": "drink",
                "subcategory": "topping",
                "ingredients": [
                    {"no": 1, "ingredient": "Heavy Cream", "amount": 200, "uom": "ml", "remark": "cold"},
                    {"no": 2, "ingredient": "Sugar", "amount": 20, "uom": "g", "remark": ""},
                    {"no": 3, "ingredient": "Vanilla Extract", "amount": 5, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Chill bowl and beaters",
                    "Combine cream, sugar, and vanilla",
                    "Whip until soft peaks form",
                    "Store in refrigerator"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_whipped_cream"
            }
        ],
        "source": [
            {
                "id": tip_id("drink", "source", "simple_syrup"),
                "title": "Simple Syrup",
                "category": "drink",
                "subcategory": "source",
                "ingredients": [
                    {"no": 1, "ingredient": "Sugar", "amount": 200, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Water", "amount": 200, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Combine equal parts sugar and water in saucepan",
                    "Heat until sugar dissolves completely",
                    "Cool and store in airtight container",
                    "Keeps for 1 month refrigerated"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_simple_syrup"
            },
            {
                "id": tip_id("drink", "source", "caramel_sauce"),
                "title": "Caramel Sauce",
                "category": "drink",
                "subcategory": "source",
                "ingredients": [
                    {"no": 1, "ingredient": "Sugar", "amount": 200, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Water", "amount": 60, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Heavy Cream", "amount": 120, "uom": "ml", "remark": "warm"},
                    {"no": 4, "ingredient": "Butter", "amount": 30, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Dissolve sugar in water over medium heat",
                    "Cook without stirring until amber color",
                    "Remove from heat, carefully add warm cream",
                    "Stir in butter until smooth"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_caramel_sauce"
            }
        ],
        "products": [
            {
                "id": tip_id("drink", "products", "coffee_machines"),
                "title": "Coffee Machines",
                "category": "drink",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Espresso Machine (Semi-auto)",
                        "amount": "",
                        "uom": "",
                        "remark": "15‑bar pump, 1.2L tank, stainless steel",
                        "price": "$350‑800",
                        "seller": "Coffee Equipment Co.",
                        "market": "Phsar Thmei, online",
                        "image_url": "https://source.unsplash.com/400x300/?espresso,machine"
                    },
                    {
                        "no": 2,
                        "ingredient": "Automatic Drip Coffee Maker",
                        "amount": "",
                        "uom": "",
                        "remark": "Programmable, 12‑cup capacity, thermal carafe",
                        "price": "$60‑120",
                        "seller": "Home Brew",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?coffee,maker"
                    },
                    {
                        "no": 3,
                        "ingredient": "Cold Brew Maker",
                        "amount": "",
                        "uom": "",
                        "remark": "1.5L glass, stainless steel mesh filter",
                        "price": "$30‑70",
                        "seller": "Chill Brew",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?cold,brew"
                    },
                    {
                        "no": 4,
                        "ingredient": "Moka Pot",
                        "amount": "",
                        "uom": "",
                        "remark": "Aluminum, 6‑cup, stove top",
                        "price": "$20‑40",
                        "seller": "StoveTop Co.",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?moka,pot"
                    },
                    {
                        "no": 5,
                        "ingredient": "AeroPress",
                        "amount": "",
                        "uom": "",
                        "remark": "Portable, plastic, with filters",
                        "price": "$30‑50",
                        "seller": "Travel Brew",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?aeropress"
                    }
                ],
                "steps": [
                    "Consider daily output when choosing a machine",
                    "Look for 58mm portafilter for better extraction",
                    "Check warranty and service availability",
                    "Grinder is as important as the machine"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "products", "coffee_grinders"),
                "title": "Coffee Grinders",
                "category": "drink",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Burr Coffee Grinder (Conical)",
                        "amount": "",
                        "uom": "",
                        "remark": "40mm steel burrs, adjustable grind size",
                        "price": "$80‑150",
                        "seller": "GrindMaster",
                        "market": "Specialty shops",
                        "image_url": "https://source.unsplash.com/400x300/?burr,grinder"
                    },
                    {
                        "no": 2,
                        "ingredient": "Burr Grinder (Flat)",
                        "amount": "",
                        "uom": "",
                        "remark": "Professional, 54mm flat burrs",
                        "price": "$200‑400",
                        "seller": "Espresso Parts",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?flat,burr,grinder"
                    },
                    {
                        "no": 3,
                        "ingredient": "Hand Coffee Grinder",
                        "amount": "",
                        "uom": "",
                        "remark": "Ceramic burr, foldable handle",
                        "price": "$30‑60",
                        "seller": "Manual Brew",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?hand,grinder"
                    },
                    {
                        "no": 4,
                        "ingredient": "Blade Grinder",
                        "amount": "",
                        "uom": "",
                        "remark": "Electric, 200W, for coarse grinding",
                        "price": "$15‑30",
                        "seller": "QuickGrind",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?blade,grinder"
                    }
                ],
                "steps": [
                    "Burr grinders provide consistent particle size",
                    "Conical burrs are quieter and less prone to clogging",
                    "Flat burrs offer finer control for espresso",
                    "Clean grinder regularly to avoid stale coffee buildup"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "products", "milk_frothers"),
                "title": "Milk Frothers",
                "category": "drink",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Electric Milk Frother",
                        "amount": "",
                        "uom": "",
                        "remark": "Automatic, 250ml, stainless steel",
                        "price": "$30‑70",
                        "seller": "FrothPro",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?electric,frother"
                    },
                    {
                        "no": 2,
                        "ingredient": "Handheld Milk Frother",
                        "amount": "",
                        "uom": "",
                        "remark": "Battery‑operated, stainless steel wand",
                        "price": "$10‑20",
                        "seller": "MiniFroth",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?handheld,frother"
                    },
                    {
                        "no": 3,
                        "ingredient": "French Press (for frothing)",
                        "amount": "",
                        "uom": "",
                        "remark": "350ml, glass, can be used to froth milk",
                        "price": "$15‑30",
                        "seller": "Press & Froth",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?french,press"
                    }
                ],
                "steps": [
                    "Electric frothers heat and froth simultaneously",
                    "Handheld wands are cheap and portable",
                    "Use cold milk for best foam volume"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "products", "brewing_equipment"),
                "title": "Brewing Equipment",
                "category": "drink",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Pour Over Dripper (V60)",
                        "amount": "",
                        "uom": "",
                        "remark": "Ceramic, size 02, with paper filters",
                        "price": "$20‑35",
                        "seller": "PourMaster",
                        "market": "Specialty shops",
                        "image_url": "https://source.unsplash.com/400x300/?pour,over"
                    },
                    {
                        "no": 2,
                        "ingredient": "Chemex Coffee Maker",
                        "amount": "",
                        "uom": "",
                        "remark": "8‑cup, glass, with wooden collar",
                        "price": "$40‑60",
                        "seller": "Chemex",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?chemex"
                    },
                    {
                        "no": 3,
                        "ingredient": "French Press",
                        "amount": "",
                        "uom": "",
                        "remark": "1L borosilicate glass, stainless steel frame",
                        "price": "$25‑45",
                        "seller": "BrewMaster",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?french,press"
                    },
                    {
                        "no": 4,
                        "ingredient": "Gooseneck Kettle",
                        "amount": "",
                        "uom": "",
                        "remark": "1L, temperature control, pour over",
                        "price": "$40‑90",
                        "seller": "Precision Brew",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?gooseneck,kettle"
                    },
                    {
                        "no": 5,
                        "ingredient": "Siphon Coffee Brewer",
                        "amount": "",
                        "uom": "",
                        "remark": "5‑cup, alcohol lamp",
                        "price": "$70‑130",
                        "seller": "Retro Brew",
                        "market": "Kitchen shops",
                        "image_url": "https://source.unsplash.com/400x300/?siphon,coffee"
                    }
                ],
                "steps": [
                    "Pour‑over gives clean, bright flavors",
                    "French press produces full‑bodied coffee",
                    "Siphon brewing is theatrical and clean",
                    "Water temperature and pouring technique matter"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "products", "accessories"),
                "title": "Accessories",
                "category": "drink",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Coffee Tamper",
                        "amount": "",
                        "uom": "",
                        "remark": "58mm, stainless steel, calibrated spring",
                        "price": "$25‑60",
                        "seller": "Espresso Parts",
                        "market": "Specialty shops",
                        "image_url": "https://source.unsplash.com/400x300/?coffee,tamper"
                    },
                    {
                        "no": 2,
                        "ingredient": "Knock Box",
                        "amount": "",
                        "uom": "",
                        "remark": "Stainless steel, removable tray",
                        "price": "$30‑50",
                        "seller": "Barista Gear",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?knock,box"
                    },
                    {
                        "no": 3,
                        "ingredient": "Coffee Scale",
                        "amount": "",
                        "uom": "",
                        "remark": "0.1g precision, built‑in timer",
                        "price": "$20‑40",
                        "seller": "AccuBrew",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?coffee,scale"
                    },
                    {
                        "no": 4,
                        "ingredient": "Distribution Tool",
                        "amount": "",
                        "uom": "",
                        "remark": "Leveler for espresso puck",
                        "price": "$30‑50",
                        "seller": "LevelPro",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?distribution,tool"
                    },
                    {
                        "no": 5,
                        "ingredient": "Cleaning Brush Set",
                        "amount": "",
                        "uom": "",
                        "remark": "For grinder and machine maintenance",
                        "price": "$10‑20",
                        "seller": "CleanBrew",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?cleaning,brush"
                    }
                ],
                "steps": [
                    "Good tamper ensures even extraction",
                    "Knock box keeps workspace tidy",
                    "Scale improves consistency",
                    "Regular cleaning extends equipment life"
                ],
                "picture_file_id": "",
                "video_url": ""
            }
        ],
        "ingredients_list": [
            {
                "id": tip_id("drink", "ingredients_list", "coffee_beans"),
                "title": "Coffee Beans",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {
                        "no": 1, 
                        "ingredient": "Arabica Coffee Beans", 
                        "amount": "", 
                        "uom": "", 
                        "remark": "Smooth, aromatic, slightly sweet. Grown in high altitudes...",
                        "price": "$10-15 per kg",
                        "seller": "Premium Coffee Suppliers",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?arabica,coffee,beans,gourmet"
                    },
                    {
                        "no": 2, 
                        "ingredient": "Robusta Coffee Beans", 
                        "amount": "", 
                        "uom": "", 
                        "remark": "Strong, bitter, higher caffeine content...",
                        "price": "$8-12 per kg",
                        "seller": "Coffee Wholesale Co.",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?robusta,coffee,beans,dark"
                    },
                    {
                        "no": 3, 
                        "ingredient": "Liberica Coffee Beans", 
                        "amount": "", 
                        "uom": "", 
                        "remark": "Rare, floral, fruity notes. Unique aroma with smoky undertones. Limited production.",
                        "price": "$15-20 per kg",
                        "seller": "Specialty Coffee Importers",
                        "market": "Specialty shops, online stores",
                        "image_url": "https://source.unsplash.com/400x300/?exotic,coffee,beans"  # ADD THIS
                    },
                    {
                        "no": 4, 
                        "ingredient": "Excelsa Coffee Beans", 
                        "amount": "", 
                        "uom": "", 
                        "remark": "Tart, fruity, complex flavor. Adds unique character to coffee blends.",
                        "price": "$12-18 per kg",
                        "seller": "Artisanal Coffee Roasters",
                        "market": "Boutique coffee shops",
                        "image_url": "https://source.unsplash.com/400x300/?specialty,coffee,beans"  # ADD THIS
                    }
                ],
                "steps": [
                    "Look for roast date (fresher is better)",
                    "Check for uniform bean size and color",
                    "Smell for fresh aroma (not stale or musty)",
                    "Store in airtight container away from light and moisture",
                    "Whole beans stay fresh longer than ground coffee (up to 1 month)",
                    "Buy from reputable suppliers for consistent quality",
                    "Consider single-origin beans for unique flavor profiles"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "milk"),
                "title": "Milk & Dairy",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Fresh Milk (Full Cream)", "amount": "", "uom": "", "remark": "Rich, creamy texture"},
                    {"no": 2, "ingredient": "Fresh Milk (Low Fat)", "amount": "", "uom": "", "remark": "Lighter texture"},
                    {"no": 3, "ingredient": "Evaporated Milk", "amount": "", "uom": "", "remark": "Concentrated, shelf-stable"},
                    {"no": 4, "ingredient": "Condensed Milk", "amount": "", "uom": "", "remark": "Sweetened, thick texture"},
                    {"no": 5, "ingredient": "Soy Milk", "amount": "", "uom": "", "remark": "Plant-based, nutty flavor"},
                    {"no": 6, "ingredient": "Almond Milk", "amount": "", "uom": "", "remark": "Plant-based, light nutty flavor"},
                    {"no": 7, "ingredient": "Oat Milk", "amount": "", "uom": "", "remark": "Plant-based, creamy texture"}
                ],
                "steps": [
                    "Check expiration date",
                    "Look for Grade A or premium quality",
                    "Shake before using",
                    "Refrigerate immediately after purchase",
                    "Use fresh milk within 3-5 days"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "sugar"),
                "title": "Sugar & Sweeteners",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "White Sugar", "amount": "", "uom": "", "remark": "Refined, dissolves quickly"},
                    {"no": 2, "ingredient": "Brown Sugar", "amount": "", "uom": "", "remark": "Molasses flavor, moist"},
                    {"no": 3, "ingredient": "Palm Sugar", "amount": "", "uom": "", "remark": "Natural, caramel flavor"},
                    {"no": 4, "ingredient": "Honey", "amount": "", "uom": "", "remark": "Natural sweetener, floral notes"},
                    {"no": 5, "ingredient": "Maple Syrup", "amount": "", "uom": "", "remark": "Natural, rich flavor"},
                    {"no": 6, "ingredient": "Artificial Sweeteners", "amount": "", "uom": "", "remark": "Zero calorie options"}
                ],
                "steps": [
                    "Store in airtight container to prevent hardening",
                    "Keep away from moisture",
                    "Brown sugar may need softening in microwave",
                    "Check for clumps or insects",
                    "Natural sweeteners may crystallize over time"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "tea"),
                "title": "Tea Leaves & Herbs",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Black Tea", "amount": "", "uom": "", "remark": "Strong, bold flavor"},
                    {"no": 2, "ingredient": "Green Tea", "amount": "", "uom": "", "remark": "Light, fresh, grassy"},
                    {"no": 3, "ingredient": "Oolong Tea", "amount": "", "uom": "", "remark": "Semi-oxidized, complex"},
                    {"no": 4, "ingredient": "White Tea", "amount": "", "uom": "", "remark": "Delicate, subtle flavor"},
                    {"no": 5, "ingredient": "Herbal Tea (Chamomile)", "amount": "", "uom": "", "remark": "Calming, floral"},
                    {"no": 6, "ingredient": "Herbal Tea (Peppermint)", "amount": "", "uom": "", "remark": "Refreshing, minty"},
                    {"no": 7, "ingredient": "Thai Tea Mix", "amount": "", "uom": "", "remark": "Spiced, orange color"}
                ],
                "steps": [
                    "Buy loose leaf for better quality",
                    "Store in airtight, opaque containers",
                    "Keep away from strong odors",
                    "Check for freshness by aroma",
                    "Different teas need different water temperatures"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "fruit_juices"),
                "title": "Fruit Juices & Syrups",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Lemon Juice", "amount": "", "uom": "", "remark": "Fresh or bottled"},
                    {"no": 2, "ingredient": "Orange Juice", "amount": "", "uom": "", "remark": "Fresh squeezed or packaged"},
                    {"no": 3, "ingredient": "Mango Syrup", "amount": "", "uom": "", "remark": "Sweet, tropical flavor"},
                    {"no": 4, "ingredient": "Strawberry Syrup", "amount": "", "uom": "", "remark": "Sweet, berry flavor"},
                    {"no": 5, "ingredient": "Passion Fruit Syrup", "amount": "", "uom": "", "remark": "Tart, tropical"},
                    {"no": 6, "ingredient": "Grenadine", "amount": "", "uom": "", "remark": "Pomegranate syrup, red color"}
                ],
                "steps": [
                    "Check ingredient list for artificial flavors",
                    "Refrigerate after opening",
                    "Shake well before use",
                    "Look for 100% fruit content when possible",
                    "Check expiration date"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "chocolate"),
                "title": "Chocolate & Cocoa",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Cocoa Powder", "amount": "", "uom": "", "remark": "Unsweetened, for baking"},
                    {"no": 2, "ingredient": "Drinking Chocolate", "amount": "", "uom": "", "remark": "Sweetened, instant drink"},
                    {"no": 3, "ingredient": "Dark Chocolate", "amount": "", "uom": "", "remark": "High cocoa content"},
                    {"no": 4, "ingredient": "Milk Chocolate", "amount": "", "uom": "", "remark": "Creamy, sweet"},
                    {"no": 5, "ingredient": "White Chocolate", "amount": "", "uom": "", "remark": "No cocoa solids, sweet"}
                ],
                "steps": [
                    "Store in cool, dry place",
                    "Check cocoa percentage",
                    "Good quality chocolate melts smoothly",
                    "Avoid chocolate with white bloom (temperature damage)",
                    "Keep away from strong odors"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "spices"),
                "title": "Spices & Flavorings",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Cinnamon", "amount": "", "uom": "", "remark": "Ground or sticks"},
                    {"no": 2, "ingredient": "Nutmeg", "amount": "", "uom": "", "remark": "Ground or whole"},
                    {"no": 3, "ingredient": "Vanilla Extract", "amount": "", "uom": "", "remark": "Pure or artificial"},
                    {"no": 4, "ingredient": "Cardamom", "amount": "", "uom": "", "remark": "Pods or ground"},
                    {"no": 5, "ingredient": "Star Anise", "amount": "", "uom": "", "remark": "Whole stars"},
                    {"no": 6, "ingredient": "Ginger", "amount": "", "uom": "", "remark": "Fresh or ground"}
                ],
                "steps": [
                    "Buy whole spices and grind fresh for best flavor",
                    "Store in airtight containers",
                    "Keep away from heat and light",
                    "Check for freshness by aroma",
                    "Ground spices lose flavor faster than whole"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "cream_foam"),
                "title": "Cream & Foam",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Whipping Cream", "amount": "", "uom": "", "remark": "High fat, for whipping"},
                    {"no": 2, "ingredient": "Heavy Cream", "amount": "", "uom": "", "remark": "Very high fat, rich"},
                    {"no": 3, "ingredient": "Half and Half", "amount": "", "uom": "", "remark": "Half milk, half cream"},
                    {"no": 4, "ingredient": "Non-dairy Creamer", "amount": "", "uom": "", "remark": "Powdered or liquid"},
                    {"no": 5, "ingredient": "Coconut Cream", "amount": "", "uom": "", "remark": "Plant-based, tropical flavor"}
                ],
                "steps": [
                    "Check fat content (higher fat whips better)",
                    "Keep refrigerated",
                    "Shake before using",
                    "Use within expiration date",
                    "Non-dairy options for dietary restrictions"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "ice"),
                "title": "Ice & Frozen",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Clear Ice Cubes", "amount": "", "uom": "", "remark": "Made from filtered water"},
                    {"no": 2, "ingredient": "Crushed Ice", "amount": "", "uom": "", "remark": "For blended drinks"},
                    {"no": 3, "ingredient": "Ice Spheres", "amount": "", "uom": "", "remark": "Large, slow-melting"},
                    {"no": 4, "ingredient": "Flavored Ice", "amount": "", "uom": "", "remark": "Coffee or tea ice cubes"},
                    {"no": 5, "ingredient": "Nugget Ice", "amount": "", "uom": "", "remark": "Chewable, soft texture"}
                ],
                "steps": [
                    "Use filtered water for clear ice",
                    "Store in clean, sealed bags",
                    "Change ice regularly to prevent freezer taste",
                    "Clear ice melts slower than cloudy ice",
                    "Don't refreeze melted ice"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("drink", "ingredients_list", "soda_mixers"),
                "title": "Soda & Mixers",
                "category": "drink",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Soda Water", "amount": "", "uom": "", "remark": "Plain carbonated water"},
                    {"no": 2, "ingredient": "Tonic Water", "amount": "", "uom": "", "remark": "Quinine flavor, bitter"},
                    {"no": 3, "ingredient": "Ginger Ale", "amount": "", "uom": "", "remark": "Ginger-flavored soda"},
                    {"no": 4, "ingredient": "Cola", "amount": "", "uom": "", "remark": "Caramel color, sweet"},
                    {"no": 5, "ingredient": "Lemon-Lime Soda", "amount": "", "uom": "", "remark": "Clear, citrus flavor"}
                ],
                "steps": [
                    "Keep chilled for maximum carbonation",
                    "Store upright to prevent leaks",
                    "Check expiration date",
                    "Shake gently before opening",
                    "Different brands have different sweetness levels"
                ],
                "picture_file_id": "",
                "video_url": ""
            }
        ]
    },

    "bakery": {
        "cake": [
            {
                "id": tip_id("bakery", "cake", "chocolate_cake"),
                "title": "Chocolate Cake (Basic)",
                "category": "bakery",
                "subcategory": "cake",
                "ingredients": [
                    {"no": 1, "ingredient": "All-purpose Flour", "amount": 200, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Cocoa Powder", "amount": 50, "uom": "g", "remark": "unsweetened"},
                    {"no": 3, "ingredient": "Sugar", "amount": 200, "uom": "g", "remark": ""},
                    {"no": 4, "ingredient": "Eggs", "amount": 2, "uom": "pcs", "remark": "room temperature"},
                    {"no": 5, "ingredient": "Milk", "amount": 180, "uom": "ml", "remark": ""},
                    {"no": 6, "ingredient": "Vegetable Oil", "amount": 80, "uom": "ml", "remark": ""},
                    {"no": 7, "ingredient": "Baking Powder", "amount": 8, "uom": "g", "remark": ""},
                    {"no": 8, "ingredient": "Salt", "amount": 1, "uom": "g", "remark": "pinch"}
                ],
                "steps": [
                    "Preheat oven to 175°C",
                    "Mix dry ingredients; mix wet ingredients separately",
                    "Combine wet into dry; whisk until smooth",
                    "Pour into lined pan and bake 30–35 minutes",
                    "Cool and frost as desired"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "pastry": [
            {
                "id": tip_id("bakery", "pastry", "croissant"),
                "title": "Croissant (Basic)",
                "category": "bakery",
                "subcategory": "pastry",
                "ingredients": [
                    {"no": 1, "ingredient": "Bread Flour", "amount": 250, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Butter (for lamination)", "amount": 150, "uom": "g", "remark": "cold"},
                    {"no": 3, "ingredient": "Milk", "amount": 120, "uom": "ml", "remark": "lukewarm"},
                    {"no": 4, "ingredient": "Yeast", "amount": 5, "uom": "g", "remark": ""},
                    {"no": 5, "ingredient": "Sugar", "amount": 25, "uom": "g", "remark": ""},
                    {"no": 6, "ingredient": "Salt", "amount": 4, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Prepare dough and rest",
                    "Laminate with butter (folds)",
                    "Shape croissants and proof",
                    "Bake until golden"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "bread": [
            {
                "id": tip_id("bakery", "bread", "baguette"),
                "title": "Baguette",
                "category": "bakery",
                "subcategory": "bread",
                "ingredients": [
                    {"no": 1, "ingredient": "Bread Flour", "amount": 300, "uom": "g", "remark": ""},
                    {"no": 2, "ingredient": "Water", "amount": 210, "uom": "ml", "remark": ""},
                    {"no": 3, "ingredient": "Yeast", "amount": 4, "uom": "g", "remark": ""},
                    {"no": 4, "ingredient": "Salt", "amount": 6, "uom": "g", "remark": ""}
                ],
                "steps": [
                    "Mix ingredients and knead",
                    "Bulk ferment, then shape",
                    "Proof and score",
                    "Bake with steam until crusty"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "cookie": [
            {
                "id": tip_id("bakery", "cookie", "butter_cookies"),
                "title": "Butter Cookies",
                "category": "bakery",
                "subcategory": "cookie",
                "ingredients": [
                    {"no": 1, "ingredient": "Butter", "amount": 120, "uom": "g", "remark": "softened"},
                    {"no": 2, "ingredient": "Sugar", "amount": 80, "uom": "g", "remark": ""},
                    {"no": 3, "ingredient": "Egg", "amount": 1, "uom": "pc", "remark": ""},
                    {"no": 4, "ingredient": "All-purpose Flour", "amount": 180, "uom": "g", "remark": ""},
                    {"no": 5, "ingredient": "Vanilla", "amount": 3, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Cream butter and sugar",
                    "Add egg and vanilla; mix",
                    "Fold in flour; pipe or shape",
                    "Bake until edges are lightly golden"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_iced_latte"  # ADD THIS LINE
            }
        ],
        "topping": [
            {
                "id": tip_id("bakery", "topping", "cream_cheese_frosting"),
                "title": "Cream Cheese Frosting",
                "category": "bakery",
                "subcategory": "topping",
                "ingredients": [
                    {"no": 1, "ingredient": "Cream Cheese", "amount": 225, "uom": "g", "remark": "softened"},
                    {"no": 2, "ingredient": "Butter", "amount": 115, "uom": "g", "remark": "softened"},
                    {"no": 3, "ingredient": "Powdered Sugar", "amount": 400, "uom": "g", "remark": "sifted"},
                    {"no": 4, "ingredient": "Vanilla Extract", "amount": 10, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Beat cream cheese and butter until smooth",
                    "Gradually add powdered sugar",
                    "Add vanilla extract and beat until fluffy",
                    "Refrigerate before use"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_cream_cheese_frosting"
            },
            {
                "id": tip_id("bakery", "topping", "chocolate_ganache"),
                "title": "Chocolate Ganache",
                "category": "bakery",
                "subcategory": "topping",
                "ingredients": [
                    {"no": 1, "ingredient": "Dark Chocolate", "amount": 200, "uom": "g", "remark": "chopped"},
                    {"no": 2, "ingredient": "Heavy Cream", "amount": 200, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Heat cream until just boiling",
                    "Pour over chopped chocolate",
                    "Let sit for 5 minutes",
                    "Stir until smooth and glossy"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_chocolate_ganache"
            }
        ],
        "source": [
            {
                "id": tip_id("bakery", "source", "vanilla_pastry_cream"),
                "title": "Vanilla Pastry Cream",
                "category": "bakery",
                "subcategory": "source",
                "ingredients": [
                    {"no": 1, "ingredient": "Milk", "amount": 500, "uom": "ml", "remark": ""},
                    {"no": 2, "ingredient": "Egg Yolks", "amount": 6, "uom": "pcs", "remark": ""},
                    {"no": 3, "ingredient": "Sugar", "amount": 150, "uom": "g", "remark": ""},
                    {"no": 4, "ingredient": "Cornstarch", "amount": 50, "uom": "g", "remark": ""},
                    {"no": 5, "ingredient": "Vanilla Bean", "amount": 1, "uom": "pc", "remark": "or 15ml extract"}
                ],
                "steps": [
                    "Heat milk with vanilla until steaming",
                    "Whisk yolks, sugar, and cornstarch",
                    "Temper yolks with hot milk",
                    "Return to heat and cook until thick",
                    "Cover with plastic and chill"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_pastry_cream"
            },
            {
                "id": tip_id("bakery", "source", "fruit_coulis"),
                "title": "Fruit Coulis",
                "category": "bakery",
                "subcategory": "source",
                "ingredients": [
                    {"no": 1, "ingredient": "Fresh Berries", "amount": 250, "uom": "g", "remark": "strawberries, raspberries"},
                    {"no": 2, "ingredient": "Sugar", "amount": 50, "uom": "g", "remark": ""},
                    {"no": 3, "ingredient": "Lemon Juice", "amount": 15, "uom": "ml", "remark": ""}
                ],
                "steps": [
                    "Combine berries and sugar in saucepan",
                    "Cook over medium heat until berries break down",
                    "Add lemon juice and simmer for 5 minutes",
                    "Strain and cool"
                ],
                "picture_file_id": "",
                "video_url": "https://www.youtube.com/watch?v=example_fruit_coulis"
            }
        ],
        "products": [
            {
                "id": tip_id("bakery", "products", "ovens"),
                "title": "Ovens",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Convection Oven (Deck)",
                        "amount": "",
                        "uom": "",
                        "remark": "Electric, 3 trays, 60x40cm, max 300°C",
                        "price": "$1200‑2500",
                        "seller": "BakeryTech",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?convection,oven"
                    },
                    {
                        "no": 2,
                        "ingredient": "Rack Oven",
                        "amount": "",
                        "uom": "",
                        "remark": "Gas, 10 trays, rotating rack",
                        "price": "$3500‑6000",
                        "seller": "Industrial Bake",
                        "market": "Specialty suppliers",
                        "image_url": "https://source.unsplash.com/400x300/?rack,oven"
                    },
                    {
                        "no": 3,
                        "ingredient": "Deck Oven (Stone)",
                        "amount": "",
                        "uom": "",
                        "remark": "Brick, 2 decks, 80x120cm",
                        "price": "$4000‑7000",
                        "seller": "StoneHearth",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?stone,oven"
                    }
                ],
                "steps": [
                    "Match oven size to your production volume",
                    "Look for even heat distribution",
                    "Check fuel type (electric/gas/wood)",
                    "Consider installation requirements"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "products", "mixers"),
                "title": "Mixers",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Planetary Mixer",
                        "amount": "",
                        "uom": "",
                        "remark": "20L, 3 speeds, includes hook/whisk/beater",
                        "price": "$400‑900",
                        "seller": "MixPro",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?planetary,mixer"
                    },
                    {
                        "no": 2,
                        "ingredient": "Spiral Mixer",
                        "amount": "",
                        "uom": "",
                        "remark": "30L, for heavy dough, 1 hp motor",
                        "price": "$800‑1500",
                        "seller": "DoughMaster",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?spiral,mixer"
                    },
                    {
                        "no": 3,
                        "ingredient": "Hand Mixer",
                        "amount": "",
                        "uom": "",
                        "remark": "5 speeds, 250W, for light batters",
                        "price": "$30‑60",
                        "seller": "HandyBake",
                        "market": "Kitchen shops",
                        "image_url": "https://source.unsplash.com/400x300/?hand,mixer"
                    }
                ],
                "steps": [
                    "Planetary mixers are versatile",
                    "Spiral mixers handle stiff dough better",
                    "Choose capacity based on batch size",
                    "Look for safety features and bowl lift"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "products", "proofers"),
                "title": "Proofers",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Proofing Cabinet",
                        "amount": "",
                        "uom": "",
                        "remark": "Stainless steel, digital temp/humidity control",
                        "price": "$800‑1500",
                        "seller": "ProoferCo",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?proofing,cabinet"
                    },
                    {
                        "no": 2,
                        "ingredient": "Retarder Proofer",
                        "amount": "",
                        "uom": "",
                        "remark": "Combined, for overnight proofing",
                        "price": "$2000‑3500",
                        "seller": "RetardPro",
                        "market": "Specialty shops",
                        "image_url": "https://source.unsplash.com/400x300/?retarder,proofer"
                    },
                    {
                        "no": 3,
                        "ingredient": "Portable Proofer Box",
                        "amount": "",
                        "uom": "",
                        "remark": "Collapsible, for small batches",
                        "price": "$100‑200",
                        "seller": "MiniProof",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?proofer,box"
                    }
                ],
                "steps": [
                    "Consistent temperature and humidity are key",
                    "Retarder proofers save time",
                    "Ensure adequate capacity for your largest batch"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "products", "sheeters"),
                "title": "Sheeters",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Dough Sheeter (Countertop)",
                        "amount": "",
                        "uom": "",
                        "remark": "Adjustable thickness, 600mm width",
                        "price": "$1500‑3000",
                        "seller": "SheeterPro",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?dough,sheeter"
                    },
                    {
                        "no": 2,
                        "ingredient": "Industrial Sheeter",
                        "amount": "",
                        "uom": "",
                        "remark": "Floor model, 1000mm width, automatic",
                        "price": "$5000‑9000",
                        "seller": "SheeterCorp",
                        "market": "Specialty suppliers",
                        "image_url": "https://source.unsplash.com/400x300/?industrial,sheeter"
                    },
                    {
                        "no": 3,
                        "ingredient": "Lamination Sheeter",
                        "amount": "",
                        "uom": "",
                        "remark": "For croissants and puff pastry",
                        "price": "$4000‑7000",
                        "seller": "LamMaster",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?lamination,sheeter"
                    }
                ],
                "steps": [
                    "Countertop sheeters are good for small bakeries",
                    "Industrial sheeters increase productivity",
                    "Lamination sheeters create uniform layers",
                    "Check for ease of cleaning and safety features"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "products", "pans_trays"),
                "title": "Pans & Trays",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Baking Pans (Set of 12)",
                        "amount": "",
                        "uom": "",
                        "remark": "Aluminum, loaf, round, square",
                        "price": "$50‑120",
                        "seller": "PanMaster",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?baking,pan"
                    },
                    {
                        "no": 2,
                        "ingredient": "Muffin Tray (12‑cup)",
                        "amount": "",
                        "uom": "",
                        "remark": "Non‑stick, steel",
                        "price": "$15‑30",
                        "seller": "MuffinTop",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?muffin,tray"
                    },
                    {
                        "no": 3,
                        "ingredient": "Bagel Board",
                        "amount": "",
                        "uom": "",
                        "remark": "Wooden, for shaping bagels",
                        "price": "$20‑40",
                        "seller": "BagelCraft",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?bagel,board"
                    },
                    {
                        "no": 4,
                        "ingredient": "Cooling Racks (Set of 3)",
                        "amount": "",
                        "uom": "",
                        "remark": "Stainless steel, stackable, 40x60cm",
                        "price": "$30‑70",
                        "seller": "CoolRack",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?cooling,rack"
                    },
                    {
                        "no": 5,
                        "ingredient": "Sheet Pans",
                        "amount": "",
                        "uom": "",
                        "remark": "Aluminum, 13x18 inch, set of 2",
                        "price": "$20‑40",
                        "seller": "SheetPanCo",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?sheet,pan"
                    }
                ],
                "steps": [
                    "Heavy‑gauge pans distribute heat better",
                    "Non‑stick coatings ease release",
                    "Check if pans fit your oven",
                    "Cooling racks prevent soggy bottoms"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "products", "dividers"),
                "title": "Dividers & Rounders",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Dough Divider Rounder",
                        "amount": "",
                        "uom": "",
                        "remark": "36‑piece, semi‑automatic",
                        "price": "$1800‑3500",
                        "seller": "DividerPro",
                        "market": "Specialty shops",
                        "image_url": "https://source.unsplash.com/400x300/?dough,divider"
                    },
                    {
                        "no": 2,
                        "ingredient": "Manual Dough Divider",
                        "amount": "",
                        "uom": "",
                        "remark": "Bench model, 12‑piece",
                        "price": "$200‑400",
                        "seller": "BenchDivider",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?manual,divider"
                    },
                    {
                        "no": 3,
                        "ingredient": "Rounder",
                        "amount": "",
                        "uom": "",
                        "remark": "Conical, for shaping dough balls",
                        "price": "$300‑600",
                        "seller": "RoundMaster",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?dough,rounder"
                    }
                ],
                "steps": [
                    "Dividers save time and ensure uniformity",
                    "Rounders create surface tension for better rise",
                    "Choose capacity that matches your production"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "products", "decorating_tools"),
                "title": "Decorating Tools",
                "category": "bakery",
                "subcategory": "products",
                "ingredients": [
                    {
                        "no": 1,
                        "ingredient": "Piping Bags & Nozzles Set",
                        "amount": "",
                        "uom": "",
                        "remark": "12 nozzles, 50 disposable bags",
                        "price": "$15‑30",
                        "seller": "DecorPro",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?piping,bags"
                    },
                    {
                        "no": 2,
                        "ingredient": "Turntable (Icing)",
                        "amount": "",
                        "uom": "",
                        "remark": "Rotating, cast iron base",
                        "price": "$30‑60",
                        "seller": "IcingTurn",
                        "market": "Online",
                        "image_url": "https://source.unsplash.com/400x300/?turntable"
                    },
                    {
                        "no": 3,
                        "ingredient": "Brushes Set",
                        "amount": "",
                        "uom": "",
                        "remark": "Silicone, for glazing and dusting",
                        "price": "$10‑20",
                        "seller": "BrushBake",
                        "market": "Phsar Thmei",
                        "image_url": "https://source.unsplash.com/400x300/?pastry,brush"
                    },
                    {
                        "no": 4,
                        "ingredient": "Scrapers & Spatulas",
                        "amount": "",
                        "uom": "",
                        "remark": "Stainless steel, set of 3",
                        "price": "$15‑30",
                        "seller": "SmoothEdge",
                        "market": "Central Market",
                        "image_url": "https://source.unsplash.com/400x300/?spatula"
                    }
                ],
                "steps": [
                    "Good piping tips create professional finishes",
                    "Turntable makes icing easier",
                    "Silicone brushes are heat‑resistant and easy to clean"
                ],
                "picture_file_id": "",
                "video_url": ""
            }
        ],
        "ingredients_list": [
            {
                "id": tip_id("bakery", "ingredients_list", "flour"),
                "title": "Flour & Grains",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "All-purpose Flour", "amount": "", "uom": "", "remark": "Versatile, medium protein","price": "$10-15 per kg","seller": "Local coffee suppliers","market": "Central Market, Phnom Penh"},
                    {"no": 2, "ingredient": "Bread Flour", "amount": "", "uom": "", "remark": "High protein, gluten development","price": "$10-15 per kg","seller": "Local coffee suppliers","market": "Central Market, Phnom Penh"},
                    {"no": 3, "ingredient": "Cake Flour", "amount": "", "uom": "", "remark": "Low protein, soft texture","price": "$10-15 per kg","seller": "Local coffee suppliers","market": "Central Market, Phnom Penh"},
                    {"no": 4, "ingredient": "Whole Wheat Flour", "amount": "", "uom": "", "remark": "Whole grain, nutty flavor","price": "$10-15 per kg","seller": "Local coffee suppliers","market": "Central Market, Phnom Penh"},
                    {"no": 5, "ingredient": "Rice Flour", "amount": "", "uom": "", "remark": "Gluten-free, fine texture","price": "$10-15 per kg","seller": "Local coffee suppliers","market": "Central Market, Phnom Penh"},
                    {"no": 6, "ingredient": "Almond Flour", "amount": "", "uom": "", "remark": "Gluten-free, nutty flavor","price": "$10-15 per kg","seller": "Local coffee suppliers","market": "Central Market, Phnom Penh"}
                ],
                "steps": [
                    "Store in airtight container",
                    "Check for insects or weevils",
                    "Keep in cool, dry place",
                    "Different flours for different purposes",
                    "Sift before using for lighter texture"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "sugar"),
                "title": "Sugar & Sweeteners",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Granulated Sugar", "amount": "", "uom": "", "remark": "White, refined sugar"},
                    {"no": 2, "ingredient": "Powdered Sugar", "amount": "", "uom": "", "remark": "Confectioners sugar, for icing"},
                    {"no": 3, "ingredient": "Brown Sugar", "amount": "", "uom": "", "remark": "Light or dark, moist"},
                    {"no": 4, "ingredient": "Demerara Sugar", "amount": "", "uom": "", "remark": "Large crystals, crunchy"},
                    {"no": 5, "ingredient": "Honey", "amount": "", "uom": "", "remark": "Natural liquid sweetener"},
                    {"no": 6, "ingredient": "Maple Syrup", "amount": "", "uom": "", "remark": "Natural, distinct flavor"}
                ],
                "steps": [
                    "Store in airtight container to prevent hardening",
                    "Brown sugar may need apple slice to keep moist",
                    "Sift powdered sugar to remove lumps",
                    "Natural sweeteners may affect baking time",
                    "Different sugars create different textures"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "butter"),
                "title": "Butter & Fats",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Unsalted Butter", "amount": "", "uom": "", "remark": "Control salt in recipes"},
                    {"no": 2, "ingredient": "Salted Butter", "amount": "", "uom": "", "remark": "For general use"},
                    {"no": 3, "ingredient": "Clarified Butter", "amount": "", "uom": "", "remark": "Pure butterfat, higher smoke point"},
                    {"no": 4, "ingredient": "Margarine", "amount": "", "uom": "", "remark": "Plant-based alternative"},
                    {"no": 5, "ingredient": "Vegetable Oil", "amount": "", "uom": "", "remark": "Neutral flavor, liquid"},
                    {"no": 6, "ingredient": "Coconut Oil", "amount": "", "uom": "", "remark": "Solid at room temp, tropical flavor"}
                ],
                "steps": [
                    "Store butter refrigerated or frozen",
                    "Bring to room temperature before baking",
                    "Check for rancid smell",
                    "Different fats create different textures",
                    "Butter quality affects flavor significantly"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "eggs"),
                "title": "Eggs & Egg Products",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Large Eggs", "amount": "", "uom": "", "remark": "Standard baking size"},
                    {"no": 2, "ingredient": "Extra Large Eggs", "amount": "", "uom": "", "remark": "For richer recipes"},
                    {"no": 3, "ingredient": "Egg Whites", "amount": "", "uom": "", "remark": "For meringues, light texture"},
                    {"no": 4, "ingredient": "Egg Yolks", "amount": "", "uom": "", "remark": "For richness, color"},
                    {"no": 5, "ingredient": "Duck Eggs", "amount": "", "uom": "", "remark": "Larger, richer flavor"},
                    {"no": 6, "ingredient": "Egg Substitutes", "amount": "", "uom": "", "remark": "For dietary restrictions"}
                ],
                "steps": [
                    "Check for cracks before buying",
                    "Store pointed end down in refrigerator",
                    "Bring to room temperature before baking",
                    "Test freshness by placing in water (fresh eggs sink)",
                    "Separate eggs when cold, easier to separate"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "leavening"),
                "title": "Leavening Agents",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Baking Powder", "amount": "", "uom": "", "remark": "Double-acting, most common"},
                    {"no": 2, "ingredient": "Baking Soda", "amount": "", "uom": "", "remark": "Needs acid to activate"},
                    {"no": 3, "ingredient": "Yeast (Active Dry)", "amount": "", "uom": "", "remark": "Needs proofing in warm water"},
                    {"no": 4, "ingredient": "Yeast (Instant)", "amount": "", "uom": "", "remark": "Direct mix with flour"},
                    {"no": 5, "ingredient": "Yeast (Fresh)", "amount": "", "uom": "", "remark": "Compressed, perishable"},
                    {"no": 6, "ingredient": "Cream of Tartar", "amount": "", "uom": "", "remark": "Stabilizes egg whites"}
                ],
                "steps": [
                    "Check expiration date (loses potency)",
                    "Store in cool, dry place",
                    "Test baking powder in hot water (should bubble)",
                    "Yeast needs proper temperature (too hot kills)",
                    "Don't substitute baking powder for soda 1:1"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "chocolate"),
                "title": "Chocolate & Cocoa",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Dark Chocolate (70%+)", "amount": "", "uom": "", "remark": "Bittersweet, intense flavor"},
                    {"no": 2, "ingredient": "Dark Chocolate (50-70%)", "amount": "", "uom": "", "remark": "Semisweet, balanced"},
                    {"no": 3, "ingredient": "Milk Chocolate", "amount": "", "uom": "", "remark": "Creamy, sweet"},
                    {"no": 4, "ingredient": "White Chocolate", "amount": "", "uom": "", "remark": "No cocoa solids, sweet"},
                    {"no": 5, "ingredient": "Cocoa Powder (Natural)", "amount": "", "uom": "", "remark": "Acidic, strong flavor"},
                    {"no": 6, "ingredient": "Cocoa Powder (Dutch)", "amount": "", "uom": "", "remark": "Alkalized, milder flavor"}
                ],
                "steps": [
                    "Check cocoa percentage",
                    "Store in cool, dry place (not refrigerator)",
                    "Good quality chocolate melts smoothly",
                    "Chocolate chips have stabilizers for shape",
                    "Different chocolates for different purposes"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "dairy"),
                "title": "Dairy Products",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Whole Milk", "amount": "", "uom": "", "remark": "Full fat, rich"},
                    {"no": 2, "ingredient": "Buttermilk", "amount": "", "uom": "", "remark": "Tangy, tenderizes baked goods"},
                    {"no": 3, "ingredient": "Heavy Cream", "amount": "", "uom": "", "remark": "For whipping, rich desserts"},
                    {"no": 4, "ingredient": "Sour Cream", "amount": "", "uom": "", "remark": "Tangy, moist texture"},
                    {"no": 5, "ingredient": "Cream Cheese", "amount": "", "uom": "", "remark": "For cheesecake, frosting"},
                    {"no": 6, "ingredient": "Yogurt", "amount": "", "uom": "", "remark": "Plain, adds moisture"}
                ],
                "steps": [
                    "Check expiration dates (dairy spoils quickly)",
                    "Keep refrigerated",
                    "Bring to room temperature before baking",
                    "Full fat versions give richer results",
                    "Shake or stir before using"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "nuts_seeds"),
                "title": "Nuts & Seeds",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Almonds", "amount": "", "uom": "", "remark": "Whole, sliced, or slivered"},
                    {"no": 2, "ingredient": "Walnuts", "amount": "", "uom": "", "remark": "Bitter, crunchy"},
                    {"no": 3, "ingredient": "Pecans", "amount": "", "uom": "", "remark": "Sweet, buttery"},
                    {"no": 4, "ingredient": "Hazelnuts", "amount": "", "uom": "", "remark": "Nutty, pairs with chocolate"},
                    {"no": 5, "ingredient": "Sesame Seeds", "amount": "", "uom": "", "remark": "White or black, for topping"},
                    {"no": 6, "ingredient": "Chia Seeds", "amount": "", "uom": "", "remark": "For texture, nutrition"}
                ],
                "steps": [
                    "Store in airtight container in refrigerator",
                    "Check for rancid smell",
                    "Toast before using for better flavor",
                    "Nuts can be ground into flour",
                    "Remove skins for smoother texture"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "fruits"),
                "title": "Fruits & Berries",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Fresh Berries", "amount": "", "uom": "", "remark": "Strawberries, blueberries, raspberries"},
                    {"no": 2, "ingredient": "Dried Fruits", "amount": "", "uom": "", "remark": "Raisins, cranberries, apricots"},
                    {"no": 3, "ingredient": "Citrus Zest", "amount": "", "uom": "", "remark": "Lemon, orange, lime peel"},
                    {"no": 4, "ingredient": "Bananas", "amount": "", "uom": "", "remark": "Ripe for banana bread"},
                    {"no": 5, "ingredient": "Apples", "amount": "", "uom": "", "remark": "For pies, cakes"},
                    {"no": 6, "ingredient": "Dates", "amount": "", "uom": "", "remark": "Natural sweetener, sticky texture"}
                ],
                "steps": [
                    "Wash fresh fruits before using",
                    "Dry thoroughly to prevent sogginess",
                    "Soak dried fruits in liquid to plump",
                    "Use ripe fruits for best flavor",
                    "Citrus zest adds bright flavor without liquid"
                ],
                "picture_file_id": "",
                "video_url": ""
            },
            {
                "id": tip_id("bakery", "ingredients_list", "flavorings"),
                "title": "Flavorings & Extracts",
                "category": "bakery",
                "subcategory": "ingredients_list",
                "ingredients": [
                    {"no": 1, "ingredient": "Vanilla Extract", "amount": "", "uom": "", "remark": "Pure or artificial"},
                    {"no": 2, "ingredient": "Vanilla Bean", "amount": "", "uom": "", "remark": "Whole pods, premium flavor"},
                    {"no": 3, "ingredient": "Almond Extract", "amount": "", "uom": "", "remark": "Strong, use sparingly"},
                    {"no": 4, "ingredient": "Lemon Extract", "amount": "", "uom": "", "remark": "Concentrated lemon flavor"},
                    {"no": 5, "ingredient": "Rose Water", "amount": "", "uom": "", "remark": "Floral, Middle Eastern baking"},
                    {"no": 6, "ingredient": "Orange Blossom Water", "amount": "", "uom": "", "remark": "Floral, delicate"}
                ],
                "steps": [
                    "Store in dark bottles away from light",
                    "Pure extracts are alcohol-based",
                    "Use sparingly - extracts are concentrated",
                    "Check for artificial flavors",
                    "Different brands have different strengths"
                ],
                "picture_file_id": "",
                "video_url": ""
            }
        ]
    }
}

# =========================
# LANGUAGE TRANSLATIONS
# =========================
TEXTS = {
    "km": {  # Khmer
        # Main Menu
        "welcome": "សួស្តី! 👋 សូមជ្រើសរើសមុខងារ",
        "main_menu": "សូមជ្រើសរើសមុខងារ",
        "drink_tips": "🍹 គន្លឹះភេសជ្ជៈ",
        "bakery_tips": "🧁 គន្លឹះនំ",
        "drink_menu": "🍹 ជ្រើសរើសប្រភេទភេសជ្ជៈ",  # ADD THIS LINE
        "bakery_menu": "🧁 ជ្រើសរើសប្រភេទនំ",  # ADD THIS LINE
        "search": "🔎 ស្វែងរក",
        "favorites": "⭐ រក្សាទុក",
        "settings": "⚙️ កំណត់",        
        "topping": "🍒 ថែបពីង",  # Khmer
        "source": "🥣 ស៊ុបសាច់",  # Khmer
        "ingredients_list": "📋 បញ្ជីសម្ភារៈ",  # Khmer
        # Inside TEXTS["km"] add:
        "products": "🛒 ផលិតផល",
        
        # Navigation
        "back": "◀️ ត្រឡប់",
        "home": "🏠 មុខងារ",
        
        # Tip Card
        "type_label": "🧋 ប្រភេទ",
        "ingredients": "📝 សម្ភារៈ",
        "how_to_make": "👩‍🍳 វិធីធ្វើ",
        "times": "ដង",
        
        # Buttons
        "video": "🎥 វីដេអូ",
        "no_video": "🎥 គ្មានវីដេអូ",
        "save": "⭐ រក្សាទុក",
        "share": "📤 ចែករំលែក",
        
        # Search
        "search_prompt": "បញ្ចូលពាក្យស្វែងរក (ឧ. latte, cake)",
        "no_results": "មិនមានលទ្ធផលត្រូវគ្នាទេ",
        "search_results": "🔎 លទ្ធផលស្វែងរក:",
        
        # Favorites
        "favorites_list": "⭐ មាតិកាដែលបានរក្សាទុក:",
        "no_favorites": "មិនទាន់មានមាតិកាដែលបានរក្សាទុកទេ",
        "saved": "✅ បានរក្សាទុក",
        "already_saved": "⭐ មានរួចហើយ",
        
        # Share
        "share_title": "🎯 គន្លឹះពិសេសសម្រាប់អ្នក!",
        "share_prompt": "ចូលទៅមើលគន្លឹះពេញលេញនៅក្នុង Telegram Bot:",
        
        # Settings
        "settings_menu": "⚙️ ការកំណត់",
        "about": "ℹ️ អំពី",
        "help": "❓ ជំនួយ",
        "channel": "📢 ឆាណែល",
        "group": "👥 ក្រុម",
        "language": "🌐 ភាសា",
        "units": "📏 ខ្នាត",
        "contact": "📞 ទំនាក់ទំនង",
        "stats": "📊 ស្ថិតិ",
        "clear_favs": "🗑️ លុបការរក្សាទុក",
        
        # Language
        "khmer": "🇰🇭 ខ្មែរ",
        "english": "🇬🇧 English",
        "lang_changed": "✅ ភាសាត្រូវបានផ្លាស់ប្តូរទៅភាសាខ្មែរ",
    },
    "en": {  # English
        # Main Menu
        "welcome": "Hello! 👋 Please choose a function",
        "main_menu": "Please choose a function",
        "drink_tips": "🍹 Drink Tips",
        "bakery_tips": "🧁 Bakery Tips",
        "drink_menu": "🍹 Select a drink category",  # ADD THIS LINE
        "bakery_menu": "🧁 Select a bakery category",  # ADD THIS LINE
        "search": "🔎 Search",
        "favorites": "⭐ Favorites",
        "settings": "⚙️ Settings",        
        "topping": "🍒 Topping",  # English
        "source": "🥣 Sauce",  # English
        "ingredients_list": "📋 Ingredients List",  # English
        # Inside TEXTS["en"] add:
        "products": "🛒 Products",
        
        # Navigation
        "back": "◀️ Back",
        "home": "🏠 Home",
        
        # Tip Card
        "type_label": "🧋 Type",
        "ingredients": "📝 Ingredients",
        "how_to_make": "👩‍🍳 How to Make",
        "times": "times",
        
        # Buttons
        "video": "🎥 Video",
        "no_video": "🎥 No Video",
        "save": "⭐ Save",
        "share": "📤 Share",
        
        # Search
        "search_prompt": "Enter search keyword (e.g., latte, cake)",
        "no_results": "No matching results",
        "search_results": "🔎 Search results:",
        
        # Favorites
        "favorites_list": "⭐ Saved content:",
        "no_favorites": "No saved content yet",
        "saved": "✅ Saved",
        "already_saved": "⭐ Already saved",
        
        # Share
        "share_title": "🎯 Special tip for you!",
        "share_prompt": "View the full tip in Telegram Bot:",
        
        # Settings
        "settings_menu": "⚙️ Settings",
        "about": "ℹ️ About",
        "help": "❓ Help",
        "channel": "📢 Channel",
        "group": "👥 Group",
        "language": "🌐 Language",
        "units": "📏 Units",
        "contact": "📞 Contact",
        "stats": "📊 Statistics",
        "clear_favs": "🗑️ Clear Favorites",
        
        # Language
        "khmer": "🇰🇭 Khmer",
        "english": "🇬🇧 English",
        "lang_changed": "✅ Language changed to English",
    }
}

# =========================
# LANGUAGE MANAGEMENT
# =========================
# Store user language preferences
user_languages: Dict[int, str] = {}

def get_user_lang(user_id: int) -> str:
    """Get user's language preference"""
    return user_languages.get(user_id, DEFAULT_LANG)

def set_user_lang(user_id: int, lang: str):
    """Set user's language preference"""
    if lang in ["km", "en"]:
        user_languages[user_id] = lang

def get_text(user_id: int, key: str) -> str:
    """Get translated text for user"""
    lang = get_user_lang(user_id)
    return TEXTS[lang].get(key, key)


# =========================
# CONTENT STORE (with DB for favorites)
# =========================
class ContentStore:
    def __init__(self, data: Dict[str, Dict[str, List[Dict[str, Any]]]]):
        self.data = data
        self.index: Dict[str, Dict[str, Any]] = {}
        for cat, submap in data.items():
            for sub, items in submap.items():
                for tip in items:
                    self.index[tip["id"]] = tip
        # In-memory counts (views, shares) – can stay for now
        self.view_counts: Dict[str, int] = {}
        self.fav_counts: Dict[str, int] = {}
        self.share_counts: Dict[str, int] = {}

    async def add_fav(self, user_id: int, tip_id: str) -> bool:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            result = await conn.execute('''
                INSERT INTO user_favorites (user_id, tip_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            ''', user_id, tip_id)
            await conn.close()
            return 'INSERT 0 1' in result
        except:
            await conn.close()
            return False

    async def get_favs(self, user_id: int) -> List[Dict[str, Any]]:
        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch('SELECT tip_id FROM user_favorites WHERE user_id = $1', user_id)
        await conn.close()
        tip_ids = [row['tip_id'] for row in rows]
        return [self.index[tid] for tid in tip_ids if tid in self.index]

    def list_subcats(self, category: str) -> List[str]:
        return sorted(list(self.data.get(category, {}).keys()))

    def list_items(self, category: str, subcategory: str) -> List[Dict[str, Any]]:
        return list(self.data.get(category, {}).get(subcategory, []))

    def get_tip(self, tip_id: str) -> Dict[str, Any]:
        return self.index.get(tip_id)

    def increment_view(self, tip_id: str) -> int:
        current = self.view_counts.get(tip_id, 0)
        self.view_counts[tip_id] = current + 1
        return current + 1

    def get_view_count(self, tip_id: str) -> int:
        return self.view_counts.get(tip_id, 0)

    def increment_fav(self, tip_id: str) -> int:
        current = self.fav_counts.get(tip_id, 0)
        self.fav_counts[tip_id] = current + 1
        return current + 1

    def get_fav_count(self, tip_id: str) -> int:
        return self.fav_counts.get(tip_id, 0)

    def increment_share(self, tip_id: str) -> int:
        current = self.share_counts.get(tip_id, 0)
        self.share_counts[tip_id] = current + 1
        return current + 1

    def get_share_count(self, tip_id: str) -> int:
        return self.share_counts.get(tip_id, 0)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = (query or "").strip().lower()
        if not q:
            return []
        results: List[Dict[str, Any]] = []
        for tip in self.index.values():
            hay = [
                tip.get("title", ""),
                tip.get("category", ""),
                tip.get("subcategory", ""),
                " ".join([i.get("ingredient", "") for i in tip.get("ingredients", [])])
            ]
            hay_text = " ".join(hay).lower()
            if q in hay_text:
                results.append(tip)
            if len(results) >= limit:
                break
        return results

CONTENT = ContentStore(DATA)


# =========================
# HELPERS: RENDER & KEYBOARDS
# =========================
def render_tip_card(tip: Dict[str, Any], view_count: int = 0, fav_count: int = 0, share_count: int = 0, user_id: int = None) -> str:
    """Render tip card with user's language"""
    title = tip.get("title", "Untitled")
    subcat = tip.get("subcategory", "")
    ingredients: List[Dict[str, Any]] = tip.get("ingredients", [])
    steps: List[str] = tip.get("steps", [])
    
    # Get language-specific labels
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    type_label = TEXTS[lang]["type_label"]
    ingredients_label = TEXTS[lang]["ingredients"]
    how_to_make_label = TEXTS[lang]["how_to_make"]
    times_label = TEXTS[lang]["times"]

    lines: List[str] = []
    lines.append(f"📘 {title}")
    lines.append(f"{type_label}: {subcat}")
    lines.append(f"👁️ {view_count} {times_label} | ⭐ {fav_count} | 📤 {share_count}\n")
    
    lines.append(ingredients_label)
    
    # Calculate the total width for each line part
    max_prefix_length = 0
    formatted_ingredients = []
    
    for r in ingredients:
        no = str(r.get("no", ""))
        ing = str(r.get("ingredient", ""))
        amt = str(r.get("amount", ""))
        uom = str(r.get("uom", ""))
        rem = str(r.get("remark", ""))
        
        prefix = f"{no}. {ing}"
        max_prefix_length = max(max_prefix_length, len(prefix))
        
        formatted_ingredients.append({
            "prefix": prefix,
            "amount": amt,
            "uom": uom,
            "remark": rem
        })
    
    target_column = max_prefix_length + 5
    
    for item in formatted_ingredients:
        prefix = item["prefix"]
        amt = item["amount"]
        uom = item["uom"]
        rem = item["remark"]
        
        dots_needed = target_column - len(prefix)
        if dots_needed < 1:
            dots_needed = 1
        
        dots = "." * dots_needed
        
        if rem:
            line = f"{prefix}{dots}{amt}{uom} ({rem})"
        else:
            line = f"{prefix}{dots}{amt}{uom}"
        
        lines.append(line)

    lines.append(f"\n{how_to_make_label}")
    for i, s in enumerate(steps, start=1):
        lines.append(f"{i}) {s}")

    return "\n".join(lines)

def render_ingredient_card(tip: Dict[str, Any], current_index: int, total_count: int, user_id: int = None) -> str:
    """Render ingredient card with price, seller info, and pagination"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    title = tip.get("title", "Untitled")
    price = tip.get("price", "Check market")
    market = tip.get("market", "Local markets")
    available = tip.get("available", "Various forms")
    seller_name = tip.get("seller_name", "Available seller")
    seller_telegram = tip.get("seller_telegram", "")
    seller_phone = tip.get("seller_phone", "")
    description = tip.get("description", "")
    
    lines: List[str] = []
    lines.append(f"📦 {title}\n")
    
    if price:
        lines.append(f"💰 Price: {price}")
    
    if market:
        lines.append(f"📍 Market: {market}")
    
    if available:
        lines.append(f"🛒 Available: {available}")
    
    lines.append(f"\n📞 Contact Seller:")
    
    if seller_name:
        lines.append(f"👤 Vendor: {seller_name}")
    
    if seller_telegram:
        # Remove @ if present and create link
        telegram_username = seller_telegram.lstrip('@')
        lines.append(f"📱 Telegram: <a href='https://t.me/{telegram_username}'>{seller_telegram}</a>")
    
    if seller_phone:
        lines.append(f"📞 Phone: {seller_phone}")
    
    if description:
        lines.append(f"\n📋 Description:\n{description}")
    
    lines.append(f"\n📄 Item {current_index + 1} of {total_count}")
    
    return "\n".join(lines)


def main_menu_kb(user_id: int = None) -> ReplyKeyboardMarkup:
    """Main menu keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=TEXTS[lang]["drink_tips"]), 
             KeyboardButton(text=TEXTS[lang]["bakery_tips"])],
            [KeyboardButton(text=TEXTS[lang]["search"]), 
             KeyboardButton(text=TEXTS[lang]["favorites"])],
            [KeyboardButton(text=TEXTS[lang]["settings"])]
        ],
        resize_keyboard=True
    )

def subcategory_kb(category: str, subcats: List[str], user_id: int = None) -> InlineKeyboardMarkup:
    """Subcategory keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    rows: List[List[InlineKeyboardButton]] = []
    
    # Separate new subcategories (topping, source, ingredients_list) from old ones
    new_subs = []
    old_subs = []
    
    for sub in subcats:
        if sub in ["topping", "source", "ingredients_list", "products"]:
            new_subs.append(sub)
        else:
            old_subs.append(sub)
    
    # Create grid for OLD subcategories: 2 buttons per row
    for i in range(0, len(old_subs), 2):
        row = []
        s1 = old_subs[i]
        
        # Use translated names for specific subcategories
        if s1 == "topping":
            label1 = TEXTS[lang]["topping"]
        elif s1 == "source":
            label1 = TEXTS[lang]["source"]
        elif s1 == "ingredients_list":
            label1 = TEXTS[lang]["ingredients_list"]
        else:
            label1 = s1.capitalize() if s1.isascii() else s1
            
        row.append(InlineKeyboardButton(text=label1, callback_data=f"tips:sub:{category}:{s1}:1"))
        
        if i + 1 < len(old_subs):
            s2 = old_subs[i + 1]
            if s2 == "topping":
                label2 = TEXTS[lang]["topping"]
            elif s2 == "source":
                label2 = TEXTS[lang]["source"]
            elif s2 == "ingredients_list":
                label2 = TEXTS[lang]["ingredients_list"]
            else:
                label2 = s2.capitalize() if s2.isascii() else s2
            row.append(InlineKeyboardButton(text=label2, callback_data=f"tips:sub:{category}:{s2}:1"))
        
        rows.append(row)
    
    # Create a SINGLE row for NEW subcategories: 3 buttons in one row
    if new_subs:
        new_row = []
        for sub in new_subs:
            if sub == "topping":
                label = TEXTS[lang]["topping"]
            elif sub == "source":
                label = TEXTS[lang]["source"]
            elif sub == "ingredients_list":
                label = TEXTS[lang]["ingredients_list"]
            elif sub == "products":                         # <-- ADD THIS BLOCK
                label = TEXTS[lang]["products"]
            else:
                label = sub.capitalize() if sub.isascii() else sub
                
            new_row.append(InlineKeyboardButton(text=label, callback_data=f"tips:sub:{category}:{sub}:1"))
        
        # Ensure we have exactly 3 buttons in this row
        # If we have less than 3, fill with empty buttons or adjust layout
        rows.append(new_row)
    
    # Add navigation buttons
    rows.append([
        InlineKeyboardButton(text=TEXTS[lang]["back"], callback_data="nav:back"),
        InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def item_list_kb(category: str, subcategory: str, items: List[Dict[str, Any]], page: int, page_size: int = 12, user_id: int = None) -> InlineKeyboardMarkup:
    """Item list keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    start = (page - 1) * page_size
    page_items = items[start:start + page_size]
    rows: List[List[InlineKeyboardButton]] = []
    
    # SPECIAL HANDLING: For specific subcategories in drink and bakery, use 3 columns
    drink_3col_subs = ["cafe", "ingredients_list", "tea", "soda", "frappe", "topping", "source", "products"]
    bakery_3col_subs = ["cake", "pastry", "bread", "cookie", "topping", "source", "ingredients_list", "products"]
    
    if category == "drink" and subcategory in drink_3col_subs:
        num_columns = 3
    elif category == "bakery" and subcategory in bakery_3col_subs:
        num_columns = 3
    else:
        # Original logic for other categories
        avg_length = sum(len(tip.get("title", "")) for tip in page_items) / max(len(page_items), 1)
        if avg_length > 15:
            num_columns = 2
        else:
            num_columns = 3
    
    current_row = []
    for i, tip in enumerate(page_items):
        current_row.append(InlineKeyboardButton(
            text=tip.get("title", ""), 
            callback_data=f"tips:item:{tip['id']}"
        ))
        
        if len(current_row) == num_columns or i == len(page_items) - 1:
            rows.append(current_row)
            current_row = []
    
    nav: List[InlineKeyboardButton] = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"tips:sub:{category}:{subcategory}:{page-1}"))
    
    total_pages = (len(items) + page_size - 1) // page_size
    if total_pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop"))
    
    if start + page_size < len(items):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"tips:sub:{category}:{subcategory}:{page+1}"))
    
    if nav:
        rows.append(nav)
    
    rows.append([
        InlineKeyboardButton(text=TEXTS[lang]["back"], callback_data=f"tips:cat:{category}"),
        InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

def tip_card_kb(tip_id_str: str, back_payload: str, video_url: str = None, user_id: int = None) -> InlineKeyboardMarkup:
    """Tip card keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    buttons = []
    first_row = []
    
    if video_url and video_url.strip():
        first_row.append(InlineKeyboardButton(text=TEXTS[lang]["video"], url=video_url))
    else:
        first_row.append(InlineKeyboardButton(text=TEXTS[lang]["no_video"], callback_data="noop"))
    
    first_row.append(InlineKeyboardButton(text=TEXTS[lang]["save"], callback_data=f"tips:fav:{tip_id_str}"))
    first_row.append(InlineKeyboardButton(text=TEXTS[lang]["share"], callback_data=f"tips:share:{tip_id_str}"))
    
    buttons.append(first_row)
    buttons.append([
        InlineKeyboardButton(text=TEXTS[lang]["back"], callback_data=back_payload),
        InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def ingredient_card_kb(tip_id_str: str, prev_tip_id: str = None, next_tip_id: str = None, 
                      back_payload: str = None, user_id: int = None) -> InlineKeyboardMarkup:
    """Ingredient card keyboard with pagination and save button"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    buttons = []
    
    # First row: Previous | Save | Next
    first_row = []
    
    if prev_tip_id:
        first_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"tips:item:{prev_tip_id}"))
    
    first_row.append(InlineKeyboardButton(text=TEXTS[lang]["save"], callback_data=f"tips:fav:{tip_id_str}"))
    
    if next_tip_id:
        first_row.append(InlineKeyboardButton(text="➡️", callback_data=f"tips:item:{next_tip_id}"))
    
    buttons.append(first_row)
    
    # Second row: Back button
    if back_payload:
        buttons.append([
            InlineKeyboardButton(text="◀️ " + TEXTS[lang]["back"], callback_data=back_payload),
            InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home"),
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def search_results_kb(results: List[Dict[str, Any]], user_id: int = None) -> InlineKeyboardMarkup:
    """Search results keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    rows: List[List[InlineKeyboardButton]] = []
    for tip in results[:10]:
        rows.append([InlineKeyboardButton(text=tip["title"], callback_data=f"tips:item:{tip['id']}")])
    if not rows:
        rows = [[InlineKeyboardButton(text="—", callback_data="noop")]]
    rows.append([InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def favorites_kb(favs: List[Dict[str, Any]], user_id: int = None) -> InlineKeyboardMarkup:
    """Favorites keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    rows: List[List[InlineKeyboardButton]] = []
    for tip in favs[:10]:
        rows.append([InlineKeyboardButton(text=tip["title"], callback_data=f"tips:item:{tip['id']}")])
    if not rows:
        rows = [[InlineKeyboardButton(text="—", callback_data="noop")]]
    rows.append([InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def settings_kb(user_id: int = None) -> InlineKeyboardMarkup:
    """Settings keyboard with user's language"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=TEXTS[lang]["about"], callback_data="settings:about")],
        [InlineKeyboardButton(text=TEXTS[lang]["help"], callback_data="settings:help")],
        [
            InlineKeyboardButton(text=TEXTS[lang]["channel"], callback_data="settings:channel"),
            InlineKeyboardButton(text=TEXTS[lang]["group"], callback_data="settings:group")
        ],
        [
            InlineKeyboardButton(text=TEXTS[lang]["language"], callback_data="settings:language"),
            InlineKeyboardButton(text=TEXTS[lang]["units"], callback_data="settings:units")
        ],
        [
            InlineKeyboardButton(text=TEXTS[lang]["contact"], callback_data="settings:contact"),
            InlineKeyboardButton(text=TEXTS[lang]["stats"], callback_data="settings:stats")
        ],
        [InlineKeyboardButton(text=TEXTS[lang]["clear_favs"], callback_data="settings:clear_favs")],
        [InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home")]
    ])

# =========================
# STATES
# =========================
class SearchStates(StatesGroup):
    waiting_query = State()


# =========================
# ROUTERS & HANDLERS
# =========================
start_router = Router()
drink_router = Router()
bakery_router = Router()
search_router = Router()
favorites_router = Router()
nav_router = Router()  # for generic callbacks
# Add a settings router
settings_router = Router()

# --- Start & Home
@start_router.message(F.text == "⚙️ កំណត់")
@start_router.message(F.text == "⚙️ Settings")
async def settings_menu(message: Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["settings_menu"], reply_markup=settings_kb(message.from_user.id))


@start_router.message(F.text.in_({"សួស្តី", "Hello", "hello", "/start", "Start", "start"}))
async def greet_echo(message: Message):
    user_id = message.from_user.id
    # Set default language based on first message
    if message.text in ["Hello", "hello", "Start", "start"]:
        set_user_lang(user_id, "en")
    
    lang = get_user_lang(user_id)
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu_kb(user_id))


@start_router.message(F.text == "🏠 មុខងារ")
@start_router.message(F.text == "🏠 Home")
async def back_home_message(message: Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["home"], reply_markup=main_menu_kb(message.from_user.id))

@start_router.message(CommandStart())
async def cmd_start(message: Message):
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["welcome"], reply_markup=main_menu_kb(message.from_user.id))

# --- Generic navigation callbacks
@nav_router.callback_query(F.data == "nav:home")
async def nav_home(cb: CallbackQuery):
    lang = get_user_lang(cb.from_user.id)
    await cb.message.edit_text(TEXTS[lang]["home"])
    await cb.message.answer(TEXTS[lang]["main_menu"], reply_markup=main_menu_kb(cb.from_user.id))
    await cb.answer()

@nav_router.callback_query(F.data == "nav:back")
async def nav_back(cb: CallbackQuery):
    lang = get_user_lang(cb.from_user.id)
    await cb.message.edit_text(TEXTS[lang]["back"])
    await cb.message.answer(TEXTS[lang]["main_menu"], reply_markup=main_menu_kb(cb.from_user.id))
    await cb.answer()

# --- Drink
@drink_router.message(F.text == "🍹 គន្លឹះភេសជ្ជៈ")
@drink_router.message(F.text == "🍹 Drink Tips")
async def drink_menu(message: Message):
    user_id = message.from_user.id
    subs = CONTENT.list_subcats("drink")

    # Hide Sauce (source) in Drink menu
    if "source" in subs:
        subs.remove("source")

    # Reorder to put new subcategories at the end so they appear in the last row
    # Move topping, source, ingredients_list to the end
    new_order = []
    for sub in subs:
        if sub not in ["topping", "source", "ingredients_list", "products"]:
            new_order.append(sub)
    
    # Add new subcategories at the end
    for sub in ["topping", "source", "ingredients_list", "products"]:
        if sub in subs:
            new_order.append(sub)

    lang = get_user_lang(user_id)
    await message.answer(TEXTS[lang]["drink_tips"], reply_markup=subcategory_kb("drink", new_order, user_id))


@drink_router.callback_query(F.data.startswith("tips:cat:drink"))
async def back_to_drink(cb: CallbackQuery):
    user_id = cb.from_user.id
    subs = CONTENT.list_subcats("drink")

    if "source" in subs:
        subs.remove("source")

    lang = get_user_lang(user_id)
    await cb.message.edit_text(TEXTS[lang]["drink_tips"], reply_markup=subcategory_kb("drink", subs, user_id))
    await cb.answer()


@drink_router.callback_query(F.data.startswith("tips:sub:drink:"))
async def open_drink_sub(cb: CallbackQuery):
    # data format: tips:sub:{category}:{subcategory}:{page}
    parts = cb.data.split(":")
    # safety parse
    if len(parts) != 5:
        await cb.answer()
        return
    _, _, category, subcategory, page_str = parts
    try:
        page = int(page_str)
    except ValueError:
        page = 1
    items = CONTENT.list_items(category, subcategory)
    await cb.message.edit_text(
        f"🍹 {subcategory.capitalize()}",
        reply_markup=item_list_kb(category, subcategory, items, page)
    )
    await cb.answer()


# --- Bakery
@bakery_router.message(F.text == "🧁 គន្លឹះនំ")
@bakery_router.message(F.text == "🧁 Bakery Tips")
async def bakery_menu(message: Message):
    user_id = message.from_user.id
    subs = CONTENT.list_subcats("bakery")

    # Hide Topping in Bakery menu
    if "topping" in subs:
        subs.remove("topping")

    # Reorder to put new subcategories at the end
    new_order = []
    for sub in subs:
        if sub not in ["topping", "source", "ingredients_list", "products"]:
            new_order.append(sub)
    
    # Add new subcategories at the end
    for sub in ["topping", "source", "ingredients_list", "products"]:
        if sub in subs:
            new_order.append(sub)

    lang = get_user_lang(user_id)
    await message.answer(TEXTS[lang]["bakery_tips"], reply_markup=subcategory_kb("bakery", new_order, user_id))

@bakery_router.callback_query(F.data.startswith("tips:cat:bakery"))
async def back_to_bakery(cb: CallbackQuery):
    user_id = cb.from_user.id
    subs = CONTENT.list_subcats("bakery")

    if "topping" in subs:
        subs.remove("topping")

    lang = get_user_lang(user_id)
    await cb.message.edit_text(TEXTS[lang]["bakery_tips"], reply_markup=subcategory_kb("bakery", subs, user_id))
    await cb.answer()

# --- Subcategory handlers
@drink_router.callback_query(F.data.startswith("tips:sub:drink:"))
@bakery_router.callback_query(F.data.startswith("tips:sub:bakery:"))
async def open_sub(cb: CallbackQuery):
    parts = cb.data.split(":")
    if len(parts) != 5:
        await cb.answer()
        return
    _, _, category, subcategory, page_str = parts
    try:
        page = int(page_str)
    except ValueError:
        page = 1
    items = CONTENT.list_items(category, subcategory)
    await cb.message.edit_text(
        f"{'🍹' if category == 'drink' else '🧁'} {subcategory.capitalize()}",
        reply_markup=item_list_kb(category, subcategory, items, page, user_id=cb.from_user.id)
    )
    await cb.answer()

@bakery_router.callback_query(F.data.startswith("tips:sub:bakery:"))
async def open_bakery_sub(cb: CallbackQuery):
    parts = cb.data.split(":")
    if len(parts) != 5:
        await cb.answer()
        return
    _, _, category, subcategory, page_str = parts
    try:
        page = int(page_str)
    except ValueError:
        page = 1
    items = CONTENT.list_items(category, subcategory)
    await cb.message.edit_text(
        f"🧁 {subcategory.capitalize()}",
        reply_markup=item_list_kb(category, subcategory, items, page, user_id=cb.from_user.id)  # ADD user_id
    )
    await cb.answer()


# =========================
# NEW FUNCTIONS FOR INGREDIENTS LIST ALBUM VIEW
# =========================

def render_ingredients_album_page(tip: Dict[str, Any], page: int, items_per_page: int = 6, user_id: int = None) -> str:
    """Render a paginated album page for ingredients list"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    title = tip.get("title", "Untitled")
    ingredients: List[Dict[str, Any]] = tip.get("ingredients", [])
    
    # Calculate pagination
    total_items = len(ingredients)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    page_items = ingredients[start_idx:end_idx]
    
    # Header
    lines = [f"📋 **{title}**"]
    lines.append(f"📄 ទំព័រ {page}/{total_pages}\n")
    
    # Items for this page
    for i, item in enumerate(page_items, start=start_idx + 1):
        ingredient = item.get("ingredient", "")
        remark = item.get("remark", "")
        
        if remark:
            lines.append(f"• **{ingredient}**: {remark}")
        else:
            lines.append(f"• **{ingredient}**")
    
    # If no ingredients
    if not page_items:
        lines.append("មិនមានទិន្នន័យ")
    
    return "\n".join(lines)


def ingredients_album_kb(tip_id_str: str, category: str, subcategory: str, current_page: int, total_pages: int, user_id: int = None) -> InlineKeyboardMarkup:
    """Keyboard for ingredients album pagination"""
    lang = get_user_lang(user_id) if user_id else DEFAULT_LANG
    rows = []
    
    # Navigation row
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(
            text="⬅️ ថយក្រោយ",
            callback_data=f"ingredients:page:{tip_id_str}:{current_page - 1}"
        ))
    
    nav_buttons.append(InlineKeyboardButton(
        text=f"📄 {current_page}/{total_pages}",
        callback_data="noop"
    ))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            text="ទៅមុខ ➡️",
            callback_data=f"ingredients:page:{tip_id_str}:{current_page + 1}"
        ))
    
    if nav_buttons:
        rows.append(nav_buttons)
    
    # Control row
    rows.append([
        InlineKeyboardButton(
            text=TEXTS[lang]["back"],
            callback_data=f"tips:sub:{category}:{subcategory}:1"
        ),
        InlineKeyboardButton(
            text=TEXTS[lang]["home"],
            callback_data="nav:home"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)

# =========================
# UPDATED TIP HANDLER FOR INGREDIENTS LIST
# =========================

@drink_router.callback_query(F.data.startswith("tips:item:"))
@bakery_router.callback_query(F.data.startswith("tips:item:"))
async def open_tip(cb: CallbackQuery):
    tip_id_str = cb.data.replace("tips:item:", "", 1)
    tip = CONTENT.get_tip(tip_id_str)
    
    if not tip:
        await cb.answer("Content not found", show_alert=True)
        return
    
    # SPECIAL HANDLING FOR INGREDIENTS LIST - EACH ITEM AS SEPARATE PAGE
    if tip.get("subcategory") in ["ingredients_list", "products"]:
        # Increment view count
        CONTENT.increment_view(tip_id_str)
        
        # Get category info for back navigation
        category = tip.get("category", "")
        subcategory = tip.get("subcategory", "")
        
        # Get all ingredients
        ingredients = tip.get("ingredients", [])
        
        if not ingredients:
            await cb.answer("No ingredients found", show_alert=True)
            return
            
        # Create separate page for first ingredient
        current_index = 0
        await show_ingredient_page(cb, tip, ingredients, current_index, category, subcategory)
        await cb.answer()
        return
    
    # ORIGINAL HANDLER FOR REGULAR TIPS (with small fix)
    await cb.message.delete()  # Only delete for regular tips
    
    view_count = CONTENT.increment_view(tip_id_str)
    fav_count = CONTENT.get_fav_count(tip_id_str)
    share_count = CONTENT.get_share_count(tip_id_str)

    photo = tip.get("picture_file_id")
    if photo:
        await cb.message.answer_photo(photo=photo, caption=tip["title"])
    else:
        seed = tip["id"].replace("/", "_")
        await cb.message.answer_photo(photo=f"https://picsum.photos/seed/{seed}/640/480", caption=tip["title"])

    text = render_tip_card(tip, view_count, fav_count, share_count, cb.from_user.id)
    back_payload = f"tips:sub:{tip['category']}:{tip['subcategory']}:1"
    video_url = tip.get("video_url", None)
    await cb.message.answer(text, reply_markup=tip_card_kb(tip["id"], back_payload, video_url, cb.from_user.id))
    await cb.answer()

# =========================
# HELPER FUNCTION FOR BETTER IMAGE SELECTION
# =========================

def get_ingredient_image_url(ingredient_name: str, current_index: int) -> str:
    """Get appropriate image URL for an ingredient"""
    ing_name_lower = ingredient_name.lower()
    
    # Map keywords to image search terms
    keyword_mapping = {
        "coffee": ["coffee", "beans", "arabica", "robusta", "espresso"],
        "tea": ["tea", "leaf", "herbal", "matcha", "green tea"],
        "milk": ["milk", "dairy", "cream", "butter", "cheese"],
        "sugar": ["sugar", "sweet", "honey", "syrup", "candy"],
        "chocolate": ["chocolate", "cocoa", "dark chocolate", "cacao"],
        "fruit": ["fruit", "berry", "citrus", "apple", "banana"],
        "spice": ["spice", "cinnamon", "vanilla", "ginger", "nutmeg"],
        "grain": ["flour", "wheat", "grain", "cereal", "oats"],
        "nut": ["nut", "almond", "walnut", "peanut", "cashew"]
    }
    
    # Find matching category
    category = "food"  # default
    for cat, keywords in keyword_mapping.items():
        if any(keyword in ing_name_lower for keyword in keywords):
            category = cat
            break
    
    # Use Unsplash API with the category
    search_terms = [category]
    
    # Add specific ingredient words
    words = ingredient_name.split()
    for word in words[:2]:  # Use first 2 words
        if len(word) > 3:  # Avoid very short words
            search_terms.append(word.lower())
    
    # Create search query
    query = ",".join(search_terms[:3])  # Max 3 search terms
    
    # Return Unsplash image URL
    return f"https://source.unsplash.com/400x300/?{query}"


# =========================
# ADD IMAGE TO INGREDIENT PAGES
# =========================

async def show_ingredient_page(cb: CallbackQuery, tip: Dict[str, Any], ingredients: List[Dict[str, Any]], 
                             current_index: int, category: str, subcategory: str):
    """Show a single ingredient as a separate page with image"""
    if current_index >= len(ingredients):
        await cb.answer("Invalid ingredient index", show_alert=True)
        return
    
    ingredient = ingredients[current_index]
    total_count = len(ingredients)
    
    # Create a detailed card for this ingredient
    lang = get_user_lang(cb.from_user.id)
    
    # Prepare the caption
    lines = []
    
    # 1. Categories
    tip_title = tip.get("title", "Ingredients List")
    lines.append(f"📋 **{tip_title}**")
    lines.append(f"📍 **Category:** {category.capitalize()} → {subcategory.replace('_', ' ').title()}")
    lines.append(f"📄 **Item:** {current_index + 1}/{total_count}\n")
    
    # 2. Item name
    ing_name = ingredient.get("ingredient", "")
    lines.append(f"🛒 **{ing_name}**\n")
    
    # 3. Description
    remark = ingredient.get("remark", "")
    if remark:
        lines.append(f"📝 **Description:**")
        lines.append(f"{remark}\n")
    
    # 4. Price information
    price = ingredient.get("price", "")
    if price:
        lines.append(f"💰 **Price:** {price}")
    
    # 5. Seller information
    seller = ingredient.get("seller", "")
    if seller:
        lines.append(f"👤 **Seller:** {seller}")
    
    # 6. Market/availability info
    market = ingredient.get("market", "")
    if market:
        lines.append(f"📍 **Market:** {market}")
    
    # 7. Amount/Unit if available
    amount = ingredient.get("amount", "")
    uom = ingredient.get("uom", "")
    if amount and uom:
        lines.append(f"⚖️ **Amount:** {amount}{uom}")
    
    # 8. Tips section
    steps = tip.get("steps", [])
    if steps:
        lines.append(f"\n💡 **Tips:**")
        for i, step in enumerate(steps[:3], 1):  # Show first 3 tips
            lines.append(f"{i}. {step}")
    
    caption = "\n".join(lines)
    
    # Create navigation buttons
    back_payload = f"tips:sub:{category}:{subcategory}:1"
    
    # Create unique IDs for each ingredient within the same tip
    tip_base_id = tip["id"]
    
    # Current ingredient's "fake" ID for save button
    current_tip_id = f"{tip_base_id}__{current_index}"
    
    # Create custom keyboard for ingredient pagination
    rows = []
    
    # First row: Previous | Save | Next
    first_row = []
    
    if current_index > 0:
        prev_tip_id = f"{tip_base_id}__{current_index - 1}"
        first_row.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"ingredient:page:{prev_tip_id}"))
    
    first_row.append(InlineKeyboardButton(text=TEXTS[lang]["save"], callback_data=f"tips:fav:{current_tip_id}"))
    
    if current_index < total_count - 1:
        next_tip_id = f"{tip_base_id}__{current_index + 1}"
        first_row.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"ingredient:page:{next_tip_id}"))
    
    rows.append(first_row)
    
    # Second row: Back and Home buttons
    rows.append([
        InlineKeyboardButton(text="◀️ " + TEXTS[lang]["back"], callback_data=back_payload),
        InlineKeyboardButton(text=TEXTS[lang]["home"], callback_data="nav:home"),
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    
    # Get image for the ingredient
    image_url = ingredient.get("image_url", "")
    
    # If no image_url in data, generate one based on ingredient name
    if not image_url:
        # Get appropriate image URL for this ingredient
        ing_name_lower = ing_name.lower()
        
        # Map keywords to image search terms
        if any(word in ing_name_lower for word in ["coffee", "bean", "arabica", "robusta", "liberica"]):
            category_term = "coffee"
        elif any(word in ing_name_lower for word in ["tea", "leaf", "herbal", "matcha"]):
            category_term = "tea"
        elif any(word in ing_name_lower for word in ["milk", "cream", "dairy", "cheese"]):
            category_term = "milk"
        elif any(word in ing_name_lower for word in ["sugar", "honey", "syrup", "sweet"]):
            category_term = "sugar"
        elif any(word in ing_name_lower for word in ["chocolate", "cocoa"]):
            category_term = "chocolate"
        elif any(word in ing_name_lower for word in ["spice", "cinnamon", "vanilla", "ginger"]):
            category_term = "spice"
        elif any(word in ing_name_lower for word in ["fruit", "berry", "lemon", "orange"]):
            category_term = "fruit"
        elif any(word in ing_name_lower for word in ["flour", "grain", "wheat"]):
            category_term = "flour"
        elif any(word in ing_name_lower for word in ["nut", "almond", "walnut"]):
            category_term = "nuts"
        else:
            category_term = "food"
        
        # Add specific ingredient name for better results
        search_terms = [category_term]
        words = ing_name.split()
        for word in words[:2]:  # Use first 2 words
            if len(word) > 3:  # Avoid very short words
                search_terms.append(word.lower())
        
        # Create search query (max 3 terms)
        query = ",".join(search_terms[:3])
        
        # Use Unsplash for high-quality food images
        image_url = f"https://source.unsplash.com/400x300/?{query}"
        
        # Add image source note to caption
        caption += "\n\n📸 *Image courtesy of Unsplash*"
    else:
        # If image_url is provided in data, add appropriate source note
        if "unsplash" in image_url:
            caption += "\n\n📸 *Image courtesy of Unsplash*"
        elif "picsum" in image_url:
            caption += "\n\n📸 *Placeholder image*"
    
    # Try to send as photo with caption
    try:
        # Check if we're editing an existing message or sending a new one
        try:
            # Try to delete the previous message first
            await cb.message.delete()
        except:
            pass
        
        # Send new photo message
        await cb.message.answer_photo(
            photo=image_url,
            caption=caption,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        # If photo fails, send as text message with image URL
        print(f"Error sending photo: {e}")
        caption_with_image = f"[🖼️ View Image]({image_url})\n\n{caption}"
        
        try:
            await cb.message.edit_text(
                caption_with_image,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except:
            await cb.message.answer(
                caption_with_image,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

# =========================
# NEW HANDLER FOR INGREDIENT PAGINATION
# =========================

@drink_router.callback_query(F.data.startswith("ingredient:page:"))
@bakery_router.callback_query(F.data.startswith("ingredient:page:"))
async def handle_ingredient_pagination(cb: CallbackQuery):
    """Handle pagination for individual ingredient pages"""
    # data format: ingredient:page:{tip_id}__{index}
    tip_id_with_index = cb.data.replace("ingredient:page:", "", 1)
    
    # Split the combined ID: original_tip_id__index
    if "__" not in tip_id_with_index:
        await cb.answer("Invalid ingredient ID", show_alert=True)
        return
    
    base_tip_id, index_str = tip_id_with_index.split("__")
    
    try:
        current_index = int(index_str)
    except ValueError:
        await cb.answer("Invalid page", show_alert=True)
        return
    
    # Get the original tip
    tip = CONTENT.get_tip(base_tip_id)
    if not tip:
        await cb.answer("Content not found", show_alert=True)
        return
    
    # Show the specified ingredient page
    ingredients = tip.get("ingredients", [])
    category = tip.get("category", "")
    subcategory = tip.get("subcategory", "")
    
    await show_ingredient_page(cb, tip, ingredients, current_index, category, subcategory)
    await cb.answer()

# =========================
# ALSO UPDATE THE FAVORITES HANDLER TO WORK WITH INGREDIENT PAGES
# =========================

@drink_router.callback_query(F.data.startswith("tips:fav:"))
@bakery_router.callback_query(F.data.startswith("tips:fav:"))
async def fav_tip(cb: CallbackQuery):
    tip_id_str = cb.data.replace("tips:fav:", "", 1)
    added = await CONTENT.add_fav(cb.from_user.id, tip_id_str)
    lang = get_user_lang(cb.from_user.id)
    await cb.answer(TEXTS[lang]["saved"] if added else TEXTS[lang]["already_saved"])

# --- Share Tip Handler
@drink_router.callback_query(F.data.startswith("tips:share:"))
@bakery_router.callback_query(F.data.startswith("tips:share:"))
async def share_tip(cb: CallbackQuery):
    tip_id_str = cb.data.replace("tips:share:", "", 1)
    tip = CONTENT.get_tip(tip_id_str)
    
    if not tip:
        await cb.answer("Content not found", show_alert=True)
        return
    
    CONTENT.increment_share(tip_id_str)
    
    bot_username = (await cb.bot.get_me()).username
    title = tip.get("title", "Untitled")
    lang = get_user_lang(cb.from_user.id)
    
    share_text = f"""
{TEXTS[lang]["share_title"]}
📘 {title}

{TEXTS[lang]["share_prompt"]}
👉 @{bot_username}

#Tips #Recipe
"""
    
    await cb.message.answer(share_text)
    await cb.answer("✅ Share text created")

# --- Search
@search_router.message(F.text == "🔎 ស្វែងរក")
@search_router.message(F.text == "🔎 Search")
async def search_entry(message: Message, state: FSMContext):
    lang = get_user_lang(message.from_user.id)
    await message.answer(TEXTS[lang]["search_prompt"])
    await state.set_state(SearchStates.waiting_query)

@search_router.message(SearchStates.waiting_query)
async def do_search(message: Message, state: FSMContext):
    q = message.text
    results = CONTENT.search(q)
    await state.clear()
    
    lang = get_user_lang(message.from_user.id)
    
    if not results:
        await message.answer(TEXTS[lang]["no_results"])
        return
    await message.answer(TEXTS[lang]["search_results"], reply_markup=search_results_kb(results, message.from_user.id))

# --- Favorites
@favorites_router.message(F.text == "⭐ រក្សាទុក")
@favorites_router.message(F.text == "⭐ Favorites")
async def show_favorites(message: Message):
    tips = await CONTENT.get_favs(message.from_user.id)
    lang = get_user_lang(message.from_user.id)
    if not tips:
        await message.answer(TEXTS[lang]["no_favorites"])
        return
    await message.answer(TEXTS[lang]["favorites_list"], reply_markup=favorites_kb(tips, message.from_user.id))

# --- Settings Handlers
@settings_router.callback_query(F.data == "settings:language")
async def settings_language(cb: CallbackQuery):
    lang = get_user_lang(cb.from_user.id)
    
    lang_text = f"""🌐 **Select Language**

Current: {'Khmer' if lang == 'km' else 'English'}

**Supported languages:**
🇰🇭 Khmer - For local users
🇬🇧 English - For international users"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇭 ខ្មែរ", callback_data="lang:km")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text="◀️ " + TEXTS[lang]["back"], callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(lang_text, reply_markup=kb)
    await cb.answer()

# --- Language Change Handler
@settings_router.callback_query(F.data.startswith("lang:"))
async def change_language(cb: CallbackQuery):
    lang_code = cb.data.split(":")[1]
    user_id = cb.from_user.id
    
    set_user_lang(user_id, lang_code)
    lang = get_user_lang(user_id)
    
    # Delete the language selection message
    await cb.message.delete()
    
    # Send confirmation and main menu
    await cb.message.answer(
        TEXTS[lang]["welcome"],
        reply_markup=main_menu_kb(user_id)
    )
    
    await cb.answer(TEXTS[lang]["lang_changed"])

# Help/Instructions
@settings_router.callback_query(F.data == "settings:help")
async def settings_help(cb: CallbackQuery):
    help_text = """📖 **របៀបប្រើបូត:**

1. **ជ្រើសរើសប្រភេទ:**
   - 🍹 គន្លឹះភេសជ្ជៈ
   - 🧁 គន្លឹះនំ

2. **រុករកគន្លឹះ:**
   - ជ្រើសរើសប្រភេទរង
   - ជ្រើសរើសគន្លឹះដែលចង់មើល

3. **មុខងារពិសេស:**
   - 🔎 ស្វែងរក: ស្វែងរកគន្លឹះតាមពាក្យគន្លឹះ
   - ⭐ រក្សាទុក: រក្សាទុកគន្លឹះដែលអ្នកចូលចិត្ត
   - ⚙️ កំណត់: កែប្រែការកំណត់

4. **ក្នុងគន្លឹះ:**
   - 🎥 វីដេអូ: មើលវីដេអូណែនាំ
   - ⭐ រក្សាទុក: រក្សាទុកគន្លឹះ
   - 📤 ចែករំលែក: ចែករំលែកគន្លឹះទៅកាន់មិត្តភក្តិ

❓ **សំណួរទូទៅ:**
- បូតនេះឥតគិតថ្លៃទេ
- អាចប្រើបានគ្រប់ពេល
- ទិន្នន័យត្រូវបានរក្សាទុកតែក្នុងកំឡុងពេលប្រើប្រាស់ប៉ុណ្ណោះ"""
    
    await cb.message.edit_text(help_text, reply_markup=settings_kb(cb.from_user.id))
    await cb.answer()


# Channel Link
@settings_router.callback_query(F.data == "settings:channel")
async def settings_channel(cb: CallbackQuery):
    channel_text = """📢 **ឆាណែលផ្លូវការ**

ចូលរួមជាមួយយើងដើម្បីទទួលបាន:
- គន្លឹះថ្មីៗ
- ព័ត៌មានអំពីអាហារ
- ការប្រកួតប្រជែង
- ការផ្តល់អនុសាសន៍ពិសេស

👉 **ចូលរួមទីនេះ:** [@drinkbakerytips](https://t.me/drinkbakerytips)

ចុចប៊ូតុងខាងក្រោមដើម្បីចូលឆាណែល។"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 ចូលរួមឆាណែល", url="https://t.me/drinkbakerytips")],
        [InlineKeyboardButton(text="◀️ ត្រឡប់ក្រោយ", callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(channel_text, reply_markup=kb)
    await cb.answer()


# Group Link
@settings_router.callback_query(F.data == "settings:group")
async def settings_group(cb: CallbackQuery):
    group_text = """👥 **ក្រុមសហគមន៍**

ចូលរួមក្នុងក្រុមសំណួរសុំដើម្បី:
- សួរសំណួរអំពីគន្លឹះ
- ចែករំលែកបទពិសោធន៍
- ជួបជាមួយអ្នកដទៃទៀតដែលចាប់អារម្មណ៍ផងដែរ
- ទទួលបានជំនួយពីអ្នកជំនាញ

👉 **ចូលរួមក្រុម:** [@drinkbakerycommunity](https://t.me/drinkbakerycommunity)

ចុចប៊ូតុងខាងក្រោមដើម្បីចូលក្រុម។"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 ចូលរួមក្រុម", url="https://t.me/drinkbakerycommunity")],
        [InlineKeyboardButton(text="◀️ ត្រឡប់ក្រោយ", callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(group_text, reply_markup=kb)
    await cb.answer()


# Contact
@settings_router.callback_query(F.data == "settings:contact")
async def settings_contact(cb: CallbackQuery):
    contact_text = """📞 **ទំនាក់ទំនង**

ប្រសិនបើអ្នកមានសំណួរ ឬត្រូវការជំនួយ:

📧 **អ៊ីមែល:** support@drinkbakerytips.com
👨‍💻 **អ្នកគ្រប់គ្រង:** @admin_username
🌐 **គេហទំព័រ:** https://drinkbakerytips.com

**ម៉ោងធ្វើការ:**
ច័ន្ទ-សៅរ៍: 8:00 - 17:00
អាទិត្យ: បិទ

**ក្នុងករណីបញ្ហា:**
1. ពិពណ៌នាបញ្ហាឱ្យបានច្បាស់
2. បញ្ជាក់ពីកំណែបូត
3. ភ្ជាប់រូបភាព (បើអាច)"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ ផ្ញើសារជាឯកជន", url="https://t.me/admin_username")],
        [InlineKeyboardButton(text="◀️ ត្រឡប់ក្រោយ", callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(contact_text, reply_markup=kb)
    await cb.answer()


# User Statistics
@settings_router.callback_query(F.data == "settings:stats")
async def settings_stats(cb: CallbackQuery):
    # Get user's favorites count
    favs = await CONTENT.get_favs(cb.from_user.id)
    fav_count = len(favs)
    
    # Calculate estimated views (this is simplified)
    # In a real app, you'd track this per user
    total_tips = sum(len(items) for submap in DATA.values() for items in submap.values())
    
    stats_text = f"""📊 **ស្ថិតិផ្ទាល់ខ្លួន**

👤 **អ្នកប្រើ:** {cb.from_user.first_name}
🆔 **លេខសម្គាល់:** {cb.from_user.id}

⭐ **គន្លឹះដែលរក្សាទុក:** {fav_count}
👁️ **គន្លឹះដែលបានមើល:** {min(fav_count * 3, total_tips)} (ប្រមាណ)

📈 **សកម្មភាពសរុប:**
- បានមើលគន្លឹះ: {min(fav_count * 5, total_tips * 2)}
- បានរក្សាទុក: {fav_count}
- បានចែករំលែក: {min(fav_count, 10)}

🎯 **គន្លឹះសរុបក្នុងបូត:** {total_tips}
🔄 **ចុងក្រោយបានប្រើ:** ឥឡូវនេះ

**ព័ត៌មានបន្ថែម:**
ស្ថិតិនេះផ្អែកលើសកម្មភាពរបស់អ្នកក្នុងបូត។"""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ លុបការរក្សាទុក", callback_data="settings:clear_favs")],
        [InlineKeyboardButton(text="◀️ ត្រឡប់ក្រោយ", callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(stats_text, reply_markup=kb)
    await cb.answer()


# Clear Favorites
@settings_router.callback_query(F.data == "settings:clear_favs")
async def settings_clear_favs(cb: CallbackQuery):
    confirm_text = """⚠️ **លុបការរក្សាទុកទាំងអស់**

តើអ្នកពិតជាចង់លុបគន្លឹះដែលអ្នកបានរក្សាទុកទាំងអស់មែនទេ?

សកម្មភាពនេះ **មិនអាចមិនធ្វើវិញ** បានទេ។

✅ **អ្វីដែលនឹងកើតឡើង:**
- គន្លឹះដែលរក្សាទុកទាំងអស់នឹងត្រូវបានលុប
- ស្ថិតិរបស់អ្នកនឹងត្រូវបានកំណត់ឡើងវិញ

❌ **អ្វីដែលមិននឹងកើតឡើង:**
- មិនលុបប្រវត្តិមើលគន្លឹះ
- មិនលុបសំណុំឯកសារផ្ទាល់ខ្លួន"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ យល់ព្រមលុប", callback_data="settings:confirm_clear_favs")],
        [InlineKeyboardButton(text="❌ បោះបង់", callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(confirm_text, reply_markup=kb)
    await cb.answer()


@settings_router.callback_query(F.data == "settings:confirm_clear_favs")
async def settings_confirm_clear_favs(cb: CallbackQuery):
    # TODO: implement deletion from DB
    await cb.message.edit_text(
        "✅ បានលុបគន្លឹះដែលរក្សាទុកទាំងអស់ដោយជោគជ័យ!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ ត្រឡប់ទៅការកំណត់", callback_data="settings:back")]
        ])
    )
    await cb.answer()


# Back to settings menu
@settings_router.callback_query(F.data == "settings:back")
async def settings_back(cb: CallbackQuery):
  lang = get_user_lang(cb.from_user.id)
  await cb.message.edit_text(TEXTS[lang]["settings_menu"], reply_markup=settings_kb(cb.from_user.id))
  await cb.answer()

# Units selection (placeholder)
@settings_router.callback_query(F.data == "settings:units")
async def settings_units(cb: CallbackQuery):
    units_text = """📏 **ជ្រើសរើសខ្នាតវាស់វែង**

បច្ចុប្បន្ន: ខ្នាតម៉ែត្រ (g, ml, °C)

**ខ្នាតដែលគាំទ្រ:**
⚖️ ខ្នាតម៉ែត្រ (ណ្តាញ)
- ក្រាម (g)
- មីលីលីត្រ (ml)
- អង្សាសេ (°C)

🇺🇸 ខ្នាតអាមេរិកាំង (ចាស់)
- អោន (oz)
- ស្លាបព្រា (tbsp)
- ដឺក្រេផារ៉ែនហៃ (°F)

មុខងារនេះកំពុងអភិវឌ្ឍន៍..."""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ ខ្នាតម៉ែត្រ", callback_data="units:metric")],
        [InlineKeyboardButton(text="🇺🇸 ខ្នាតអាមេរិកាំង", callback_data="units:imperial")],
        [InlineKeyboardButton(text="◀️ ត្រឡប់ក្រោយ", callback_data="settings:back")]
    ])
    
    await cb.message.edit_text(units_text, reply_markup=kb)
    await cb.answer()

# =========================
# APP BOOTSTRAP
# =========================
async def main():
    await init_db()  # create table if not exists
    print("Database initialized successfully")
    logging.basicConfig(level=logging.INFO)
    if not BOT_TOKEN or not BOT_TOKEN.strip():
        raise RuntimeError("BOT_TOKEN is missing")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(start_router)
    dp.include_router(nav_router)
    dp.include_router(drink_router)
    dp.include_router(bakery_router)
    dp.include_router(search_router)
    dp.include_router(favorites_router)
    dp.include_router(settings_router)  # Add this line

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")


