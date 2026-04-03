from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
import uuid
from pathlib import Path


DB_MODULE_PATH = Path(__file__).resolve().parents[1] / "db.py"


def load_db_module(db_path: Path):
    module_name = f"db_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, DB_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load db module for tests")

    module = importlib.util.module_from_spec(spec)
    previous_db_path = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = str(db_path)

    try:
        spec.loader.exec_module(module)
    finally:
        if previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = previous_db_path

    return module


class DbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        db_path = Path(self.temp_dir.name) / "routes.json"
        self.db_module = load_db_module(db_path)
        self.addCleanup(self.db_module.db.close)

    def test_route_crud_and_grouping(self) -> None:
        self.assertEqual(self.db_module.get_all_routes(), [])
        self.assertFalse(self.db_module.route_exists(-100, -10))

        self.db_module.add_route("@source", "https://max.ru/one", -100, -10)
        self.db_module.add_route("@source", "https://max.ru/two", -100, -20)
        self.db_module.add_route("@source", "https://max.ru/two", -100, -20)

        self.assertTrue(self.db_module.route_exists(-100, -10))
        self.assertEqual(self.db_module.get_channel_links(), {-100: [-10, -20]})
        self.assertEqual(len(self.db_module.get_all_routes()), 3)

        grouped = self.db_module.get_grouped_routes()
        self.assertIn("@source (-100)", grouped)
        self.assertEqual(
            grouped["@source (-100)"][0],
            {"max_target": "https://max.ru/one", "max_target_id": -10},
        )
        self.assertEqual(len(grouped["@source (-100)"]), 3)

        removed = self.db_module.remove_route(-100, -20)
        self.assertEqual(len(removed), 2)
        self.assertFalse(self.db_module.route_exists(-100, -20))
        self.assertEqual(len(self.db_module.get_all_routes()), 1)

    def test_admin_crud(self) -> None:
        self.assertEqual(self.db_module.get_all_admins(), [])
        self.assertFalse(self.db_module.admin_exists(123))

        self.db_module.add_admin(123)
        self.db_module.add_admin(456)

        self.assertTrue(self.db_module.admin_exists(123))
        self.assertEqual(sorted(self.db_module.get_all_admins()), [123, 456])

        removed = self.db_module.remove_admin(123)
        self.assertEqual(len(removed), 1)
        self.assertFalse(self.db_module.admin_exists(123))
        self.assertEqual(self.db_module.remove_admin(999), [])


if __name__ == "__main__":
    unittest.main()
