import os
print("=== ALL ENVIRONMENT VARIABLES ===")
for key in sorted(os.environ.keys()):
    print(key)
print("=================================")
print(f"BOT_TOKEN = {repr(os.environ.get('BOT_TOKEN'))}")
print(f"DATABASE_URL = {repr(os.environ.get('DATABASE_URL'))}")
