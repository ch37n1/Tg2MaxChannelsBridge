import os

from dotenv import load_dotenv

load_dotenv()

MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
MAX_CHANNEL_ID = int(os.getenv("MAX_CHANNEL_ID", 0))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Admin user IDs (comma-separated in env)
_admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: set[int] = {
    int(uid.strip()) for uid in _admin_ids_raw.split(",") if uid.strip()
}
