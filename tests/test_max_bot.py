from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from utils.max_bot import MaxBot


class MaxBotTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        MaxBot._get_chats_task.cache_clear()
        self.addCleanup(MaxBot._get_chats_task.cache_clear)
        self.bot = object.__new__(MaxBot)
        self.bot._chat_cache_lock = asyncio.Lock()

    def test_normalize_chat_link_handles_supported_forms(self) -> None:
        self.assertEqual(
            MaxBot.normalize_chat_link("http://max.ru/example/"),
            "https://max.ru/example",
        )
        self.assertEqual(
            MaxBot.normalize_chat_link("max.ru/example"),
            "https://max.ru/example",
        )
        self.assertEqual(
            MaxBot.normalize_chat_link("https://max.ru/example/"),
            "https://max.ru/example",
        )

    async def test_get_chat_finds_match_across_pages(self) -> None:
        self.bot.get_chats = AsyncMock(
            side_effect=[
                SimpleNamespace(
                    chats=[SimpleNamespace(link="https://max.ru/other", chat_id=1)],
                    marker=50,
                ),
                SimpleNamespace(
                    chats=[SimpleNamespace(link="max.ru/target/", chat_id=42)],
                    marker=None,
                ),
            ]
        )

        chat = await MaxBot.get_chat(self.bot, "http://max.ru/target/")

        self.assertEqual(chat.chat_id, 42)
        self.assertEqual(self.bot.get_chats.await_count, 2)

    async def test_get_chat_raises_when_not_found(self) -> None:
        self.bot.get_chats = AsyncMock(
            return_value=SimpleNamespace(chats=[], marker=None)
        )

        with self.assertRaisesRegex(LookupError, "not found"):
            await MaxBot.get_chat(self.bot, "https://max.ru/missing")

    async def test_get_chats_reuses_cached_task(self) -> None:
        page = SimpleNamespace(chats=[], marker=None)
        mock_get_chats = AsyncMock(return_value=page)

        with patch("utils.max_bot.BaseMaxBot.get_chats", mock_get_chats):
            result_one = await MaxBot.get_chats(self.bot, count=10, marker=None)
            result_two = await MaxBot.get_chats(self.bot, count=10, marker=None)

        self.assertIs(result_one, page)
        self.assertIs(result_two, page)
        mock_get_chats.assert_awaited_once_with(self.bot, count=10, marker=None)

    async def test_get_chats_clears_cache_after_failure(self) -> None:
        page = SimpleNamespace(chats=[], marker=None)
        mock_get_chats = AsyncMock(side_effect=[RuntimeError("boom"), page])

        with patch("utils.max_bot.BaseMaxBot.get_chats", mock_get_chats):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                await MaxBot.get_chats(self.bot)

            result = await MaxBot.get_chats(self.bot)

        self.assertIs(result, page)
        self.assertEqual(mock_get_chats.await_count, 2)


if __name__ == "__main__":
    unittest.main()
