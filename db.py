"""
TinyDB database module for route management.

DB Schema:
{
    "tg_source": str,       # Display string (@nick or ID)
    "max_target": str,      # Display string (https://max.ru/nick or ID)
    "tg_source_id": int,    # Resolved Telegram channel ID
    "max_target_id": int    # Resolved Max channel ID
}
"""

from collections import defaultdict

from tinydb import TinyDB, Query

db = TinyDB("routes.db")
routes_table = db.table("routes")
admins_table = db.table("admins")

Route = Query()
Admin = Query()


def get_all_routes() -> list[dict]:
    """Get all routes as list of dicts."""
    return routes_table.all()


def get_channel_links() -> dict[int, list[int]]:
    """
    Get routes in {tg_id: [max_ids]} format for forwarding.

    Returns:
        Dict mapping Telegram source IDs to lists of Max target IDs.
    """
    result: dict[int, list[int]] = defaultdict(list)

    for route in routes_table.all():
        tg_id = route["tg_source_id"]
        max_id = route["max_target_id"]
        if max_id not in result[tg_id]:
            result[tg_id].append(max_id)

    return dict(result)


def get_grouped_routes() -> dict[str, list[dict]]:
    """
    Get routes grouped by source for /links display.

    Returns:
        Dict mapping display strings to list of route info:
        {
            "@channel1 (-1001234567890)": [
                {"max_target": "https://max.ru/target1", "max_target_id": -695...},
                ...
            ]
        }
    """
    result: dict[str, list[dict]] = defaultdict(list)

    for route in routes_table.all():
        source_key = f"{route['tg_source']} ({route['tg_source_id']})"
        result[source_key].append(
            {
                "max_target": route["max_target"],
                "max_target_id": route["max_target_id"],
            }
        )

    return dict(result)


def add_route(
    tg_source: str, max_target: str, tg_source_id: int, max_target_id: int
) -> int:
    """
    Add a new route.

    Args:
        tg_source: Display string for Telegram source (@nick or ID)
        max_target: Display string for Max target (URL or ID)
        tg_source_id: Resolved Telegram channel ID
        max_target_id: Resolved Max channel ID

    Returns:
        Document ID of the inserted route.
    """
    return routes_table.insert(
        {
            "tg_source": tg_source,
            "max_target": max_target,
            "tg_source_id": tg_source_id,
            "max_target_id": max_target_id,
        }
    )


def remove_route(tg_source_id: int, max_target_id: int) -> list[int]:
    """
    Remove a route by source and target IDs.

    Args:
        tg_source_id: Telegram channel ID
        max_target_id: Max channel ID

    Returns:
        List of removed document IDs (empty if not found).
    """
    return routes_table.remove(
        (Route.tg_source_id == tg_source_id) & (Route.max_target_id == max_target_id)
    )


def route_exists(tg_source_id: int, max_target_id: int) -> bool:
    """
    Check if a route exists.

    Args:
        tg_source_id: Telegram channel ID
        max_target_id: Max channel ID

    Returns:
        True if route exists, False otherwise.
    """
    return routes_table.contains(
        (Route.tg_source_id == tg_source_id) & (Route.max_target_id == max_target_id)
    )


# --- Admin Management ---


def get_all_admins() -> list[int]:
    """
    Get all admin user IDs from the database.

    Returns:
        List of admin Telegram user IDs.
    """
    return [admin["user_id"] for admin in admins_table.all()]


def add_admin(user_id: int) -> int:
    """
    Add a new admin to the database.

    Args:
        user_id: Telegram user ID to add as admin.

    Returns:
        Document ID of the inserted admin.
    """
    return admins_table.insert({"user_id": user_id})


def remove_admin(user_id: int) -> list[int]:
    """
    Remove an admin from the database.

    Args:
        user_id: Telegram user ID to remove.

    Returns:
        List of removed document IDs (empty if not found).
    """
    return admins_table.remove(Admin.user_id == user_id)


def admin_exists(user_id: int) -> bool:
    """
    Check if a user is an admin in the database.

    Args:
        user_id: Telegram user ID to check.

    Returns:
        True if user is an admin, False otherwise.
    """
    return admins_table.contains(Admin.user_id == user_id)
