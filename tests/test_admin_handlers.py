from __future__ import annotations

import io
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import handlers.admin_handlers as admin_handlers
from utils.resolvers import ResolveError


def make_message(
    *,
    text: str | None = None,
    document: object | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        document=document,
        reply=AsyncMock(),
        reply_document=AsyncMock(),
    )


class AdminHandlersTests(unittest.IsolatedAsyncioTestCase):
    async def test_handle_help_replies_with_help_text(self) -> None:
        message = make_message()

        await admin_handlers.handle_help.__wrapped__(message)

        message.reply.assert_awaited_once_with(admin_handlers.HELP_TEXT)

    async def test_handle_links_handles_empty_and_grouped_routes(self) -> None:
        empty_message = make_message()
        with patch.object(admin_handlers.db, "get_grouped_routes", return_value={}):
            await admin_handlers.handle_links.__wrapped__(empty_message)

        empty_message.reply.assert_awaited_once_with("No routes configured.")

        grouped_message = make_message()
        grouped_routes = {
            "@source (-100)": [
                {"max_target": "https://max.ru/one", "max_target_id": -1},
                {"max_target": "https://max.ru/two", "max_target_id": -2},
            ]
        }
        with patch.object(
            admin_handlers.db,
            "get_grouped_routes",
            return_value=grouped_routes,
        ):
            await admin_handlers.handle_links.__wrapped__(grouped_message)

        reply_text = grouped_message.reply.await_args.args[0]
        self.assertIn("@source (-100):", reply_text)
        self.assertIn("→ https://max.ru/one", reply_text)
        self.assertIn("Total: 2 route(s)", reply_text)

    async def test_handle_add_validates_usage(self) -> None:
        message = make_message(text="/add only-one-arg")

        await admin_handlers.handle_add.__wrapped__(message)

        message.reply.assert_awaited_once()
        self.assertIn("Usage: /add", message.reply.await_args.args[0])

    async def test_handle_add_reports_identity_failure(self) -> None:
        message = make_message(text="/add @source https://max.ru/target")

        with patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(side_effect=RuntimeError("no bot")),
        ):
            await admin_handlers.handle_add.__wrapped__(message)

        self.assertIn(
            "Failed to verify Telegram bot identity: no bot",
            message.reply.await_args.args[0],
        )

    async def test_handle_add_reports_resolution_failures_and_duplicates(self) -> None:
        tg_failure = make_message(text="/add @source https://max.ru/target")
        with patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(return_value=SimpleNamespace(id=77)),
        ), patch(
            "handlers.admin_handlers.resolve_tg_forward_source",
            AsyncMock(side_effect=ResolveError("bad tg")),
        ):
            await admin_handlers.handle_add.__wrapped__(tg_failure)
        self.assertEqual(
            tg_failure.reply.await_args.args[0],
            "Failed to resolve Telegram source: bad tg",
        )

        max_failure = make_message(text="/add @source https://max.ru/target")
        with patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(return_value=SimpleNamespace(id=77)),
        ), patch(
            "handlers.admin_handlers.resolve_tg_forward_source",
            AsyncMock(return_value=("@source", -100)),
        ), patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(side_effect=ResolveError("bad max")),
        ):
            await admin_handlers.handle_add.__wrapped__(max_failure)
        self.assertEqual(
            max_failure.reply.await_args.args[0],
            "Failed to resolve Max target: bad max",
        )

        duplicate_message = make_message(text="/add @source https://max.ru/target")
        with patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(return_value=SimpleNamespace(id=77)),
        ), patch(
            "handlers.admin_handlers.resolve_tg_forward_source",
            AsyncMock(return_value=("@source", -100)),
        ), patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(return_value=("https://max.ru/target", -200)),
        ), patch.object(
            admin_handlers.db,
            "route_exists",
            return_value=True,
        ):
            await admin_handlers.handle_add.__wrapped__(duplicate_message)

        self.assertIn(
            "Route already exists: @source (-100) → https://max.ru/target (-200)",
            duplicate_message.reply.await_args.args[0],
        )

    async def test_handle_add_adds_route(self) -> None:
        message = make_message(text="/add @source https://max.ru/target")

        with patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(return_value=SimpleNamespace(id=77)),
        ), patch(
            "handlers.admin_handlers.resolve_tg_forward_source",
            AsyncMock(return_value=("@source", -100)),
        ) as resolve_tg, patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(return_value=("https://max.ru/target", -200)),
        ) as resolve_max, patch.object(
            admin_handlers.db,
            "route_exists",
            return_value=False,
        ), patch.object(
            admin_handlers.db,
            "add_route",
        ) as add_route:
            await admin_handlers.handle_add.__wrapped__(message)

        resolve_tg.assert_awaited_once_with(
            admin_handlers.tg_bot,
            "@source",
            bot_user_id=77,
        )
        resolve_max.assert_awaited_once_with(
            admin_handlers.max_bot,
            "https://max.ru/target",
        )
        add_route.assert_called_once_with("@source", "https://max.ru/target", -100, -200)
        self.assertEqual(
            message.reply.await_args.args[0],
            "Added: @source (-100) → https://max.ru/target (-200)",
        )

    async def test_handle_remove_validates_and_reports_outcomes(self) -> None:
        usage_message = make_message(text="/remove only-one-arg")
        await admin_handlers.handle_remove.__wrapped__(usage_message)
        self.assertIn("Usage: /remove", usage_message.reply.await_args.args[0])

        tg_failure = make_message(text="/remove @source https://max.ru/target")
        with patch(
            "handlers.admin_handlers.resolve_tg_chat",
            AsyncMock(side_effect=ResolveError("bad tg")),
        ):
            await admin_handlers.handle_remove.__wrapped__(tg_failure)
        self.assertEqual(
            tg_failure.reply.await_args.args[0],
            "Failed to resolve Telegram source: bad tg",
        )

        max_failure = make_message(text="/remove @source https://max.ru/target")
        with patch(
            "handlers.admin_handlers.resolve_tg_chat",
            AsyncMock(return_value=("@source", -100)),
        ), patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(side_effect=ResolveError("bad max")),
        ):
            await admin_handlers.handle_remove.__wrapped__(max_failure)
        self.assertEqual(
            max_failure.reply.await_args.args[0],
            "Failed to resolve Max target: bad max",
        )

        missing_message = make_message(text="/remove @source https://max.ru/target")
        with patch(
            "handlers.admin_handlers.resolve_tg_chat",
            AsyncMock(return_value=("@source", -100)),
        ), patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(return_value=("https://max.ru/target", -200)),
        ), patch.object(
            admin_handlers.db,
            "remove_route",
            return_value=[],
        ):
            await admin_handlers.handle_remove.__wrapped__(missing_message)
        self.assertEqual(
            missing_message.reply.await_args.args[0],
            "Route not found: @source (-100) → https://max.ru/target (-200)",
        )

        removed_message = make_message(text="/remove @source https://max.ru/target")
        with patch(
            "handlers.admin_handlers.resolve_tg_chat",
            AsyncMock(return_value=("@source", -100)),
        ), patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(return_value=("https://max.ru/target", -200)),
        ), patch.object(
            admin_handlers.db,
            "remove_route",
            return_value=[1],
        ):
            await admin_handlers.handle_remove.__wrapped__(removed_message)
        self.assertEqual(
            removed_message.reply.await_args.args[0],
            "Removed: @source (-100) → https://max.ru/target (-200)",
        )

    async def test_handle_import_validates_attachment_and_csv(self) -> None:
        no_document_message = make_message()
        await admin_handlers.handle_import.__wrapped__(no_document_message)
        self.assertIn("/import as caption", no_document_message.reply.await_args.args[0])

        missing_path_message = make_message(document=SimpleNamespace(file_id="file"))
        with patch.object(
            admin_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path=None)),
        ):
            await admin_handlers.handle_import.__wrapped__(missing_path_message)
        self.assertEqual(
            missing_path_message.reply.await_args.args[0],
            "Failed to download file.",
        )

        invalid_header_message = make_message(document=SimpleNamespace(file_id="file"))
        with patch.object(
            admin_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path="routes.csv")),
        ), patch.object(
            admin_handlers.tg_bot,
            "download_file",
            AsyncMock(return_value=io.BytesIO(b"wrong,headers\nvalue,other\n")),
        ):
            await admin_handlers.handle_import.__wrapped__(invalid_header_message)
        self.assertEqual(
            invalid_header_message.reply.await_args.args[0],
            "Invalid CSV format. Required headers: tg_source, max_target",
        )

        empty_csv_message = make_message(document=SimpleNamespace(file_id="file"))
        with patch.object(
            admin_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path="routes.csv")),
        ), patch.object(
            admin_handlers.tg_bot,
            "download_file",
            AsyncMock(return_value=io.BytesIO(b"tg_source,max_target\n")),
        ):
            await admin_handlers.handle_import.__wrapped__(empty_csv_message)
        self.assertEqual(empty_csv_message.reply.await_args.args[0], "CSV file is empty.")

    async def test_handle_import_reports_identity_failure(self) -> None:
        message = make_message(document=SimpleNamespace(file_id="file"))

        with patch.object(
            admin_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path="routes.csv")),
        ), patch.object(
            admin_handlers.tg_bot,
            "download_file",
            AsyncMock(return_value=io.BytesIO(b"tg_source,max_target\n@a,https://max.ru/a\n")),
        ), patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(side_effect=RuntimeError("no bot")),
        ):
            await admin_handlers.handle_import.__wrapped__(message)

        self.assertEqual(
            message.reply.await_args.args[0],
            "Failed to verify Telegram bot identity: no bot",
        )

    async def test_handle_import_processes_rows_and_reports_summary(self) -> None:
        csv_content = (
            "tg_source,max_target\n"
            "@ok,https://max.ru/ok\n"
            "@dup,https://max.ru/dup\n"
            "@badtg,https://max.ru/skip\n"
            "@ok2,badmax\n"
            ",https://max.ru/missing\n"
        )
        message = make_message(document=SimpleNamespace(file_id="file"))

        async def resolve_tg_side_effect(bot, value, *, bot_user_id=None):
            del bot, bot_user_id
            if value == "@badtg":
                raise ResolveError("bad tg")
            mapping = {
                "@ok": ("@ok", -1),
                "@dup": ("@dup", -2),
                "@ok2": ("@ok2", -3),
            }
            return mapping[value]

        async def resolve_max_side_effect(bot, value):
            del bot
            if value == "badmax":
                raise ResolveError("bad max")
            mapping = {
                "https://max.ru/ok": ("https://max.ru/ok", -10),
                "https://max.ru/dup": ("https://max.ru/dup", -20),
                "https://max.ru/skip": ("https://max.ru/skip", -30),
            }
            return mapping[value]

        with patch.object(
            admin_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path="routes.csv")),
        ), patch.object(
            admin_handlers.tg_bot,
            "download_file",
            AsyncMock(return_value=io.BytesIO(csv_content.encode("utf-8"))),
        ), patch.object(
            admin_handlers.tg_bot,
            "get_me",
            AsyncMock(return_value=SimpleNamespace(id=77)),
        ), patch(
            "handlers.admin_handlers.resolve_tg_forward_source",
            AsyncMock(side_effect=resolve_tg_side_effect),
        ), patch(
            "handlers.admin_handlers.resolve_max_chat",
            AsyncMock(side_effect=resolve_max_side_effect),
        ), patch.object(
            admin_handlers.db,
            "route_exists",
            side_effect=lambda tg_id, max_id: (tg_id, max_id) == (-2, -20),
        ), patch.object(
            admin_handlers.db,
            "add_route",
        ) as add_route:
            await admin_handlers.handle_import.__wrapped__(message)

        add_route.assert_called_once_with("@ok", "https://max.ru/ok", -1, -10)
        reply_text = message.reply.await_args.args[0]
        self.assertIn("Imported 1 route(s)", reply_text)
        self.assertIn("1 duplicate(s) skipped", reply_text)
        self.assertIn("3 error(s)", reply_text)
        self.assertIn("Line 4: bad tg", reply_text)
        self.assertIn("Line 5: bad max", reply_text)
        self.assertIn("Line 6: empty value", reply_text)

    async def test_handle_export_and_admin_lists(self) -> None:
        empty_message = make_message()
        with patch.object(admin_handlers.db, "get_all_routes", return_value=[]):
            await admin_handlers.handle_export.__wrapped__(empty_message)
        self.assertEqual(empty_message.reply.await_args.args[0], "No routes to export.")

        export_message = make_message()
        with patch.object(
            admin_handlers.db,
            "get_all_routes",
            return_value=[
                {"tg_source": "@a", "max_target": "https://max.ru/a"},
                {"tg_source": "@b", "max_target": "https://max.ru/b"},
            ],
        ):
            await admin_handlers.handle_export.__wrapped__(export_message)
        document = export_message.reply_document.await_args.args[0]
        self.assertEqual(document.filename, "routes.csv")
        self.assertEqual(
            export_message.reply_document.await_args.kwargs["caption"],
            "Exported 2 route(s)",
        )

        admins_message = make_message()
        with patch.object(admin_handlers.config, "ADMIN_IDS", {10, 20}), patch.object(
            admin_handlers.db,
            "get_all_admins",
            return_value=[30],
        ):
            await admin_handlers.handle_admins.__wrapped__(admins_message)
        admins_text = admins_message.reply.await_args.args[0]
        self.assertIn("Admins from env:", admins_text)
        self.assertIn("10", admins_text)
        self.assertIn("Admins from DB:", admins_text)
        self.assertIn("Total: 3 admin(s)", admins_text)

    async def test_handle_addadmin_validates_and_adds(self) -> None:
        usage_message = make_message(text="/addadmin")
        await admin_handlers.handle_addadmin.__wrapped__(usage_message)
        self.assertIn("Usage: /addadmin", usage_message.reply.await_args.args[0])

        invalid_message = make_message(text="/addadmin not-a-number")
        await admin_handlers.handle_addadmin.__wrapped__(invalid_message)
        self.assertEqual(
            invalid_message.reply.await_args.args[0],
            "Invalid user ID. Must be an integer.",
        )

        env_message = make_message(text="/addadmin 10")
        with patch.object(admin_handlers.config, "ADMIN_IDS", {10}), patch.object(
            admin_handlers.db,
            "admin_exists",
            return_value=False,
        ):
            await admin_handlers.handle_addadmin.__wrapped__(env_message)
        self.assertEqual(env_message.reply.await_args.args[0], "User 10 is already an env admin.")

        db_message = make_message(text="/addadmin 20")
        with patch.object(admin_handlers.config, "ADMIN_IDS", set()), patch.object(
            admin_handlers.db,
            "admin_exists",
            return_value=True,
        ):
            await admin_handlers.handle_addadmin.__wrapped__(db_message)
        self.assertEqual(db_message.reply.await_args.args[0], "User 20 is already a DB admin.")

        success_message = make_message(text="/addadmin 30")
        with patch.object(admin_handlers.config, "ADMIN_IDS", set()), patch.object(
            admin_handlers.db,
            "admin_exists",
            return_value=False,
        ), patch.object(admin_handlers.db, "add_admin") as add_admin:
            await admin_handlers.handle_addadmin.__wrapped__(success_message)
        add_admin.assert_called_once_with(30)
        self.assertEqual(success_message.reply.await_args.args[0], "Added admin: 30")

    async def test_handle_removeadmin_validates_and_removes(self) -> None:
        usage_message = make_message(text="/removeadmin")
        await admin_handlers.handle_removeadmin.__wrapped__(usage_message)
        self.assertIn("Usage: /removeadmin", usage_message.reply.await_args.args[0])

        invalid_message = make_message(text="/removeadmin not-a-number")
        await admin_handlers.handle_removeadmin.__wrapped__(invalid_message)
        self.assertEqual(
            invalid_message.reply.await_args.args[0],
            "Invalid user ID. Must be an integer.",
        )

        env_message = make_message(text="/removeadmin 10")
        with patch.object(admin_handlers.config, "ADMIN_IDS", {10}):
            await admin_handlers.handle_removeadmin.__wrapped__(env_message)
        self.assertEqual(env_message.reply.await_args.args[0], "Cannot remove env admin: 10")

        missing_message = make_message(text="/removeadmin 20")
        with patch.object(admin_handlers.config, "ADMIN_IDS", set()), patch.object(
            admin_handlers.db,
            "remove_admin",
            return_value=[],
        ):
            await admin_handlers.handle_removeadmin.__wrapped__(missing_message)
        self.assertEqual(missing_message.reply.await_args.args[0], "Admin not found: 20")

        success_message = make_message(text="/removeadmin 30")
        with patch.object(admin_handlers.config, "ADMIN_IDS", set()), patch.object(
            admin_handlers.db,
            "remove_admin",
            return_value=[1],
        ) as remove_admin:
            await admin_handlers.handle_removeadmin.__wrapped__(success_message)
        remove_admin.assert_called_once_with(30)
        self.assertEqual(success_message.reply.await_args.args[0], "Removed admin: 30")


if __name__ == "__main__":
    unittest.main()
