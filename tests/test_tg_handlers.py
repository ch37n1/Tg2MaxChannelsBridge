from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, call, patch

import handlers.tg_handlers as tg_handlers
from utils.formatting import FormattedText
from utils.maxapi_compat import ParseMode


def make_message(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "sticker": None,
        "voice": None,
        "contact": None,
        "dice": None,
        "game": None,
        "poll": None,
        "location": None,
        "photo": None,
        "audio": None,
        "document": None,
        "video": None,
        "text": None,
        "caption": None,
        "entities": None,
        "caption_entities": None,
        "media_group_id": None,
        "message_id": 1,
        "chat": SimpleNamespace(id=-100123),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TgHandlersTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        tg_handlers.media_groups.clear()

    async def test_download_tg_media_downloads_to_temp_file(self) -> None:
        async def fake_download_file(file_path: str, destination: str) -> None:
            del file_path
            with open(destination, "wb") as file_obj:
                file_obj.write(b"payload")

        with patch.object(
            tg_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path="photos/image.jpg")),
        ), patch.object(
            tg_handlers.tg_bot,
            "download_file",
            AsyncMock(side_effect=fake_download_file),
        ):
            temp_path = await tg_handlers.download_tg_media("file-id")

        self.assertIsNotNone(temp_path)
        assert temp_path is not None
        self.assertTrue(temp_path.endswith(".jpg"))
        self.assertTrue(os.path.exists(temp_path))
        os.remove(temp_path)

    async def test_download_tg_media_returns_none_for_missing_path_or_errors(self) -> None:
        with patch("handlers.tg_handlers.logging.error"), patch.object(
            tg_handlers.tg_bot,
            "get_file",
            AsyncMock(return_value=SimpleNamespace(file_path=None)),
        ):
            self.assertIsNone(await tg_handlers.download_tg_media("file-id"))

        with patch("handlers.tg_handlers.logging.error"), patch.object(
            tg_handlers.tg_bot,
            "get_file",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            self.assertIsNone(await tg_handlers.download_tg_media("file-id"))

    async def test_send_to_max_cleans_up_on_success_and_failure(self) -> None:
        success_fd, success_path = tempfile.mkstemp()
        os.close(success_fd)
        failure_fd, failure_path = tempfile.mkstemp()
        os.close(failure_fd)

        with patch.object(
            tg_handlers.max_bot,
            "send_message",
            AsyncMock(),
        ) as send_message:
            result = await tg_handlers.send_to_max(
                10,
                "hello",
                [success_path],
                parse_mode=ParseMode.MARKDOWN,
            )

        self.assertTrue(result)
        self.assertFalse(os.path.exists(success_path))
        send_message.assert_awaited_once()
        self.assertEqual(send_message.await_args.kwargs["chat_id"], 10)
        self.assertEqual(send_message.await_args.kwargs["text"], "hello")
        self.assertEqual(send_message.await_args.kwargs["parse_mode"], ParseMode.MARKDOWN)
        attachments = send_message.await_args.kwargs["attachments"]
        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].path, success_path)

        with patch("handlers.tg_handlers.logging.error"), patch.object(
            tg_handlers.max_bot,
            "send_message",
            AsyncMock(side_effect=RuntimeError("boom")),
        ):
            result = await tg_handlers.send_to_max(10, None, [failure_path])

        self.assertFalse(result)
        self.assertFalse(os.path.exists(failure_path))

    def test_cleanup_temp_files_ignores_missing_files_and_logs_remove_errors(self) -> None:
        fd, path = tempfile.mkstemp()
        os.close(fd)

        with patch("handlers.tg_handlers.os.remove", side_effect=OSError("nope")), patch(
            "handlers.tg_handlers.logging.error"
        ) as log_error:
            tg_handlers.cleanup_temp_files([path, "/tmp/definitely-missing-file"])

        log_error.assert_called_once()
        self.assertTrue(os.path.exists(path))
        os.remove(path)

    async def test_forward_media_group_sends_caption_and_downloaded_media(self) -> None:
        first = make_message(
            media_group_id="group-1",
            message_id=2,
            photo=[SimpleNamespace(file_id="photo-file")],
        )
        second = make_message(
            media_group_id="group-1",
            message_id=1,
            video=SimpleNamespace(file_id="video-file"),
        )
        tg_handlers.media_groups["group-1"] = [first, second]

        with patch("handlers.tg_handlers.asyncio.sleep", AsyncMock()), patch(
            "handlers.tg_handlers.format_message_for_max",
            side_effect=[
                FormattedText("", None),
                FormattedText("caption", ParseMode.MARKDOWN),
            ],
        ), patch(
            "handlers.tg_handlers.download_tg_media",
            AsyncMock(side_effect=["/tmp/video.mp4", "/tmp/photo.jpg"]),
        ) as download_media, patch(
            "handlers.tg_handlers.send_to_max",
            AsyncMock(return_value=True),
        ) as send_to_max:
            await tg_handlers.forward_media_group("group-1", 999)

        self.assertNotIn("group-1", tg_handlers.media_groups)
        self.assertEqual(download_media.await_args_list, [
            call("video-file", default_suffix=".mp4"),
            call("photo-file", default_suffix=".jpg"),
        ])
        send_to_max.assert_awaited_once_with(
            999,
            "caption",
            ["/tmp/video.mp4", "/tmp/photo.jpg"],
            parse_mode=ParseMode.MARKDOWN,
        )

    async def test_forward_media_group_returns_when_no_media_downloaded(self) -> None:
        message = make_message(
            media_group_id="group-2",
            message_id=1,
            photo=[SimpleNamespace(file_id="photo-file")],
        )
        tg_handlers.media_groups["group-2"] = [message]

        with patch("handlers.tg_handlers.logging.warning"), patch(
            "handlers.tg_handlers.asyncio.sleep",
            AsyncMock(),
        ), patch(
            "handlers.tg_handlers.format_message_for_max",
            return_value=FormattedText("", None),
        ), patch(
            "handlers.tg_handlers.download_tg_media",
            AsyncMock(return_value=None),
        ), patch(
            "handlers.tg_handlers.send_to_max",
            AsyncMock(),
        ) as send_to_max:
            await tg_handlers.forward_media_group("group-2", 999)

        self.assertNotIn("group-2", tg_handlers.media_groups)
        send_to_max.assert_not_awaited()

    async def test_handle_media_group_starts_background_task_once(self) -> None:
        created_coroutines = []

        def fake_create_task(coro):
            created_coroutines.append(coro)
            coro.close()
            return SimpleNamespace()

        first = make_message(media_group_id="group-3")
        second = make_message(media_group_id="group-3", message_id=2)

        with patch("handlers.tg_handlers.asyncio.create_task", side_effect=fake_create_task) as create_task:
            await tg_handlers.handle_media_group(first, 10)
            await tg_handlers.handle_media_group(second, 10)

        create_task.assert_called_once()
        self.assertEqual(tg_handlers.media_groups["group-3"], [first, second])
        self.assertEqual(len(created_coroutines), 1)

    async def test_handle_single_skips_unsupported_messages(self) -> None:
        for attr in [
            "sticker",
            "voice",
            "contact",
            "dice",
            "game",
            "poll",
            "location",
        ]:
            with self.subTest(attr=attr), patch(
                "handlers.tg_handlers.send_to_max",
                AsyncMock(),
            ) as send_to_max, patch(
                "handlers.tg_handlers.format_message_for_max",
            ) as format_message:
                await tg_handlers.handle_single(
                    make_message(**{attr: object()}),
                    55,
                )

            send_to_max.assert_not_awaited()
            format_message.assert_not_called()

    async def test_handle_single_forwards_media_and_text(self) -> None:
        scenarios = [
            ("photo", [SimpleNamespace(file_id="photo-file")], ".jpg"),
            ("audio", SimpleNamespace(file_id="audio-file"), ".mp3"),
            ("document", SimpleNamespace(file_id="document-file"), ".bin"),
            ("video", SimpleNamespace(file_id="video-file"), ".mp4"),
        ]

        for attr, payload, suffix in scenarios:
            message = make_message(**{attr: payload})
            with self.subTest(attr=attr), patch(
                "handlers.tg_handlers.format_message_for_max",
                return_value=FormattedText("caption", ParseMode.MARKDOWN),
            ), patch(
                "handlers.tg_handlers.download_tg_media",
                AsyncMock(return_value="/tmp/uploaded"),
            ) as download_media, patch(
                "handlers.tg_handlers.send_to_max",
                AsyncMock(),
            ) as send_to_max:
                await tg_handlers.handle_single(message, 77)

            expected_file_id = payload[-1].file_id if attr == "photo" else payload.file_id
            download_media.assert_awaited_once_with(expected_file_id, default_suffix=suffix)
            send_to_max.assert_awaited_once_with(
                77,
                "caption",
                ["/tmp/uploaded"],
                parse_mode=ParseMode.MARKDOWN,
            )

        text_message = make_message(text="plain")
        with patch(
            "handlers.tg_handlers.format_message_for_max",
            return_value=FormattedText("plain", ParseMode.MARKDOWN),
        ), patch(
            "handlers.tg_handlers.send_to_max",
            AsyncMock(),
        ) as send_to_max:
            await tg_handlers.handle_single(text_message, 88)

        send_to_max.assert_awaited_once_with(
            88,
            "plain",
            [],
            parse_mode=ParseMode.MARKDOWN,
        )

    async def test_handle_single_ignores_empty_text_message(self) -> None:
        message = make_message(text="ignored")

        with patch(
            "handlers.tg_handlers.format_message_for_max",
            return_value=FormattedText("", None),
        ), patch(
            "handlers.tg_handlers.send_to_max",
            AsyncMock(),
        ) as send_to_max:
            await tg_handlers.handle_single(message, 88)

        send_to_max.assert_not_awaited()

    async def test_on_channel_post_handles_missing_targets_media_groups_and_single_posts(self) -> None:
        message = make_message(chat=SimpleNamespace(id=-100500), message_id=7)

        with patch.object(admin_db := tg_handlers.db, "get_channel_links", return_value={}):
            await tg_handlers.on_channel_post(message)

        media_group_message = make_message(
            chat=SimpleNamespace(id=-100500),
            message_id=8,
            media_group_id="media-group",
        )
        with patch.object(admin_db, "get_channel_links", return_value={-100500: [10, 20]}), patch(
            "handlers.tg_handlers.handle_media_group",
            AsyncMock(),
        ) as handle_media_group, patch("handlers.tg_handlers.handle_single", AsyncMock()) as handle_single:
            await tg_handlers.on_channel_post(media_group_message)

        handle_media_group.assert_awaited_once_with(media_group_message, 10)
        handle_single.assert_not_awaited()

        single_message = make_message(chat=SimpleNamespace(id=-100500), message_id=9)
        with patch.object(admin_db, "get_channel_links", return_value={-100500: [10, 20]}), patch(
            "handlers.tg_handlers.handle_single",
            AsyncMock(),
        ) as handle_single, patch("handlers.tg_handlers.asyncio.sleep", AsyncMock()) as sleep_mock:
            await tg_handlers.on_channel_post(single_message)

        self.assertEqual(
            handle_single.await_args_list,
            [call(single_message, 10), call(single_message, 20)],
        )
        self.assertEqual(sleep_mock.await_args_list, [call(1), call(1)])


if __name__ == "__main__":
    unittest.main()
