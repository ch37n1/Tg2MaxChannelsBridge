import os
import json
from dotenv import load_dotenv

load_dotenv()

MAX_BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")
MAX_CHANNEL_ID = int(os.getenv("MAX_CHANNEL_ID", 0))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

with open("./links.json") as f:
    raw_channel_links = json.loads(f.read())

CHANNEL_LINKS: dict[int, list[int]] = {}

# Postprocess to correct type
for src_id_str, dst_ids_str in raw_channel_links.items():
    CHANNEL_LINKS[int(src_id_str)] = [int(id) for id in dst_ids_str]
