"""
Admin command handlers for route management.
"""

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message as TgMessage

import db
from loader import tg_dp, tg_bot, max_bot
from utils.auth import admin_only
from utils.resolvers import resolve_tg_chat, resolve_max_chat, ResolveError


HELP_TEXT = """Bot Admin Commands:

/help - Show this help message
/links - List all configured routes
/add <tg_source> <max_target> - Add a new route
/remove <tg_source> <max_target> - Remove a route
/import - Import routes from CSV (send file with this caption)
/export - Export all routes to CSV

Examples:
  /add @my_channel https://max.ru/target
  /add -1001234567890 -69520134802093
  /remove @my_channel https://max.ru/target"""


@tg_dp.message(Command("help"))
@admin_only
async def handle_help(message: TgMessage):
    """Show help message with available commands."""
    await message.reply(HELP_TEXT)


@tg_dp.message(Command("links"))
@admin_only
async def handle_links(message: TgMessage):
    """List all configured routes grouped by source."""
    grouped = db.get_grouped_routes()

    if not grouped:
        await message.reply("No routes configured.")
        return

    lines = []
    total = 0

    for source_key, targets in grouped.items():
        lines.append(f"{source_key}:")
        for target in targets:
            lines.append(f"  → {target['max_target']}")
            total += 1
        lines.append("")  # Empty line between groups

    lines.append(f"Total: {total} route(s)")

    await message.reply("\n".join(lines))


@tg_dp.message(Command("add"))
@admin_only
async def handle_add(message: TgMessage):
    """Add a new route with ID resolution."""
    if not message.text:
        return

    # Parse arguments
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("Usage: /add <tg_source> <max_target>\n\nExample: /add @my_channel https://max.ru/target")
        return

    _, tg_input, max_input = parts

    # Resolve Telegram source
    try:
        tg_display, tg_id = await resolve_tg_chat(tg_bot, tg_input)
    except ResolveError as e:
        await message.reply(f"Failed to resolve Telegram source: {e}")
        return

    # Resolve Max target
    try:
        max_display, max_id = await resolve_max_chat(max_bot, max_input)
    except ResolveError as e:
        await message.reply(f"Failed to resolve Max target: {e}")
        return

    # Check if route already exists
    if db.route_exists(tg_id, max_id):
        await message.reply(f"Route already exists: {tg_display} ({tg_id}) → {max_display} ({max_id})")
        return

    # Add route
    db.add_route(tg_display, max_display, tg_id, max_id)

    await message.reply(f"Added: {tg_display} ({tg_id}) → {max_display} ({max_id})")


@tg_dp.message(Command("remove"))
@admin_only
async def handle_remove(message: TgMessage):
    """Remove a route."""
    if not message.text:
        return

    # Parse arguments
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.reply("Usage: /remove <tg_source> <max_target>\n\nExample: /remove @my_channel https://max.ru/target")
        return

    _, tg_input, max_input = parts

    # Resolve Telegram source
    try:
        tg_display, tg_id = await resolve_tg_chat(tg_bot, tg_input)
    except ResolveError as e:
        await message.reply(f"Failed to resolve Telegram source: {e}")
        return

    # Resolve Max target
    try:
        max_display, max_id = await resolve_max_chat(max_bot, max_input)
    except ResolveError as e:
        await message.reply(f"Failed to resolve Max target: {e}")
        return

    # Remove route
    removed = db.remove_route(tg_id, max_id)

    if removed:
        await message.reply(f"Removed: {tg_display} ({tg_id}) → {max_display} ({max_id})")
    else:
        await message.reply(f"Route not found: {tg_display} ({tg_id}) → {max_display} ({max_id})")
