from loader import max_dp
from utils.maxapi_compat import BotStarted


@max_dp.bot_started()
async def bot_started(event: BotStarted):
    if not event.bot:
        raise ValueError('bad state')
    await event.bot.send_message(
        chat_id=event.chat_id, text="Привет! Отправь мне /start"
    )
