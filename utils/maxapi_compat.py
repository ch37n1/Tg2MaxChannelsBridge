from __future__ import annotations

import warnings

from pydantic.warnings import PydanticDeprecatedSince20


with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"Support for class-based `config` is deprecated, use ConfigDict instead\.",
        category=PydanticDeprecatedSince20,
    )

    from maxapi import Bot as BaseMaxBot
    from maxapi import Dispatcher as MaxDispatcher
    from maxapi.enums.parse_mode import ParseMode
    from maxapi.types import BotStarted, InputMedia
    from maxapi.types.chats import Chat, Chats


__all__ = [
    "BaseMaxBot",
    "BotStarted",
    "Chat",
    "Chats",
    "InputMedia",
    "MaxDispatcher",
    "ParseMode",
]
