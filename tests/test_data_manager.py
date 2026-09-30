import json
import tempfile
import unittest
from pathlib import Path

from src.services.data_manager import (
    DataManager,
    InvalidSaveError,
    PersistenceError,
    SaveNotFoundError,
)


class DataManagerTests(unittest.TestCase):

    def test_exists_before_and_after_save(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            manager = DataManager(path)

            self.assertFalse(manager.exists())

            manager.save({"version": 1})

            self.assertTrue(manager.exists())

    def test_round_trip_preserves_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            manager = DataManager(path)

            expected = {
                "version": 1,
                "status": "playing",
                "current_room": 1
            }

            manager.save(expected)
            result = manager.load()

            self.assertEqual(expected, result)

    def test_round_trip_preserves_unicode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            manager = DataManager(path)

            expected = {
                "version": 1,
                "hero": {
                    "name": "Ámbar"
                }
            }

            manager.save(expected)
            result = manager.load()

            self.assertEqual(expected, result)

    def test_save_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "carpeta" / "save.json"
            manager = DataManager(path)

            manager.save({"version": 1})

            self.assertTrue(path.is_file())

    def test_load_missing_file_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            manager = DataManager(path)

            with self.assertRaises(SaveNotFoundError):
                manager.load()

    def test_load_invalid_json_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"

            path.write_text("{ json roto", encoding="utf-8")

            manager = DataManager(path)

            with self.assertRaises(InvalidSaveError):
                manager.load()

    def test_load_list_root_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"

            with path.open("w", encoding="utf-8") as file:
                json.dump([1, 2, 3], file)

            manager = DataManager(path)

            with self.assertRaises(InvalidSaveError):
                manager.load()

    def test_save_non_serializable_value_raises_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "save.json"
            manager = DataManager(path)

            state = {
                "version": 1,
                "invalid": {1, 2, 3}
            }

            with self.assertRaises(PersistenceError):
                manager.save(state)


if __name__ == "__main__":
    unittest.main()