import asyncio
import logging
import signal
import os

from loader import tg_dp, tg_bot
import handlers.admin_handlers
import handlers.max_handlers
import handlers.tg_handlers

_ = (
    handlers.admin_handlers,
    handlers.max_handlers,
    handlers.tg_handlers,
)

logging.basicConfig(level=logging.INFO)


def force_exit(signum, frame):
    logging.info("Received interrupt signal, forcing exit...")
    os._exit(0)


async def main():
    logging.info("Starting bots...")

    # Register signal handlers
    signal.signal(signal.SIGINT, force_exit)
    signal.signal(signal.SIGTERM, force_exit)

    # Run telegram bot in main thread
    await tg_dp.start_polling(tg_bot)


if __name__ == "__main__":
    asyncio.run(main())
