from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from utils import auth


class AuthTests(unittest.IsolatedAsyncioTestCase):
    def test_is_admin_accepts_env_admin(self) -> None:
        with patch.object(auth.config, "ADMIN_IDS", {100}), patch.object(
            auth.db,
            "admin_exists",
            return_value=False,
        ) as admin_exists:
            self.assertTrue(auth.is_admin(100))
            admin_exists.assert_not_called()

    def test_is_admin_checks_db_for_non_env_user(self) -> None:
        with patch.object(auth.config, "ADMIN_IDS", set()), patch.object(
            auth.db,
            "admin_exists",
            return_value=True,
        ) as admin_exists:
            self.assertTrue(auth.is_admin(200))
            admin_exists.assert_called_once_with(200)

    async def test_admin_only_ignores_messages_without_sender(self) -> None:
        handler = AsyncMock()
        wrapped = auth.admin_only(handler)
        message = SimpleNamespace(from_user=None, reply=AsyncMock())

        result = await wrapped(message)

        self.assertIsNone(result)
        handler.assert_not_awaited()
        message.reply.assert_not_awaited()

    async def test_admin_only_rejects_non_admin(self) -> None:
        handler = AsyncMock()
        wrapped = auth.admin_only(handler)
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=300),
            reply=AsyncMock(),
        )

        with patch("utils.auth.is_admin", return_value=False):
            result = await wrapped(message)

        self.assertIsNone(result)
        handler.assert_not_awaited()
        message.reply.assert_awaited_once_with("Access denied. You are not an admin.")

    async def test_admin_only_calls_wrapped_handler_for_admin(self) -> None:
        handler = AsyncMock(return_value="ok")
        wrapped = auth.admin_only(handler)
        message = SimpleNamespace(
            from_user=SimpleNamespace(id=400),
            reply=AsyncMock(),
        )

        with patch("utils.auth.is_admin", return_value=True):
            result = await wrapped(message, 1, keyword="value")

        self.assertEqual(result, "ok")
        handler.assert_awaited_once_with(message, 1, keyword="value")
        message.reply.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
