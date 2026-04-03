from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.enums import ChatMemberStatus, ChatType

from utils.resolvers import (
    ResolveError,
    resolve_tg_chat,
    resolve_tg_forward_source,
    validate_tg_channel_access,
)


class TelegramResolverTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_tg_channel_access_accepts_admin_channel(self) -> None:
        bot = SimpleNamespace(
            get_chat=AsyncMock(
                return_value=SimpleNamespace(type=ChatType.CHANNEL),
            ),
            get_chat_member=AsyncMock(
                return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR),
            ),
            get_me=AsyncMock(),
        )

        await validate_tg_channel_access(bot, -100123, bot_user_id=77)

        bot.get_chat.assert_awaited_once_with(-100123)
        bot.get_chat_member.assert_awaited_once_with(-100123, 77)
        bot.get_me.assert_not_called()

    async def test_validate_tg_channel_access_rejects_non_channel(self) -> None:
        bot = SimpleNamespace(
            get_chat=AsyncMock(
                return_value=SimpleNamespace(type=ChatType.SUPERGROUP),
            ),
            get_chat_member=AsyncMock(),
            get_me=AsyncMock(),
        )

        with self.assertRaisesRegex(ResolveError, "is not a channel"):
            await validate_tg_channel_access(bot, -100123, bot_user_id=77)

        bot.get_chat_member.assert_not_called()

    async def test_validate_tg_channel_access_rejects_non_admin(self) -> None:
        bot = SimpleNamespace(
            get_chat=AsyncMock(
                return_value=SimpleNamespace(type=ChatType.CHANNEL),
            ),
            get_chat_member=AsyncMock(
                return_value=SimpleNamespace(status=ChatMemberStatus.LEFT),
            ),
            get_me=AsyncMock(),
        )

        with self.assertRaisesRegex(ResolveError, "not an administrator"):
            await validate_tg_channel_access(bot, -100123, bot_user_id=77)

    async def test_validate_tg_channel_access_fetches_bot_identity_when_missing(self) -> None:
        bot = SimpleNamespace(
            get_chat=AsyncMock(
                return_value=SimpleNamespace(type=ChatType.CHANNEL),
            ),
            get_chat_member=AsyncMock(
                return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR),
            ),
            get_me=AsyncMock(return_value=SimpleNamespace(id=77)),
        )

        await validate_tg_channel_access(bot, -100123)

        bot.get_me.assert_awaited_once_with()
        bot.get_chat_member.assert_awaited_once_with(-100123, 77)

    async def test_resolve_tg_forward_source_checks_public_channel_access(self) -> None:
        bot = SimpleNamespace(
            get_chat=AsyncMock(
                return_value=SimpleNamespace(
                    id=-100123,
                    type=ChatType.CHANNEL,
                ),
            ),
            get_chat_member=AsyncMock(
                return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR),
            ),
            get_me=AsyncMock(),
        )

        display, chat_id = await resolve_tg_forward_source(
            bot,
            "@example_channel",
            bot_user_id=77,
        )

        self.assertEqual(display, "@example_channel")
        self.assertEqual(chat_id, -100123)
        bot.get_chat.assert_awaited_once_with("@example_channel")
        bot.get_chat_member.assert_awaited_once_with(-100123, 77)

    async def test_resolve_tg_forward_source_rejects_inaccessible_numeric_id(self) -> None:
        bot = SimpleNamespace(
            get_chat=AsyncMock(side_effect=Exception("chat not found")),
            get_chat_member=AsyncMock(),
            get_me=AsyncMock(),
        )

        with self.assertRaisesRegex(ResolveError, "Bot has no access"):
            await resolve_tg_forward_source(bot, "-100123", bot_user_id=77)

        bot.get_chat_member.assert_not_called()

    async def test_numeric_resolve_stays_permissive_for_remove_flow(self) -> None:
        bot = SimpleNamespace(get_chat=AsyncMock())

        display, chat_id = await resolve_tg_chat(bot, "-100123")

        self.assertEqual(display, "-100123")
        self.assertEqual(chat_id, -100123)
        bot.get_chat.assert_not_called()


if __name__ == "__main__":
    unittest.main()
