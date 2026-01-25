import asyncio
import logging
import signal
import os
import threading

from loader import max_dp, max_bot, tg_dp, tg_bot
import handlers.max_handlers
import handlers.tg_handlers

_ = (
    handlers.max_handlers,
    handlers.tg_handlers,
)

logging.basicConfig(level=logging.INFO)

def force_exit(signum, frame):
    logging.info("Received interrupt signal, forcing exit...")
    os._exit(0)

def run_max_bot():
    """Run max bot in a separate thread with its own event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(max_dp.start_polling(max_bot))

async def main():
    logging.info("Starting bots...")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, force_exit)
    signal.signal(signal.SIGTERM, force_exit)
    
    # Start max bot in a daemon thread (will be killed when main thread exits)
    max_thread = threading.Thread(target=run_max_bot, daemon=True)
    max_thread.start()
    
    # Run telegram bot in main thread
    await tg_dp.start_polling(tg_bot)

if __name__ == '__main__':
    asyncio.run(main())
