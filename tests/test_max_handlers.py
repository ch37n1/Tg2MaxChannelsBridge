from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import handlers.max_handlers as max_handlers


class MaxHandlersTests(unittest.IsolatedAsyncioTestCase):
    async def test_bot_started_sends_greeting(self) -> None:
        event = SimpleNamespace(
            bot=SimpleNamespace(send_message=AsyncMock()),
            chat_id=123,
        )

        await max_handlers.bot_started(event)

        event.bot.send_message.assert_awaited_once_with(
            chat_id=123,
            text="Привет! Отправь мне /start",
        )


if __name__ == "__main__":
    unittest.main()
