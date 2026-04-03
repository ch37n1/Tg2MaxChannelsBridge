from __future__ import annotations

import html
import re
from dataclasses import dataclass

from aiogram.enums import MessageEntityType
from aiogram.types import Message as TgMessage, MessageEntity
from aiogram.utils.text_decorations import HtmlDecoration, TextDecoration
from maxapi.enums.parse_mode import ParseMode


@dataclass(frozen=True)
class FormattedText:
    text: str
    parse_mode: ParseMode | None = None


class MaxMarkdownDecoration(TextDecoration):
    _ESCAPE_RE = re.compile(r"([\\*_`\[\]()~+])")

    def apply_entity(self, entity: MessageEntity, text: str) -> str:
        if entity.type == MessageEntityType.TEXT_MENTION:
            return text
        return super().apply_entity(entity, text)

    def link(self, value: str, link: str) -> str:
        escaped_link = link.replace("\\", "\\\\").replace(")", r"\)")
        return f"[{value}]({escaped_link})"

    def bold(self, value: str) -> str:
        return f"**{value}**"

    def italic(self, value: str) -> str:
        return f"_{value}_"

    def code(self, value: str) -> str:
        safe_value = value.replace("\\", "\\\\").replace("`", r"\`").replace("\n", " ")
        return f"`{safe_value}`"

    def pre(self, value: str) -> str:
        return value

    def pre_language(self, value: str, language: str) -> str:
        del language
        return value

    def underline(self, value: str) -> str:
        return f"++{value}++"

    def strikethrough(self, value: str) -> str:
        return f"~~{value}~~"

    def spoiler(self, value: str) -> str:
        return value

    def quote(self, value: str) -> str:
        return self._ESCAPE_RE.sub(r"\\\1", value)

    def custom_emoji(self, value: str, custom_emoji_id: str) -> str:
        del custom_emoji_id
        return value

    def blockquote(self, value: str) -> str:
        return value

    def expandable_blockquote(self, value: str) -> str:
        return value


class MaxHtmlDecoration(HtmlDecoration):
    BOLD_TAG = "strong"
    ITALIC_TAG = "em"
    UNDERLINE_TAG = "u"
    STRIKETHROUGH_TAG = "s"

    def apply_entity(self, entity: MessageEntity, text: str) -> str:
        if entity.type == MessageEntityType.TEXT_MENTION:
            return text
        return super().apply_entity(entity, text)

    def link(self, value: str, link: str) -> str:
        return f'<a href="{html.escape(link, quote=True)}">{value}</a>'

    def pre_language(self, value: str, language: str) -> str:
        del language
        return self.pre(value)

    def spoiler(self, value: str) -> str:
        return value

    def custom_emoji(self, value: str, custom_emoji_id: str) -> str:
        del custom_emoji_id
        return value

    def blockquote(self, value: str) -> str:
        return value

    def expandable_blockquote(self, value: str) -> str:
        return value


MAX_MARKDOWN_DECORATION = MaxMarkdownDecoration()
MAX_HTML_DECORATION = MaxHtmlDecoration()


def format_message_for_max(message: TgMessage) -> FormattedText:
    text = message.text or message.caption or ""
    entities = message.entities or message.caption_entities or []
    return format_text_for_max(text, entities)


def format_text_for_max(
    text: str | None,
    entities: list[MessageEntity] | None = None,
) -> FormattedText:
    if not text:
        return FormattedText("")

    resolved_entities = list(entities or [])
    if not resolved_entities:
        return FormattedText(text=text)

    if any(_requires_html(entity, text) for entity in resolved_entities):
        return FormattedText(
            text=MAX_HTML_DECORATION.unparse(text, resolved_entities),
            parse_mode=ParseMode.HTML,
        )

    return FormattedText(
        text=MAX_MARKDOWN_DECORATION.unparse(text, resolved_entities),
        parse_mode=ParseMode.MARKDOWN,
    )


def _requires_html(entity: MessageEntity, text: str) -> bool:
    if entity.type == MessageEntityType.PRE:
        return True

    if entity.type == MessageEntityType.CODE:
        entity_text = entity.extract_from(text)
        return "\n" in entity_text or "`" in entity_text

    return False
