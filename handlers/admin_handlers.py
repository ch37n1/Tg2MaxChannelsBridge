"""
Admin command handlers for route management.
"""

import csv
import io
import tempfile

from aiogram import F
from aiogram.filters import Command
from aiogram.types import Message as TgMessage, BufferedInputFile

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


@tg_dp.message(Command("import"))
@admin_only
async def handle_import(message: TgMessage):
    """Import routes from CSV file attachment."""
    # Check for document attachment
    if not message.document:
        await message.reply(
            "Please send a CSV file with /import as caption.\n\n"
            "CSV format:\n"
            "tg_source,max_target\n"
            "@my_channel,https://max.ru/target\n"
            "-1001234567890,-69520134802093"
        )
        return

    # Download file
    file = await tg_bot.get_file(message.document.file_id)
    if not file.file_path:
        await message.reply("Failed to download file.")
        return

    file_data = await tg_bot.download_file(file.file_path)
    if not file_data:
        await message.reply("Failed to download file.")
        return

    # Parse CSV
    try:
        content = file_data.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(content))

        # Validate headers
        if not reader.fieldnames or "tg_source" not in reader.fieldnames or "max_target" not in reader.fieldnames:
            await message.reply("Invalid CSV format. Required headers: tg_source, max_target")
            return

        rows = list(reader)
    except Exception as e:
        await message.reply(f"Failed to parse CSV: {e}")
        return

    if not rows:
        await message.reply("CSV file is empty.")
        return

    # Process rows
    success_count = 0
    duplicate_count = 0
    errors = []

    for i, row in enumerate(rows, start=2):  # Start at 2 (line 1 is header)
        tg_input = row.get("tg_source", "").strip()
        max_input = row.get("max_target", "").strip()

        if not tg_input or not max_input:
            errors.append(f"Line {i}: empty value")
            continue

        # Resolve Telegram source
        try:
            tg_display, tg_id = await resolve_tg_chat(tg_bot, tg_input)
        except ResolveError as e:
            errors.append(f"Line {i}: {e}")
            continue

        # Resolve Max target
        try:
            max_display, max_id = await resolve_max_chat(max_bot, max_input)
        except ResolveError as e:
            errors.append(f"Line {i}: {e}")
            continue

        # Check for duplicate
        if db.route_exists(tg_id, max_id):
            duplicate_count += 1
            continue

        # Add route
        db.add_route(tg_display, max_display, tg_id, max_id)
        success_count += 1

    # Build report
    report_parts = [f"Imported {success_count} route(s)"]
    if duplicate_count:
        report_parts.append(f"{duplicate_count} duplicate(s) skipped")
    if errors:
        report_parts.append(f"{len(errors)} error(s)")
        # Show first 5 errors
        error_details = "\n".join(errors[:5])
        if len(errors) > 5:
            error_details += f"\n... and {len(errors) - 5} more"
        report_parts.append(f"\nErrors:\n{error_details}")

    await message.reply(", ".join(report_parts[:3]) + (report_parts[3] if len(report_parts) > 3 else ""))


@tg_dp.message(Command("export"))
@admin_only
async def handle_export(message: TgMessage):
    """Export all routes to CSV file."""
    routes = db.get_all_routes()

    if not routes:
        await message.reply("No routes to export.")
        return

    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["tg_source", "max_target"])
    writer.writeheader()

    for route in routes:
        writer.writerow({
            "tg_source": route["tg_source"],
            "max_target": route["max_target"],
        })

    csv_content = output.getvalue().encode("utf-8")

    # Send as document
    document = BufferedInputFile(csv_content, filename="routes.csv")
    await message.reply_document(document, caption=f"Exported {len(routes)} route(s)")
