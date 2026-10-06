import json
import unittest

from src.domain.exceptions import InvalidActionError
from src.domain.models import Enemy
from src.services.app_service import GameService


class FakeDataManager:
    def __init__(self):
        self.serialized_state = None

    def save(self, state):
        self.serialized_state = json.dumps(state, ensure_ascii=False)

    def load(self):
        return json.loads(self.serialized_state)

    def exists(self):
        return self.serialized_state is not None


class GameServiceTests(unittest.TestCase):
    def setUp(self):
        self.data_manager = FakeDataManager()
        self.service = GameService(self.data_manager)

    def start_game(self, hero_class="warrior"):
        self.service.start_new_game("Ada", hero_class)

    def defeat_current_enemy(self):
        while self.service.get_snapshot()["room"]["enemy"]["health"] > 0:
            self.service.attack()

    def test_initial_state_has_no_active_game(self):
        snapshot = self.service.get_snapshot()

        self.assertEqual("not_started", snapshot["status"])
        self.assertIsNone(snapshot["hero"])
        self.assertIsNone(snapshot["room"])

    def test_new_game_creates_hero_and_first_room(self):
        messages = self.service.start_new_game("Ada", "warrior")
        snapshot = self.service.get_snapshot()

        self.assertEqual("playing", self.service.status)
        self.assertEqual("Ada", snapshot["hero"]["name"])
        self.assertEqual(0, snapshot["room"]["number"])
        self.assertEqual(3, snapshot["total_rooms"])
        self.assertTrue(messages)

    def test_collect_and_equip_weapon_updates_attack(self):
        self.start_game()

        self.service.collect_item()
        messages = self.service.equip_item(0)
        snapshot = self.service.get_snapshot()

        self.assertEqual("Espada", snapshot["hero"]["weapon"]["name"])
        self.assertIn("Ataque: 10. Defensa: 4.", messages)

    def test_item_can_only_be_collected_once(self):
        self.start_game()
        self.service.collect_item()

        with self.assertRaises(InvalidActionError):
            self.service.collect_item()

    def test_attack_requires_an_enemy(self):
        self.start_game()

        with self.assertRaises(InvalidActionError):
            self.service.attack()

    def test_cannot_advance_while_enemy_is_alive(self):
        self.start_game()
        self.service.advance()

        with self.assertRaises(InvalidActionError):
            self.service.advance()

    def test_enemy_counterattacks_when_it_survives(self):
        self.start_game()
        self.service.advance()

        messages = self.service.attack()
        snapshot = self.service.get_snapshot()

        self.assertEqual(6, snapshot["room"]["enemy"]["health"])
        self.assertEqual(29, snapshot["hero"]["health"])
        self.assertEqual(2, len(messages))

    def test_defeated_enemy_does_not_counterattack(self):
        self.start_game()
        self.service.advance()
        self.service.attack()
        health_before_final_attack = self.service.get_snapshot()["hero"]["health"]

        messages = self.service.attack()
        snapshot = self.service.get_snapshot()

        self.assertEqual(health_before_final_attack, snapshot["hero"]["health"])
        self.assertEqual(0, snapshot["room"]["enemy"]["health"])
        self.assertIn("Derrotaste a Goblin.", messages)

    def test_item_is_blocked_until_room_enemy_is_defeated(self):
        self.start_game()
        self.service.advance()

        with self.assertRaises(InvalidActionError):
            self.service.collect_item()

        self.defeat_current_enemy()
        self.assertEqual(["Recogiste Armadura."], self.service.collect_item())

    def test_defeating_boss_finishes_with_victory(self):
        self.start_game()
        self.service.collect_item()
        self.service.equip_item(0)
        self.service.advance()
        self.defeat_current_enemy()
        self.service.collect_item()
        self.service.equip_item(1)
        self.service.advance()

        self.defeat_current_enemy()

        self.assertEqual("victory", self.service.status)
        self.assertEqual(
            0,
            self.service.get_snapshot()["room"]["enemy"]["health"],
        )

    def test_hero_death_finishes_with_defeat(self):
        self.start_game()
        state = self.service.export_state()
        state["current_room"] = 1
        state["rooms"][1]["enemy"] = Enemy(
            "Ogro",
            max_health=100,
            attack=50,
            defense=1,
        ).to_dict()
        self.service.restore_state(state)

        self.service.attack()

        self.assertEqual("defeat", self.service.status)
        self.assertEqual(0, self.service.get_snapshot()["hero"]["health"])

    def test_save_and_load_restore_equivalent_state(self):
        self.start_game()
        self.service.collect_item()
        self.service.equip_item(0)
        self.service.advance()
        self.service.attack()
        expected_state = self.service.export_state()
        self.service.save_game()
        restored_service = GameService(self.data_manager)

        restored_service.load_game()

        self.assertEqual(expected_state, restored_service.export_state())

    def test_snapshot_does_not_expose_mutable_internal_state(self):
        self.start_game()
        snapshot = self.service.get_snapshot()
        snapshot["hero"]["name"] = "Nombre alterado"
        snapshot["room"]["description"] = "Sala alterada"

        current_snapshot = self.service.get_snapshot()

        self.assertEqual("Ada", current_snapshot["hero"]["name"])
        self.assertEqual(
            "Entrada de la cueva · los restos del caído",
            current_snapshot["room"]["description"],
        )

    def test_restore_rejects_invalid_version_and_room_index(self):
        self.start_game()
        state = self.service.export_state()
        state["version"] = 99

        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

        state = self.service.export_state()
        state["version"] = True
        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

        state = self.service.export_state()
        state["current_room"] = 99
        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

    def test_restore_rejects_corrupt_nested_data_and_preserves_game(self):
        self.start_game()
        original_state = self.service.export_state()
        state = self.service.export_state()
        state["rooms"][0] = None

        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

        self.assertEqual(original_state, self.service.export_state())

    def test_restore_rejects_invalid_health_type(self):
        self.start_game()
        state = self.service.export_state()
        state["hero"]["health"] = "30"

        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

    def test_restore_rejects_inconsistent_status(self):
        self.start_game()
        state = self.service.export_state()
        state["hero"]["health"] = 0

        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

        state = self.service.export_state()
        state["rooms"][2]["enemy"]["health"] = 0
        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

        state = self.service.export_state()
        state["rooms"][1]["enemy"] = state["rooms"][2]["enemy"]
        state["rooms"][1]["is_final"] = True
        state["rooms"][2]["enemy"] = None
        state["rooms"][2]["is_final"] = False
        with self.assertRaises(InvalidActionError):
            self.service.restore_state(state)

    def test_load_requires_an_existing_save(self):
        with self.assertRaises(InvalidActionError):
            self.service.load_game()


if __name__ == "__main__":
    unittest.main()
