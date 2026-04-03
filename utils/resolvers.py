"""
ID/Nick resolution utilities for Telegram and Max chats.
"""

import re

from aiogram import Bot as TgBot
from aiogram.enums import ChatMemberStatus, ChatType
from utils.max_bot import MaxBot


class ResolveError(Exception):
    """Raised when chat resolution fails."""

    pass


async def resolve_tg_chat(bot: TgBot, input_str: str) -> tuple[str, int]:
    """
    Resolve Telegram chat input to (display_string, resolved_id).

    Args:
        bot: Telegram bot instance
        input_str: Either @username or numeric ID

    Returns:
        Tuple of (display_string, resolved_id)

    Raises:
        ResolveError: If resolution fails
    """
    input_str = input_str.strip()

    # If it's a numeric ID, just parse it
    if re.match(r"^-?\d+$", input_str):
        chat_id = int(input_str)
        return (input_str, chat_id)

    # Otherwise, resolve via API (assumes @username format)
    try:
        chat = await bot.get_chat(input_str)
        return (input_str, chat.id)
    except Exception as e:
        raise ResolveError(f"Failed to resolve Telegram chat '{input_str}': {e}")


async def validate_tg_channel_access(
    bot: TgBot,
    chat_id: int,
    *,
    chat: object | None = None,
    bot_user_id: int | None = None,
) -> None:
    """
    Validate that the bot can receive posts from a Telegram channel.

    Args:
        bot: Telegram bot instance
        chat_id: Telegram chat ID
        chat: Optional pre-fetched chat object
        bot_user_id: Optional bot user ID to avoid repeated get_me() calls

    Raises:
        ResolveError: If the chat is not a channel or the bot lacks access
    """
    if chat is None:
        try:
            chat = await bot.get_chat(chat_id)
        except Exception as e:
            raise ResolveError(f"Bot has no access to Telegram chat '{chat_id}': {e}")

    if getattr(chat, "type", None) != ChatType.CHANNEL:
        raise ResolveError(f"Telegram chat '{chat_id}' is not a channel")

    if bot_user_id is None:
        try:
            bot_user_id = (await bot.get_me()).id
        except Exception as e:
            raise ResolveError(f"Failed to verify Telegram bot identity: {e}")

    try:
        member = await bot.get_chat_member(chat_id, bot_user_id)
    except Exception as e:
        raise ResolveError(f"Failed to verify bot access to Telegram channel '{chat_id}': {e}")

    allowed_statuses = {
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
    }
    if getattr(member, "status", None) not in allowed_statuses:
        raise ResolveError(
            f"Bot is not an administrator in Telegram channel '{chat_id}' "
            f"(status: {getattr(member, 'status', 'unknown')})"
        )


async def resolve_tg_forward_source(
    bot: TgBot,
    input_str: str,
    *,
    bot_user_id: int | None = None,
) -> tuple[str, int]:
    """
    Resolve a Telegram forwarding source and verify bot access to it.

    Unlike resolve_tg_chat(), this helper validates that the source is a
    channel and that the bot is an administrator there.
    """
    input_str = input_str.strip()

    if re.match(r"^-?\d+$", input_str):
        chat_id = int(input_str)
        display = input_str
        try:
            chat = await bot.get_chat(chat_id)
        except Exception as e:
            raise ResolveError(f"Bot has no access to Telegram chat '{input_str}': {e}")
    else:
        display = input_str
        try:
            chat = await bot.get_chat(input_str)
            chat_id = chat.id
        except Exception as e:
            raise ResolveError(f"Failed to resolve Telegram chat '{input_str}': {e}")

    await validate_tg_channel_access(
        bot,
        chat_id,
        chat=chat,
        bot_user_id=bot_user_id,
    )
    return (display, chat_id)


async def resolve_max_chat(bot: MaxBot, input_str: str) -> tuple[str, int]:
    """
    Resolve Max chat input to (display_string, resolved_id).

    Args:
        bot: Max bot instance
        input_str: Either URL (https://max.ru/nick or max.ru/nick) or numeric ID

    Returns:
        Tuple of (display_string, resolved_id)

    Raises:
        ResolveError: If resolution fails
    """
    input_str = input_str.strip()

    # If it's a numeric ID, just parse it
    if re.match(r"^-?\d+$", input_str):
        chat_id = int(input_str)
        return (input_str, chat_id)

    url = bot.normalize_chat_link(input_str)

    # Store display as full https URL
    display = url

    try:
        chat = await bot.get_chat(url)
        return (display, chat.chat_id)
    except Exception as e:
        raise ResolveError(f"Failed to resolve Max chat '{input_str}': {e}")
