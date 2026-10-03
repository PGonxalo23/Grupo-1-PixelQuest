"""Punto de entrada ejecutable de Pixel Quest."""

from src.services.app_service import GameService
from src.services.data_manager import DataManager
from src.ui.cli_interface import MenuCLI


def main() -> None:
    data_manager = DataManager()
    service = GameService(data_manager)
    MenuCLI(service).run()


if __name__ == "__main__":
    main()
