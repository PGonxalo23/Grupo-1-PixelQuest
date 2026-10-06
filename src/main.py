"""Punto de entrada: RPG 2D por defecto o consola mediante --cli."""

import argparse
import os
import sys
from pathlib import Path

# Permite también el botón «Run Python File» de VS Code.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.app_service import GameService
from src.services.data_manager import DataManager


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pixel Quest · Cueva 2D y combate en tiempo real")
    parser.add_argument("--cli", action="store_true", help="Ejecutar la interfaz de consola")
    parser.add_argument("--save-path", type=Path, default=PROJECT_ROOT / "data" / "savegame.json",
                        help="Ruta del guardado (por defecto: data/savegame.json del proyecto)")
    parser.add_argument("--smoke-test", action="store_true",
                        help="Abrir la interfaz gráfica tres frames y comprobar el arranque")
    args = parser.parse_args(argv)
    data_manager = DataManager(args.save_path)
    if args.cli:
        from src.ui.cli_interface import MenuCLI

        MenuCLI(GameService(data_manager)).run()
        return 0

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    try:
        from src.ui.graphical_interface import GraphicalGame
    except ModuleNotFoundError as exc:
        if exc.name != "pygame":
            raise
        print("Falta Pygame. Instala las dependencias con: python -m pip install -r requirements.txt",
              file=sys.stderr)
        return 1

    from src.ui.visual_persistence import VisualDataManager
    from src.ui.world import ExplorationWorld

    world = ExplorationWorld()
    visual_data_manager = VisualDataManager(data_manager, world)
    service = GameService(visual_data_manager)
    GraphicalGame(service, world, visual_data_manager).run(frame_limit=3 if args.smoke_test else None)
    if args.smoke_test:
        print("Arranque gráfico verificado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
