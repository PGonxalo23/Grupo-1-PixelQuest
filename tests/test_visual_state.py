import copy
import math
import tempfile
import unittest
from pathlib import Path

from src.domain.exceptions import InvalidActionError, ValidationError
from src.domain.models import Hero
from src.services.app_service import GameService
from src.services.data_manager import DataManager
from src.ui.visual_persistence import VisualDataManager
from src.ui.world import ExplorationWorld


class AppearanceTests(unittest.TestCase):
    def test_color_change_does_not_change_combat_stats(self):
        hero = Hero("Ámbar", "mage", " #e88c61 ")
        self.assertEqual("#E88C61", hero.color)
        stats = hero.health, hero.attack, hero.defense
        hero.change_color("#59C9A5")
        self.assertEqual(stats, (hero.health, hero.attack, hero.defense))
        with self.assertRaises(ValidationError):
            hero.change_color("blue")
        self.assertEqual("#59C9A5", hero.color)

    def test_legacy_hero_receives_class_default(self):
        for hero_class in ("warrior", "mage"):
            data = Hero("Ada", hero_class).to_dict()
            del data["color"]
            restored = Hero.from_dict(data)
            self.assertEqual(Hero.DEFAULT_COLORS[hero_class], restored.color)

    def test_corrupt_color_rejects_restore_without_mutating_game(self):
        service = GameService(None)
        service.start_new_game("Ada", "warrior", "#E88C61")
        state = service.export_state()
        for color in (123, "#GGGGGG", "", "#123", []):
            with self.subTest(color=color):
                invalid = copy.deepcopy(state)
                invalid["hero"]["color"] = color
                with self.assertRaises(InvalidActionError):
                    service.restore_state(invalid)
                self.assertEqual(state, service.export_state())


class ExplorationTests(unittest.TestCase):
    def test_collision_blocks_walls_and_pillars(self):
        world = ExplorationWorld()
        for _ in range(100):
            world.move(-1, 0, 0.05)
        self.assertGreaterEqual(world.position[0], 32 + world.RADIUS)
        world.position = (180, 120)
        for _ in range(100):
            world.move(1, 0, 0.05)
        self.assertLessEqual(world.position[0], 224 - world.RADIUS)

    def test_diagonal_movement_is_normalized(self):
        straight, diagonal = ExplorationWorld(), ExplorationWorld()
        straight.move(1, 0, 0.05)
        diagonal.move(1, 1, 0.05)
        self.assertAlmostEqual(math.dist(straight.SPAWN, straight.position),
                               math.dist(diagonal.SPAWN, diagonal.position))

    def test_enemy_collision_and_range(self):
        service = GameService(None)
        service.start_new_game("Ada", "warrior")
        service.advance()
        world = ExplorationWorld()
        world.enter_room(1)
        self.assertFalse(world.can_attack(service.get_snapshot()))
        for _ in range(100):
            world.move(1, 0, 0.05, enemy_alive=True)
        self.assertLessEqual(world.position[0], world.ENEMY[0] - 24 - world.RADIUS)
        self.assertTrue(world.can_attack(service.get_snapshot()))

    def test_unsafe_or_stale_positions_fall_back_to_spawn(self):
        world = ExplorationWorld()
        for position in ([math.nan, 240], [math.inf, 240], [True, 240],
                         [-900, 240], [240, 120], [576, 240]):
            with self.subTest(position=position):
                data = {"version": 1, "room_index": 1,
                        "position": position, "facing": "right"}
                self.assertFalse(world.restore(data, 1, enemy_alive=True))
                self.assertEqual(world.SPAWN, world.position)
        self.assertFalse(world.restore(world.to_dict(), 2))
        self.assertEqual(2, world.room_index)


class VisualPersistenceTests(unittest.TestCase):
    def test_real_save_restores_color_equipment_damage_and_position(self):
        with tempfile.TemporaryDirectory() as directory:
            data = DataManager(Path(directory) / "save.json")
            world = ExplorationWorld()
            adapter = VisualDataManager(data, world)
            service = GameService(adapter)
            service.start_new_game("Ámbar", "mage", "#E88C61")
            service.collect_item()
            service.equip_item(0)
            service.advance()
            world.enter_room(1)
            world.position = (496, 240)
            service.attack()
            expected = service.export_state()
            service.save_game()
            other_world = ExplorationWorld()
            other_adapter = VisualDataManager(data, other_world)
            restored = GameService(other_adapter)
            restored.load_game()
            self.assertTrue(other_adapter.restore_view(restored.get_snapshot()))
            self.assertEqual(expected, restored.export_state())
            self.assertEqual(world.position, other_world.position)

    def test_console_v1_save_without_visual_fields_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            data = DataManager(Path(directory) / "save.json")
            service = GameService(data)
            service.start_new_game("Ada", "warrior")
            service.advance()
            state = service.export_state()
            del state["hero"]["color"]
            data.save(state)
            world = ExplorationWorld()
            adapter = VisualDataManager(data, world)
            loaded = GameService(adapter)
            loaded.load_game()
            self.assertFalse(adapter.restore_view(loaded.get_snapshot()))
            self.assertEqual(1, world.room_index)
            self.assertEqual(world.SPAWN, world.position)
            self.assertEqual("#59C9A5", loaded.get_snapshot()["hero"]["color"])
