import importlib
import tempfile
import unittest
from pathlib import Path

from src.services.app_service import GameService
from src.services.data_manager import DataManager
from src.ui.cli_interface import MenuCLI


class ScriptedInput:
    def __init__(self, values):
        self._values = iter(values)
        self.prompts = []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        try:
            return next(self._values)
        except StopIteration as exc:
            raise AssertionError(
                f"La prueba no preparó una respuesta para: {prompt}"
            ) from exc


class MenuCLIIntegrationTests(unittest.TestCase):
    def build_cli(self, inputs, save_path):
        self.outputs = []
        service = GameService(DataManager(save_path))
        cli = MenuCLI(
            service,
            input_func=ScriptedInput(inputs),
            output_func=self.outputs.append,
        )
        return cli, service

    def test_main_module_can_be_imported_without_starting_menu(self):
        module = importlib.import_module("src.main")

        self.assertTrue(callable(module.main))

    def test_user_can_exit_main_menu(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cli, _ = self.build_cli(
                ["0"],
                Path(temp_dir) / "save.json",
            )

            cli.run()

        self.assertIn("Hasta la próxima aventura.", self.outputs)

    def test_invalid_main_option_is_requested_again(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cli, _ = self.build_cli(
                ["opción incorrecta", "0"],
                Path(temp_dir) / "save.json",
            )

            cli.run()

        self.assertIn("Opción inválida. Intenta nuevamente.", self.outputs)

    def test_domain_error_is_shown_without_closing_application(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cli, _ = self.build_cli(
                ["1", "   ", "1", "0"],
                Path(temp_dir) / "save.json",
            )

            cli.run()

        self.assertTrue(
            any(message.startswith("Error: ") for message in self.outputs)
        )
        self.assertIn("Hasta la próxima aventura.", self.outputs)

    def test_complete_cli_game_finishes_with_victory(self):
        inputs = [
            "1",  # Nueva partida
            "Ada",
            "1",  # Guerrero
            "2",  # Recoger espada
            "3", "1",  # Equipar espada
            "5",  # Avanzar al Goblin
            "4", "4",  # Derrotar Goblin
            "2",  # Recoger armadura
            "3", "2",  # Equipar armadura
            "5",  # Avanzar al jefe
            "4", "4", "4", "4",  # Derrotar jefe
            "0",  # Salir desde menú principal
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            cli, service = self.build_cli(
                inputs,
                Path(temp_dir) / "save.json",
            )

            cli.run()

        self.assertEqual("victory", service.status)
        self.assertTrue(
            any(
                "*** VICTORIA: Pixel Quest completado ***" in message
                for message in self.outputs
            )
        )

    def test_saved_game_can_be_loaded_from_main_menu(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "save.json"
            initial_service = GameService(DataManager(save_path))
            initial_service.start_new_game("Ada", "mage")
            initial_service.save_game()
            cli, loaded_service = self.build_cli(
                ["2", "0", "0"],
                save_path,
            )

            cli.run()

        self.assertEqual("playing", loaded_service.status)
        self.assertEqual(
            "Ada",
            loaded_service.get_snapshot()["hero"]["name"],
        )
        self.assertIn("Partida restaurada correctamente.", self.outputs)

    def test_mage_cli_staff_mana_and_victory(self):
        inputs = ["1", "Ada", "2", "2", "3", "1", "5", "4", "2", "3", "2",
                  "5", "4", "1", "4", "4", "0"]
        with tempfile.TemporaryDirectory() as temp_dir:
            cli, service = self.build_cli(inputs, Path(temp_dir) / "save.json")
            cli.run()
        self.assertEqual("victory", service.status)
        self.assertIn("Maná: 85/100", self.outputs)
        self.assertEqual("staff", service.get_snapshot()["hero"]["weapon"]["weapon_kind"])

    def test_game_can_be_saved_and_loaded_entirely_from_cli(self):
        inputs = [
            "1", "Ada", "2",  # Nueva partida como Mago
            "6",  # Guardar desde el menú de partida
            "0",  # Volver al menú principal
            "2",  # Cargar desde el menú principal
            "0",  # Volver nuevamente al menú principal
            "0",  # Salir
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "save.json"
            cli, service = self.build_cli(inputs, save_path)

            cli.run()

            self.assertTrue(save_path.is_file())
        self.assertEqual("playing", service.status)
        self.assertIn("Partida guardada correctamente.", self.outputs)
        self.assertIn("Partida restaurada correctamente.", self.outputs)

    def test_corrupt_save_is_reported_and_menu_continues(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "save.json"
            save_path.write_bytes(b"\xff\xfe\xfa")
            cli, _ = self.build_cli(["2", "0"], save_path)

            cli.run()

        self.assertTrue(
            any(
                message.startswith("Error: ") and "UTF-8" in message
                for message in self.outputs
            )
        )
        self.assertIn("Hasta la próxima aventura.", self.outputs)

    def test_invalid_action_inside_game_is_reported(self):
        inputs = [
            "1", "Ada", "1",  # Nueva partida
            "4",  # Atacar en una habitación sin enemigo
            "0",  # Volver al menú principal
            "0",  # Salir
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            cli, _ = self.build_cli(
                inputs,
                Path(temp_dir) / "save.json",
            )

            cli.run()

        self.assertIn("Error: No hay un enemigo en esta habitación.", self.outputs)


if __name__ == "__main__":
    unittest.main()
