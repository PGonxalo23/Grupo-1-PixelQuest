"""Integración real de eventos, renderizado y partidas con SDL sin pantalla."""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

try:
    import pygame
except ModuleNotFoundError:
    pygame = None

from src.services.app_service import GameService
from src.services.data_manager import DataManager
from src.ui.visual_persistence import VisualDataManager
from src.ui.world import ExplorationWorld


@unittest.skipIf(pygame is None, "Instala requirements.txt para verificar el RPG gráfico")
class GraphicalIntegrationTests(unittest.TestCase):
    def setUp(self):
        from src.ui.graphical_interface import GraphicalGame

        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "save.json"
        self.world = ExplorationWorld()
        self.data = DataManager(self.path)
        self.adapter = VisualDataManager(self.data, self.world)
        self.service = GameService(self.adapter)
        self.app = GraphicalGame(self.service, self.world, self.adapter)

    def tearDown(self):
        pygame.quit()
        self.directory.cleanup()

    def click(self, action):
        self.app.render()
        buttons = [b for b in self.app.buttons if b.action == action and b.enabled]
        self.assertTrue(buttons, f"No existe botón activo para {action} en {self.app.screen}")
        scale, _, offset = self.app._viewport()
        x, y = buttons[0].rect.center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                  button=1, pos=(round(x * scale + offset[0]),
                                                 round(y * scale + offset[1])))
        self.app.process_event(event)

    def key(self, key):
        self.app.process_event(pygame.event.Event(pygame.KEYDOWN, key=key))

    def create_hero(self, hero_class="warrior"):
        self.click("create")
        self.app.process_event(pygame.event.Event(pygame.TEXTINPUT, text="Ámbar"))
        self.click(f"class:{hero_class}")
        self.click("color:#E86E75")
        self.key(pygame.K_RETURN)
        self.assertEqual("playing", self.app.screen)
        self.assertEqual("#E86E75", self.service.get_snapshot()["hero"]["color"])

    def walk_to(self, target):
        for _ in range(150):
            x, y = self.world.position
            dx, dy = target[0] - x, target[1] - y
            if abs(dx) < 8 and abs(dy) < 8:
                return
            self.app.update(0.025, (0 if abs(dx) < 6 else 1 if dx > 0 else -1,
                                    0 if abs(dy) < 6 else 1 if dy > 0 else -1))
        self.fail(f"No se pudo llegar a {target} desde {self.world.position}")

    def finish_turn(self):
        for _ in range(20):
            self.app.update(0.05, (0, 0))
            self.app.render()

    def test_complete_graphical_game_with_keyboard_and_mouse(self):
        self.complete_game("warrior")

    def test_mage_can_complete_graphical_game_with_spell_animation(self):
        self.complete_game("mage")

    def complete_game(self, hero_class):
        self.create_hero(hero_class)
        self.walk_to(self.world.ITEM)
        self.key(pygame.K_e)
        self.key(pygame.K_i)
        self.click("equip:0")
        self.key(pygame.K_ESCAPE)
        self.walk_to((768, 240))
        self.key(pygame.K_e)
        self.assertEqual(1, self.world.room_index)
        self.walk_to((500, 240))
        while self.service.get_snapshot()["room"]["enemy"]["health"] > 0:
            self.key(pygame.K_SPACE)
            self.finish_turn()
        self.walk_to(self.world.ITEM)
        self.key(pygame.K_e)
        self.key(pygame.K_i)
        self.click("equip:1")
        self.key(pygame.K_ESCAPE)
        self.walk_to((768, 240))
        self.key(pygame.K_e)
        self.assertEqual(2, self.world.room_index)
        self.walk_to((500, 240))
        while self.service.status == "playing":
            self.click("attack")
            self.finish_turn()
        self.assertEqual("victory", self.service.status)
        self.assertEqual("ending", self.app.screen)
        self.click("save")
        self.assertEqual("victory", self.data.load()["status"])
        self.click("menu")
        self.click("load")
        self.assertEqual("ending", self.app.screen)

    def test_attack_cannot_happen_remotely_or_repeat_during_animation(self):
        self.create_hero()
        state = self.service.export_state()
        state["current_room"] = 1
        self.service.restore_state(state)
        self.world.enter_room(1)
        before = self.service.export_state()
        self.key(pygame.K_SPACE)
        self.assertEqual(before, self.service.export_state())
        self.walk_to((500, 240))
        self.key(pygame.K_SPACE)
        after_attack = self.service.export_state()
        self.key(pygame.K_SPACE)
        self.assertEqual(after_attack, self.service.export_state())
        position = self.world.position
        self.app.update(0.05, (1, 0))
        self.assertEqual(position, self.world.position)

    def test_defeat_is_shown_after_counterattack(self):
        self.create_hero()
        state = self.service.export_state()
        state["current_room"] = 2
        state["hero"]["health"] = 1
        self.data.save(state)
        self.key(pygame.K_F9)
        self.walk_to((500, 240))
        self.key(pygame.K_SPACE)
        self.assertEqual("defeat", self.service.status)
        self.key(pygame.K_ESCAPE)
        self.click("resume")
        self.assertEqual("playing", self.app.screen)
        self.finish_turn()
        self.assertEqual("ending", self.app.screen)
        self.assertEqual(0, self.service.get_snapshot()["hero"]["health"])
        self.click("save")
        self.assertEqual("defeat", self.data.load()["status"])

    def test_graphical_color_save_load_and_pause(self):
        self.create_hero()
        self.walk_to((300, 240))
        self.key(pygame.K_c)
        self.click("color:#67B7EA")
        self.click("apply_color")
        self.key(pygame.K_F5)
        expected = self.service.export_state()
        position = self.world.position
        self.key(pygame.K_ESCAPE)
        self.app.update(0.05, (1, 0))
        self.assertEqual(position, self.world.position)
        self.click("menu")
        self.click("load")
        self.assertEqual(expected, self.service.export_state())
        self.assertEqual(position, self.world.position)
        self.app.render()

    def test_failed_load_preserves_game_and_recovers(self):
        self.create_hero()
        expected = self.service.export_state()
        self.path.write_bytes(b"\xff\xfe")
        self.key(pygame.K_F9)
        self.assertEqual(expected, self.service.export_state())
        self.assertEqual("playing", self.app.screen)
        self.assertIn("UTF-8", self.app.notification)
        self.key(pygame.K_F5)
        self.assertEqual(expected["hero"], self.data.load()["hero"])

    def test_resized_window_keeps_clicks_and_all_screens_renderable(self):
        self.app.process_event(pygame.event.Event(pygame.VIDEORESIZE, w=900, h=640))
        self.create_hero()
        for screen in ("playing", "inventory", "appearance", "pause"):
            self.app.screen = screen
            self.app.render()
            self.app.present()
            self.assertTrue(self.app.buttons)
        self.click("resume")
        self.assertEqual("playing", self.app.screen)
