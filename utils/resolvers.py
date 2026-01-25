"""
ID/Nick resolution utilities for Telegram and Max chats.
"""

import re

from aiogram import Bot as TgBot
from maxapi import Bot as MaxBot


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

    # Normalize URL: prepend https:// if missing
    url = input_str
    if not url.startswith("https://"):
        if url.startswith("http://"):
            url = "https://" + url[7:]
        elif url.startswith("max.ru/"):
            url = "https://" + url
        # else assume it's already a full https URL or will fail

    # Store display as full https URL
    display = url

    try:
        chat = await bot.get_chat_by_link(url)
        return (display, chat.chat_id)
    except Exception as e:
        raise ResolveError(f"Failed to resolve Max chat '{input_str}': {e}")
