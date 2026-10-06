import copy
import math
import tempfile
import unittest
from pathlib import Path

from src.domain.exceptions import InvalidActionError, ValidationError
from src.domain.models import Hero
from src.services.app_service import GameService
from src.services.data_manager import DataManager
from src.ui.cinematic import OpeningCinematic
from src.ui.world import ExplorationWorld


class CaveCombatTests(unittest.TestCase):
    def build(self, hero_class="mage", boss=True, data=None):
        service = GameService(data)
        service.start_new_game("Ámbar", hero_class)
        service.collect_item()
        service.equip_item(0)
        service.advance()
        if boss:
            state = service.export_state()
            state["current_room"] = 2
            service.restore_state(state)
        return service

    def test_class_weapon_is_collected_but_not_automatically_equipped(self):
        for hero_class, kind in (("warrior", "sword"), ("mage", "staff")):
            service = GameService(None)
            service.start_new_game("Ada", hero_class)
            self.assertEqual(kind, service.current_room["item"]["weapon_kind"])
            service.collect_item()
            self.assertIsNone(service.get_snapshot()["hero"]["weapon"])
            service.equip_item(0)
            self.assertEqual(kind, service.get_snapshot()["hero"]["weapon"]["weapon_kind"])

    def test_fire_spends_15_on_cast_and_damage_only_on_impact(self):
        service = self.build()
        before = service.get_snapshot()
        spell = service.cast_fire()
        self.assertEqual(85, service.get_snapshot()["hero"]["mana"])
        self.assertEqual(before["room"]["enemy"]["health"], service.current_room["enemy"]["health"])
        service.resolve_fire(spell)
        self.assertEqual(15, service.current_room["enemy"]["health"])
        self.assertEqual(before["hero"]["health"], service.get_snapshot()["hero"]["health"])
        with self.assertRaises(InvalidActionError):
            service.resolve_fire(spell)

    def test_six_spells_then_rejects_insufficient_mana_without_mutating_state(self):
        service = self.build()
        for _ in range(6):
            service.cancel_fire(service.cast_fire())
        before = service.export_state()
        self.assertEqual(10, before["hero"]["mana"])
        with self.assertRaises(ValidationError):
            service.cast_fire()
        self.assertEqual(before, service.export_state())

    def test_first_death_restores_mana_and_creates_one_drop(self):
        service = self.build(boss=False)
        self.assertIsNone(service.current_room["item"])
        self.assertEqual("Armadura", service.current_room["drop"]["name"])
        spell = service.cast_fire()
        service.resolve_fire(spell)
        self.assertEqual(100, service.get_snapshot()["hero"]["mana"])
        self.assertEqual("Armadura", service.current_room["item"]["name"])
        self.assertIsNone(service.current_room["drop"])
        service.collect_item()
        state = service.export_state()
        state["hero"]["mana"] = 40
        service.restore_state(state)
        self.assertEqual(40, service.get_snapshot()["hero"]["mana"])
        self.assertIsNone(service.current_room["item"])
        with self.assertRaises(InvalidActionError):
            service.resolve_fire(spell)
        with self.assertRaises(InvalidActionError):
            service.collect_item()

    def test_sword_and_enemy_attacks_are_independent(self):
        service = self.build("warrior", boss=False)
        health = service.get_snapshot()["hero"]["health"]
        service.melee_attack()
        self.assertEqual(health, service.get_snapshot()["hero"]["health"])
        service.enemy_attack()
        self.assertEqual(health - 1, service.get_snapshot()["hero"]["health"])
        service.melee_attack()
        with self.assertRaises(InvalidActionError):
            service.enemy_attack()

    def test_pending_fire_cannot_be_saved_or_loaded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            service = self.build(data=DataManager(path))
            spell = service.cast_fire()
            with self.assertRaises(InvalidActionError):
                service.save_game()
            with self.assertRaises(InvalidActionError):
                service.load_game()
            self.assertFalse(path.exists())
            service.cancel_fire(spell)
            service.save_game()
            service.load_game()
            self.assertEqual(85, service.get_snapshot()["hero"]["mana"])

    def test_corrupt_mana_or_drop_preserves_current_game(self):
        service = self.build()
        before = service.export_state()
        for value in (True, -1, 101, "85", 85.0, None):
            with self.subTest(mana=value):
                invalid = copy.deepcopy(before)
                invalid["hero"]["mana"] = value
                with self.assertRaises(InvalidActionError):
                    service.restore_state(invalid)
                self.assertEqual(before, service.export_state())
        invalid = copy.deepcopy(before)
        invalid["rooms"][1]["enemy"]["health"] = 0
        with self.assertRaises(InvalidActionError):
            service.restore_state(invalid)
        self.assertEqual(before, service.export_state())

    def test_migrate_v1_staff_and_hidden_drop_without_mutating_input(self):
        service = self.build(boss=False)
        legacy = service.export_state()
        legacy["version"] = 1
        del legacy["hero"]["mana"]
        del legacy["hero"]["max_mana"]
        for item in legacy["hero"]["inventory"] + [legacy["hero"]["weapon"]]:
            item.pop("weapon_kind")
            item["name"] = "Espada"
        legacy["rooms"][1]["item"] = legacy["rooms"][1].pop("drop")
        original = copy.deepcopy(legacy)
        service.restore_state(legacy)
        self.assertEqual(original, legacy)
        self.assertEqual(2, service.export_state()["version"])
        self.assertEqual("staff", service.get_snapshot()["hero"]["weapon"]["weapon_kind"])
        self.assertEqual(100, service.get_snapshot()["hero"]["mana"])
        self.assertIsNone(service.current_room["item"])
        self.assertEqual("Armadura", service.current_room["drop"]["name"])

    def test_mana_is_class_bound_and_serializable(self):
        mage = Hero("Ada", "mage")
        mage.spend_mana(15)
        self.assertEqual(85, Hero.from_dict(mage.to_dict()).mana)
        warrior = Hero("Ada", "warrior")
        self.assertEqual(0, warrior.max_mana)
        with self.assertRaises(ValidationError):
            warrior.spend_mana(15)


class RealtimeWorldTests(unittest.TestCase):
    def test_sword_range_is_two_character_heights(self):
        service = GameService(None)
        service.start_new_game("Ada", "warrior")
        service.collect_item()
        service.equip_item(0)
        service.advance()
        world = ExplorationWorld()
        world.enter_room(1)
        world.position = (world.ENEMY[0] - 144, 240)
        self.assertTrue(world.can_attack(service.get_snapshot()))
        world.position = (world.position[0] - 1, 240)
        self.assertFalse(world.can_attack(service.get_snapshot()))

    def test_enemy_navigates_around_rock_without_crossing_it(self):
        world = ExplorationWorld()
        world.position, world.enemy_position = (320, 120), (144, 120)
        for _ in range(160):
            world.tick_cooldowns(0.05)
            world.update_enemy(0.05, True)
            self.assertTrue(world._static_valid(world.enemy_position, world.ENEMY_RADIUS))
        self.assertLess(world.distance_to(world.enemy_position), world.CONTACT_RANGE + 1)

    def test_contact_frequency_is_independent_of_frame_rate(self):
        counts = []
        for dt in (1 / 30, 1 / 60, 1 / 120):
            world = ExplorationWorld()
            world.position, world.enemy_position = (500, 240), (540, 240)
            hits = 0
            for _ in range(round(5 / dt)):
                world.tick_cooldowns(dt)
                hits += world.update_enemy(dt, True)
            counts.append(hits)
        self.assertEqual([4, 4, 4], counts)

    def test_dead_enemy_never_moves_or_attacks(self):
        world = ExplorationWorld()
        position = world.enemy_position
        for _ in range(100):
            world.tick_cooldowns(0.05)
            self.assertFalse(world.update_enemy(0.05, False))
        self.assertEqual(position, world.enemy_position)

    def test_projectile_collides_with_rock_and_cannot_tunnel(self):
        world = ExplorationWorld()
        world.position, world.enemy_position = (180, 120), (320, 120)
        world.launch_fire(17)
        hits, misses = [], []
        for _ in range(20):
            h, m = world.update_projectiles(0.1, True)
            hits.extend(h)
            misses.extend(m)
        self.assertEqual([], hits)
        self.assertEqual([17], misses)

    def test_view_restores_enemy_loot_and_attack_cooldowns(self):
        world = ExplorationWorld()
        world.enter_room(1)
        world.position, world.enemy_position = (480, 240), (540, 240)
        world.hero_cooldown, world.enemy_cooldown = 0.4, 0.8
        world.mark_enemy_defeated()
        state = world.to_dict()
        other = ExplorationWorld()
        self.assertTrue(other.restore(state, 1, False))
        self.assertEqual(state, other.to_dict())
        state["enemy_position"] = [math.nan, 240]
        self.assertFalse(other.restore(state, 1, True))


class CinematicTests(unittest.TestCase):
    def test_fades_sequence_and_completion(self):
        intro = OpeningCinematic()
        self.assertEqual(0, intro.alpha)
        self.assertEqual("Ellos te lo arrebataron…", intro.message)
        intro.update(intro.FADE_IN)
        self.assertEqual(255, intro.alpha)
        intro.update(intro.HOLD + intro.FADE_OUT)
        self.assertEqual(0, intro.alpha)
        intro.update(intro.GAP)
        self.assertEqual("Encuéntralos y destrúyelos…", intro.message)
        intro.update(intro.MESSAGE_DURATION)
        self.assertEqual("Venga a tu familia…", intro.message)
        intro.update(intro.MESSAGE_DURATION)
        self.assertTrue(intro.finished)
        self.assertEqual(0, intro.alpha)
