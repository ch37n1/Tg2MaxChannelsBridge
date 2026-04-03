"""
Local Max bot helpers used by the bridge.
"""

from __future__ import annotations

import asyncio
import time
from functools import lru_cache
from typing import Any

from utils.maxapi_compat import BaseMaxBot, Chat, Chats


CHAT_CACHE_TTL_SECONDS = 600
GET_CHATS_CACHE_MAXSIZE = 128


class MaxBot(BaseMaxBot):
    """Max bot with cached chat lookup by link."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._chat_cache_lock = asyncio.Lock()

    @staticmethod
    def normalize_chat_link(value: str) -> str:
        """Normalize Max chat links to the canonical https form."""
        link = value.strip()

        if link.startswith("http://"):
            link = "https://" + link[7:]
        elif link.startswith("max.ru/"):
            link = "https://" + link

        return link.rstrip("/")

    async def get_chat(self, link: str) -> Chat:
        """Find a chat by its public link using the bot's chat list."""
        normalized_link = self.normalize_chat_link(link)
        marker: int | None = None

        while True:
            page = await self.get_chats(marker=marker)

            for chat in page.chats:
                chat_link = chat.link
                if not chat_link:
                    continue

                if self.normalize_chat_link(chat_link) == normalized_link:
                    return chat

            if page.marker is None:
                break

            marker = page.marker

        raise LookupError(f"Chat '{link}' not found")

    async def get_chats(
        self,
        count: int | None = None,
        marker: int | None = None,
    ) -> Chats:
        """Return cached chat-list pages for a short period to avoid repeated API calls."""
        ttl_bucket = int(time.monotonic() // CHAT_CACHE_TTL_SECONDS)

        async with self._chat_cache_lock:
            task = self._get_chats_task(count, marker, ttl_bucket)

        try:
            return await task
        except Exception:
            type(self)._get_chats_task.cache_clear()
            raise

    @lru_cache(maxsize=GET_CHATS_CACHE_MAXSIZE)
    def _get_chats_task(
        self,
        count: int | None,
        marker: int | None,
        ttl_bucket: int,
    ) -> asyncio.Task[Chats]:
        del ttl_bucket
        return asyncio.create_task(
            BaseMaxBot.get_chats(self, count=count, marker=marker)
        )
