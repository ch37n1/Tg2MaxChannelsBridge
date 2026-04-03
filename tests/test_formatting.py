from __future__ import annotations

import unittest
from types import SimpleNamespace

from aiogram.enums import MessageEntityType
from aiogram.types import MessageEntity
from maxapi.enums.parse_mode import ParseMode

from utils.formatting import format_message_for_max, format_text_for_max


def utf16_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def make_entity(
    entity_type: MessageEntityType,
    text: str,
    fragment: str,
    *,
    start: int | None = None,
    **kwargs: object,
) -> MessageEntity:
    if start is None:
        start = text.index(fragment)

    prefix = text[:start]
    return MessageEntity(
        type=entity_type,
        offset=utf16_len(prefix),
        length=utf16_len(fragment),
        **kwargs,
    )


class FormatTextForMaxTests(unittest.TestCase):
    def test_plain_text_keeps_original_and_parse_mode(self) -> None:
        formatted = format_text_for_max("plain * text")

        self.assertEqual(formatted.text, "plain * text")
        self.assertIsNone(formatted.parse_mode)

    def test_supported_entities_render_to_max_markdown(self) -> None:
        text = "bold italic underline strike code link"
        entities = [
            make_entity(MessageEntityType.BOLD, text, "bold"),
            make_entity(MessageEntityType.ITALIC, text, "italic"),
            make_entity(MessageEntityType.UNDERLINE, text, "underline"),
            make_entity(MessageEntityType.STRIKETHROUGH, text, "strike"),
            make_entity(MessageEntityType.CODE, text, "code"),
            make_entity(
                MessageEntityType.TEXT_LINK,
                text,
                "link",
                url="https://example.com",
            ),
        ]

        formatted = format_text_for_max(text, entities)

        self.assertEqual(
            formatted.text,
            "**bold** _italic_ ++underline++ ~~strike~~ `code` [link](https://example.com)",
        )
        self.assertEqual(formatted.parse_mode, ParseMode.MARKDOWN)

    def test_utf16_offsets_are_handled_for_emoji(self) -> None:
        text = "🙂 bold"
        entities = [make_entity(MessageEntityType.BOLD, text, "bold")]

        formatted = format_text_for_max(text, entities)

        self.assertEqual(formatted.text, "🙂 **bold**")
        self.assertEqual(formatted.parse_mode, ParseMode.MARKDOWN)

    def test_pre_entities_fall_back_to_html(self) -> None:
        text = "line 1\n<tag>"
        entities = [
            make_entity(
                MessageEntityType.PRE,
                text,
                text,
                language="python",
            )
        ]

        formatted = format_text_for_max(text, entities)

        self.assertEqual(formatted.text, "<pre>line 1\n&lt;tag&gt;</pre>")
        self.assertEqual(formatted.parse_mode, ParseMode.HTML)

    def test_code_with_backticks_falls_back_to_html(self) -> None:
        text = "a`b"
        entities = [make_entity(MessageEntityType.CODE, text, text)]

        formatted = format_text_for_max(text, entities)

        self.assertEqual(formatted.text, "<code>a`b</code>")
        self.assertEqual(formatted.parse_mode, ParseMode.HTML)

    def test_caption_entities_are_used_when_message_has_no_text(self) -> None:
        message = SimpleNamespace(
            text=None,
            entities=None,
            caption="Go to docs",
            caption_entities=[
                make_entity(
                    MessageEntityType.TEXT_LINK,
                    "Go to docs",
                    "docs",
                    url="https://example.com",
                )
            ],
        )

        formatted = format_message_for_max(message)

        self.assertEqual(formatted.text, "Go to [docs](https://example.com)")
        self.assertEqual(formatted.parse_mode, ParseMode.MARKDOWN)


if __name__ == "__main__":
    unittest.main()
