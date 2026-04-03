from aiogram import Bot as TgBot, Dispatcher as TgDispatcher
import config
from utils.maxapi_compat import MaxDispatcher
from utils.max_bot import MaxBot

# Initialize Bots
max_bot = MaxBot(token=config.MAX_BOT_TOKEN)
max_dp = MaxDispatcher()

tg_bot = TgBot(token=config.TELEGRAM_BOT_TOKEN)
tg_dp = TgDispatcher()
