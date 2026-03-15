"""
ID/Nick resolution utilities for Telegram and Max chats.
"""

import re

from aiogram import Bot as TgBot
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
