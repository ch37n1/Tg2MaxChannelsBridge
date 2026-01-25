"""
Admin authentication utilities.
"""

from functools import wraps
from typing import Callable, Awaitable

from aiogram.types import Message as TgMessage

import config
import db


def is_admin(user_id: int) -> bool:
    """
    Check if user ID is an admin.

    Checks env admins first (always have access), then checks DB.
    """
    # Check env admins first (always have access)
    if user_id in config.ADMIN_IDS:
        return True
    # Then check DB
    return db.admin_exists(user_id)


def admin_only(handler: Callable[[TgMessage], Awaitable[None]]):
    """
    Decorator to restrict handler to admin users only.

    Usage:
        @admin_only
        async def handle_add(message: TgMessage):
            ...
    """

    @wraps(handler)
    async def wrapper(message: TgMessage, *args, **kwargs):
        if not message.from_user:
            return

        if not is_admin(message.from_user.id):
            await message.reply("Access denied. You are not an admin.")
            return

        return await handler(message, *args, **kwargs)

    return wrapper
