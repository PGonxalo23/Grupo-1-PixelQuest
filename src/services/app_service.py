"""Casos de uso y flujo principal de una partida de Pixel Quest."""

from typing import Any, Dict, List, Protocol

from src.domain.exceptions import DomainError, InvalidActionError
from src.domain.models import Enemy, Hero, Item, Room
from src.services.data_manager import PersistenceError


class ApplicationError(Exception):
    """Error controlado de coordinación entre servicios."""


class DataManagerProtocol(Protocol):
    """Contrato mínimo requerido al adaptador de persistencia."""

    def save(self, state: Dict[str, Any]) -> None: ...

    def load(self) -> Dict[str, Any]: ...

    def exists(self) -> bool: ...


class GameService:
    """Coordina una partida sin depender de la interfaz ni del sistema de archivos."""

    SAVE_VERSION = 1
    STATUS_NOT_STARTED = "not_started"
    STATUS_PLAYING = "playing"
    STATUS_VICTORY = "victory"
    STATUS_DEFEAT = "defeat"
    VALID_STATUSES = {
        STATUS_NOT_STARTED,
        STATUS_PLAYING,
        STATUS_VICTORY,
        STATUS_DEFEAT,
    }

    def __init__(self, data_manager: DataManagerProtocol) -> None:
        self._data_manager = data_manager
        self._hero = None
        self._rooms: List[Room] = []
        self._current_room_index = 0
        self._status = self.STATUS_NOT_STARTED

    @property
    def status(self) -> str:
        return self._status

    @property
    def current_room(self) -> Dict[str, Any]:
        """Expone una copia serializable de la habitación actual."""
        return self._current_room_model().to_dict()

    def start_new_game(self, name: str, hero_class: str) -> List[str]:
        """Crea un héroe y la mazmorra determinista del MVP."""
        self._hero = Hero(name, hero_class)
        self._rooms = self._build_rooms()
        self._current_room_index = 0
        self._status = self.STATUS_PLAYING
        return [
            f"Comienza la aventura de {self._hero.name}.",
            self._current_room_model().description,
        ]

    def get_snapshot(self) -> Dict[str, Any]:
        """Devuelve una fotografía serializable sin exponer colecciones internas."""
        if self._status == self.STATUS_NOT_STARTED:
            return {
                "status": self._status,
                "current_room_index": None,
                "total_rooms": 0,
                "hero": None,
                "room": None,
            }

        return {
            "status": self._status,
            "current_room_index": self._current_room_index,
            "total_rooms": len(self._rooms),
            "hero": self._hero.to_dict(),
            "room": self.current_room,
        }

    def collect_item(self) -> List[str]:
        """Añade al inventario el objeto de la habitación actual."""
        self._require_playing()
        room = self._current_room_model()
        if room.enemy is not None and room.enemy.is_alive:
            raise InvalidActionError(
                "No puedes recoger el objeto mientras haya un enemigo vivo."
            )
        if room.item is None:
            raise InvalidActionError("No hay ningún objeto para recoger aquí.")

        item = room.item
        self._hero.add_item(item)
        room.item = None
        return [f"Recogiste {item.name}."]

    def equip_item(self, index: int) -> List[str]:
        """Equipa un objeto del inventario delegando la regla al modelo Hero."""
        self._require_playing()
        if isinstance(index, bool) or not isinstance(index, int):
            raise InvalidActionError("El índice del inventario debe ser un entero.")

        self._hero.equip_item(index)
        item = self._hero.inventory[index]
        return [
            f"Equipaste {item.name}.",
            f"Ataque: {self._hero.attack}. Defensa: {self._hero.defense}.",
        ]

    def attack(self) -> List[str]:
        """Ejecuta un ataque del héroe y el contraataque del enemigo si sobrevive."""
        self._require_playing()
        room = self._current_room_model()
        enemy = room.enemy
        if enemy is None:
            raise InvalidActionError("No hay un enemigo en esta habitación.")
        if not enemy.is_alive:
            raise InvalidActionError("El enemigo de esta habitación ya fue derrotado.")

        messages = []
        damage = enemy.receive_damage(self._hero.attack)
        messages.append(
            f"{self._hero.name} causa {damage} de daño a {enemy.name}."
        )

        if not enemy.is_alive:
            messages.append(f"Derrotaste a {enemy.name}.")
            if enemy.is_boss and room.is_final:
                self._status = self.STATUS_VICTORY
                messages.append("¡Victoria! Derrotaste al guardián final.")
            return messages

        damage = self._hero.receive_damage(enemy.attack)
        messages.append(f"{enemy.name} causa {damage} de daño a {self._hero.name}.")
        if not self._hero.is_alive:
            self._status = self.STATUS_DEFEAT
            messages.append("Derrota. Tu héroe ha caído.")
        return messages

    def advance(self) -> List[str]:
        """Avanza a la siguiente habitación cuando el encuentro está resuelto."""
        self._require_playing()
        enemy = self._current_room_model().enemy
        if enemy is not None and enemy.is_alive:
            raise InvalidActionError(
                "Debes derrotar al enemigo antes de avanzar."
            )
        if self._current_room_index >= len(self._rooms) - 1:
            raise InvalidActionError("No hay otra habitación disponible.")

        self._current_room_index += 1
        return [f"Avanzas a: {self._current_room_model().description}"]

    def export_state(self) -> Dict[str, Any]:
        """Convierte la partida actual al contrato serializable de persistencia."""
        self._require_game_started()
        return {
            "version": self.SAVE_VERSION,
            "status": self._status,
            "current_room": self._current_room_index,
            "hero": self._hero.to_dict(),
            "rooms": [room.to_dict() for room in self._rooms],
        }

    def restore_state(self, data: Dict[str, Any]) -> List[str]:
        """Reconstruye una partida después de validar su estructura básica."""
        try:
            status, room_index, hero_data, rooms_data = self._validate_state_data(data)
            hero = Hero.from_dict(hero_data)
            rooms = [Room.from_dict(room_data) for room_data in rooms_data]
            self._validate_restored_models(status, room_index, hero, rooms)
        except InvalidActionError:
            raise
        except (AttributeError, DomainError, KeyError, TypeError, ValueError) as exc:
            raise InvalidActionError("El estado guardado está incompleto o dañado.") from exc

        self._hero = hero
        self._rooms = rooms
        self._current_room_index = room_index
        self._status = status
        return ["Partida restaurada correctamente."]

    def save_game(self) -> List[str]:
        """Delega el guardado al administrador de datos recibido."""
        save = self._require_data_manager_method("save")
        try:
            save(self.export_state())
        except PersistenceError as exc:
            raise ApplicationError(str(exc)) from exc
        return ["Partida guardada correctamente."]

    def load_game(self) -> List[str]:
        """Carga un estado y reconstruye los modelos de dominio."""
        exists = self._require_data_manager_method("exists")
        load = self._require_data_manager_method("load")
        try:
            if not exists():
                raise InvalidActionError("No existe una partida guardada.")
            return self.restore_state(load())
        except PersistenceError as exc:
            raise ApplicationError(str(exc)) from exc

    @staticmethod
    def _build_rooms() -> List[Room]:
        sword = Item("Espada", "weapon", attack_bonus=3)
        armor = Item("Armadura", "armor", defense_bonus=2)
        goblin = Enemy("Goblin", max_health=12, attack=5, defense=1)
        boss = Enemy(
            "Guardián final",
            max_health=25,
            attack=8,
            defense=3,
            is_boss=True,
        )
        return [
            Room(
                0,
                "Entrada de la mazmorra",
                item=sword,
            ),
            Room(
                1,
                "Sala del Goblin",
                enemy=goblin,
                item=armor,
            ),
            Room(
                2,
                "Cámara del guardián final",
                enemy=boss,
                is_final=True,
            ),
        ]

    def _require_game_started(self) -> None:
        if self._hero is None or not self._rooms:
            raise InvalidActionError("Primero debes iniciar o cargar una partida.")

    def _require_playing(self) -> None:
        self._require_game_started()
        if not self._hero.is_alive:
            self._status = self.STATUS_DEFEAT
            raise InvalidActionError("El héroe está derrotado.")
        if self._status != self.STATUS_PLAYING:
            raise InvalidActionError("La partida ya terminó.")

    def _current_room_model(self) -> Room:
        self._require_game_started()
        return self._rooms[self._current_room_index]

    def _require_data_manager_method(self, method_name: str):
        method = getattr(self._data_manager, method_name, None)
        if not callable(method):
            raise InvalidActionError(
                f"El administrador de datos no permite {method_name}."
            )
        return method

    @classmethod
    def _validate_state_data(cls, data):
        if not isinstance(data, dict):
            raise InvalidActionError("El estado guardado debe ser un objeto.")
        version = data.get("version")
        if (
            isinstance(version, bool)
            or not isinstance(version, int)
            or version != cls.SAVE_VERSION
        ):
            raise InvalidActionError("La versión del guardado no es compatible.")

        status = data.get("status")
        if not isinstance(status, str) or status not in cls.VALID_STATUSES - {
            cls.STATUS_NOT_STARTED
        }:
            raise InvalidActionError("El estado de partida guardado no es válido.")

        room_index = data.get("current_room")
        if isinstance(room_index, bool) or not isinstance(room_index, int):
            raise InvalidActionError("El índice de habitación no es válido.")

        hero_data = data.get("hero")
        if not isinstance(hero_data, dict):
            raise InvalidActionError("Los datos del héroe no son válidos.")
        cls._validate_character_health(hero_data, "héroe")
        inventory = hero_data.get("inventory")
        if not isinstance(inventory, list) or not all(
            isinstance(item, dict) for item in inventory
        ):
            raise InvalidActionError("El inventario guardado no es válido.")
        for equipment_key in ("weapon", "armor"):
            equipment = hero_data.get(equipment_key)
            if equipment is not None and not isinstance(equipment, dict):
                raise InvalidActionError("El equipamiento guardado no es válido.")

        rooms_data = data.get("rooms")
        if not isinstance(rooms_data, list) or not rooms_data:
            raise InvalidActionError("El guardado no contiene habitaciones.")
        if room_index < 0 or room_index >= len(rooms_data):
            raise InvalidActionError("La habitación guardada no existe.")
        for room_data in rooms_data:
            cls._validate_room_data(room_data)
        return status, room_index, hero_data, rooms_data

    @classmethod
    def _validate_room_data(cls, room_data):
        if not isinstance(room_data, dict):
            raise InvalidActionError("Una habitación guardada no es válida.")
        number = room_data.get("number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise InvalidActionError("El número de habitación no es válido.")
        if not isinstance(room_data.get("description"), str):
            raise InvalidActionError("La descripción de habitación no es válida.")
        if not isinstance(room_data.get("is_final", False), bool):
            raise InvalidActionError("La marca de habitación final no es válida.")

        enemy_data = room_data.get("enemy")
        if enemy_data is not None:
            if not isinstance(enemy_data, dict):
                raise InvalidActionError("Los datos del enemigo no son válidos.")
            cls._validate_character_health(enemy_data, "enemigo")
            if not isinstance(enemy_data.get("is_boss", False), bool):
                raise InvalidActionError("La marca de jefe no es válida.")

        item_data = room_data.get("item")
        if item_data is not None and not isinstance(item_data, dict):
            raise InvalidActionError("Los datos del objeto no son válidos.")

    @staticmethod
    def _validate_character_health(character_data, label):
        max_health = character_data.get("max_health")
        health = character_data.get("health")
        if (
            isinstance(max_health, bool)
            or not isinstance(max_health, int)
            or max_health <= 0
            or isinstance(health, bool)
            or not isinstance(health, int)
            or health < 0
            or health > max_health
        ):
            raise InvalidActionError(f"La vida guardada del {label} no es válida.")

    @classmethod
    def _validate_restored_models(cls, status, room_index, hero, rooms):
        if hero.health < 0 or hero.health > hero.max_health:
            raise InvalidActionError("La vida reconstruida del héroe no es válida.")
        current_room = rooms[room_index]
        final_bosses = [
            (index, room.enemy)
            for index, room in enumerate(rooms)
            if room.is_final
            and room.enemy is not None
            and room.enemy.is_boss
        ]
        if len(final_bosses) != 1:
            raise InvalidActionError("El guardado debe contener un único jefe final.")
        final_boss_index, final_boss = final_bosses[0]
        if final_boss_index != len(rooms) - 1:
            raise InvalidActionError("El jefe final debe estar en la última habitación.")
        final_boss_defeated = not final_boss.is_alive

        if status == cls.STATUS_PLAYING and (
            not hero.is_alive or final_boss_defeated
        ):
            raise InvalidActionError("El estado playing no coincide con la partida.")
        if status == cls.STATUS_DEFEAT and hero.is_alive:
            raise InvalidActionError("El estado defeat requiere un héroe derrotado.")
        if status == cls.STATUS_DEFEAT and final_boss_defeated:
            raise InvalidActionError("Una derrota no puede tener al jefe final vencido.")
        if status == cls.STATUS_VICTORY and (
            not hero.is_alive
            or not final_boss_defeated
            or room_index != final_boss_index
            or current_room.enemy is not final_boss
        ):
            raise InvalidActionError("El estado victory no coincide con el jefe final.")
