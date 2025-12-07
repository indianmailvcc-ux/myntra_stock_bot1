import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

MONGO_URI = os.getenv("MONGO_URI", "")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "myntra_tracker_db")
MONGO_COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "trackings")

# Interval in seconds between checks, default 10 minutes
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "600"))

# Optional: your own Telegram user ID for admin logs etc.
OWNER_ID = int(os.getenv("OWNER_ID", "0"))