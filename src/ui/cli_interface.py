"""Interfaz de consola para ejecutar Pixel Quest."""

from typing import Callable, Iterable

from src.domain.exceptions import DomainError
from src.services.app_service import ApplicationError


class MenuCLI:
    """Traduce entradas de texto a operaciones de GameService."""

    def __init__(
        self,
        service,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
    ) -> None:
        self._service = service
        self._input = input_func
        self._output = output_func

    def run(self) -> None:
        self._write("=" * 48)
        self._write("PIXEL QUEST · RPG DE CONSOLA")
        self._write("=" * 48)

        try:
            while True:
                self._show_main_menu()
                choice = self._read_choice(
                    "Selecciona una opción: ",
                    {"0", "1", "2", "3"},
                )
                if choice == "0":
                    self._write("Hasta la próxima aventura.")
                    return
                try:
                    if choice == "1":
                        self._start_new_game()
                    elif choice == "2":
                        self._load_game()
                    else:
                        self._continue_game()
                except (ApplicationError, DomainError) as exc:
                    self._write(f"Error: {exc}")
        except (EOFError, KeyboardInterrupt):
            self._write("\nSesión finalizada por el usuario.")

    def _show_main_menu(self) -> None:
        self._write("\nMENÚ PRINCIPAL")
        self._write("1. Nueva partida")
        self._write("2. Cargar partida")
        self._write("3. Continuar partida actual")
        self._write("0. Salir")

    def _start_new_game(self) -> None:
        name = self._input("Nombre del héroe: ")
        self._write("Elige una clase:")
        self._write("1. Guerrero")
        self._write("2. Mago")
        choice = self._read_choice("Clase: ", {"1", "2"})
        hero_class = "warrior" if choice == "1" else "mage"
        self._write_messages(self._service.start_new_game(name, hero_class))
        self._run_game_loop()

    def _load_game(self) -> None:
        self._write_messages(self._service.load_game())
        if self._service.status == "playing":
            self._run_game_loop()
        else:
            self._show_ending()

    def _continue_game(self) -> None:
        if self._service.status != "playing":
            raise DomainError("No hay una partida activa para continuar.")
        self._run_game_loop()

    def _run_game_loop(self) -> None:
        while self._service.status == "playing":
            self._show_room()
            self._show_game_menu()
            choice = self._read_choice(
                "Acción: ",
                {"0", "1", "2", "3", "4", "5", "6"},
            )
            if choice == "0":
                self._write("Regresaste al menú principal.")
                return
            try:
                self._execute_action(choice)
            except (ApplicationError, DomainError) as exc:
                self._write(f"Error: {exc}")

        self._show_ending()

    def _show_game_menu(self) -> None:
        self._write("\nACCIONES")
        self._write("1. Ver estado")
        self._write("2. Recoger objeto")
        self._write("3. Equipar objeto")
        self._write("4. Atacar")
        self._write("5. Avanzar")
        self._write("6. Guardar partida")
        self._write("0. Volver al menú principal")

    def _execute_action(self, choice: str) -> None:
        if choice == "1":
            self._show_status()
        elif choice == "2":
            self._write_messages(self._service.collect_item())
        elif choice == "3":
            self._equip_item()
        elif choice == "4":
            self._write_messages(self._service.attack())
        elif choice == "5":
            self._write_messages(self._service.advance())
        elif choice == "6":
            self._write_messages(self._service.save_game())

    def _show_room(self) -> None:
        snapshot = self._service.get_snapshot()
        room = snapshot["room"]
        self._write(
            f"\n[{snapshot['current_room_index'] + 1}/{snapshot['total_rooms']}] "
            f"{room['description']}"
        )
        enemy = room.get("enemy")
        if enemy is not None:
            state = "vivo" if enemy["health"] > 0 else "derrotado"
            self._write(
                f"Enemigo: {enemy['name']} · Vida: "
                f"{enemy['health']}/{enemy['max_health']} · {state}"
            )
        item = room.get("item")
        if item is not None:
            self._write(f"Objeto disponible: {item['name']}")

    def _show_status(self) -> None:
        snapshot = self._service.get_snapshot()
        hero = snapshot["hero"]
        class_name = "Guerrero" if hero["hero_class"] == "warrior" else "Mago"
        self._write("\nESTADO DEL HÉROE")
        self._write(f"Nombre: {hero['name']} · Clase: {class_name}")
        self._write(f"Vida: {hero['health']}/{hero['max_health']}")
        if hero["hero_class"] == "mage":
            self._write(f"Maná: {hero['mana']}/{hero['max_mana']}")
        self._write(
            f"Ataque base: {hero['base_attack']} · "
            f"Defensa base: {hero['base_defense']}"
        )
        weapon = hero.get("weapon")
        armor = hero.get("armor")
        self._write(
            f"Arma: {weapon['name'] if weapon else 'Ninguna'} · "
            f"Armadura: {armor['name'] if armor else 'Ninguna'}"
        )
        inventory = hero.get("inventory", [])
        inventory_text = ", ".join(item["name"] for item in inventory)
        self._write(f"Inventario: {inventory_text or 'Vacío'}")

    def _equip_item(self) -> None:
        inventory = self._service.get_snapshot()["hero"].get("inventory", [])
        if not inventory:
            self._write("El inventario está vacío.")
            return

        self._write("\nINVENTARIO")
        for index, item in enumerate(inventory, start=1):
            self._write(f"{index}. {item['name']} ({item['item_type']})")
        valid_choices = {str(index) for index in range(len(inventory) + 1)}
        self._write("0. Cancelar")
        choice = self._read_choice("Objeto a equipar: ", valid_choices)
        if choice == "0":
            return
        self._write_messages(self._service.equip_item(int(choice) - 1))

    def _show_ending(self) -> None:
        if self._service.status == "victory":
            self._write("\n*** VICTORIA: Pixel Quest completado ***")
        elif self._service.status == "defeat":
            self._write("\n*** DERROTA: el héroe ha caído ***")

    def _read_choice(self, prompt: str, valid_choices: Iterable[str]) -> str:
        valid = set(valid_choices)
        while True:
            value = self._input(prompt).strip()
            if value in valid:
                return value
            self._write("Opción inválida. Intenta nuevamente.")

    def _write_messages(self, messages) -> None:
        for message in messages:
            self._write(message)

    def _write(self, message: str) -> None:
        self._output(message)
