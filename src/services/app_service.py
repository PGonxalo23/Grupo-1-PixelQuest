"""Casos de uso y flujo principal de una partida de Pixel Quest."""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Protocol

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

    SAVE_VERSION = 2
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
        self._pending_fire = {}
        self._spell_id = 0

    @property
    def status(self) -> str:
        return self._status

    @property
    def current_room(self) -> Dict[str, Any]:
        """Expone una copia serializable de la habitación actual."""
        return self._current_room_model().to_dict()

    @staticmethod
    def get_hero_classes() -> Dict[str, Dict[str, int]]:
        """Estadísticas de creación para la vista, sin exponer el catálogo mutable."""
        return {name: dict(stats) for name, stats in Hero.CLASS_STATS.items()}

    def start_new_game(self, name: str, hero_class: str, color: Optional[str] = None) -> List[str]:
        """Crea un héroe y la mazmorra determinista del MVP."""
        self._hero = Hero(name, hero_class, color)
        self._rooms = self._build_rooms(self._hero.hero_class)
        self._current_room_index = 0
        self._status = self.STATUS_PLAYING
        self._pending_fire.clear()
        return [
            f"Comienza la aventura de {self._hero.name}.",
            self._current_room_model().description,
        ]

    def change_hero_color(self, color: str) -> List[str]:
        """Personalización cosmética: no modifica estadísticas ni consume turnos."""
        self._require_game_started()
        self._hero.change_color(color)
        return ["Color del héroe actualizado."]

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
        """Adaptador de combate por turnos para la consola, sin geometría gráfica."""
        self._require_enemy()
        if self._hero.weapon and self._hero.weapon.weapon_kind == "staff":
            spell = self.cast_fire()
            messages = self.resolve_fire(spell)
        else:
            messages = self._damage_enemy(self._hero.attack)
        if self._status == self.STATUS_PLAYING and self._current_room_model().enemy.is_alive:
            messages.extend(self.enemy_attack())
        return messages

    def melee_attack(self) -> List[str]:
        """Ataque de espada sin contraataque automático (interfaz en tiempo real)."""
        self._require_enemy()
        if self._hero.weapon is None or self._hero.weapon.weapon_kind != "sword":
            raise InvalidActionError("Recoge y equipa la espada desde el inventario.")
        return self._damage_enemy(self._hero.attack)

    def cast_fire(self) -> int:
        """Consume maná al lanzar y autoriza un único impacto posterior."""
        self._require_enemy()
        if self._hero.hero_class != "mage" or self._hero.weapon is None or self._hero.weapon.weapon_kind != "staff":
            raise InvalidActionError("Recoge y equipa el bastón para lanzar fuego.")
        self._hero.spend_mana(Hero.FIRE_COST)
        self._spell_id += 1
        self._pending_fire[self._spell_id] = (self._current_room_index, self._hero.attack)
        return self._spell_id

    def resolve_fire(self, spell_id: int) -> List[str]:
        if type(spell_id) is not int or spell_id not in self._pending_fire:
            raise InvalidActionError("Este hechizo ya se resolvió o no existe.")
        room_index, attack = self._pending_fire.pop(spell_id)
        if room_index != self._current_room_index:
            raise InvalidActionError("El hechizo pertenece a otra habitación.")
        self._require_enemy()
        return self._damage_enemy(attack)

    def cancel_fire(self, spell_id: int) -> None:
        """Un proyectil fallido consume el maná, pero nunca inflige daño."""
        self._pending_fire.pop(spell_id, None)

    def _require_enemy(self):
        self._require_playing()
        enemy = self._current_room_model().enemy
        if enemy is None:
            raise InvalidActionError("No hay un enemigo en esta habitación.")
        if not enemy.is_alive:
            raise InvalidActionError("El enemigo de esta habitación ya fue derrotado.")
        return enemy

    def _damage_enemy(self, attack: int) -> List[str]:
        enemy = self._require_enemy()
        room = self._current_room_model()
        messages = []
        damage = enemy.receive_damage(attack)
        messages.append(
            f"{self._hero.name} causa {damage} de daño a {enemy.name}."
        )

        if not enemy.is_alive:
            messages.append(f"Derrotaste a {enemy.name}.")
            if room.drop is not None:
                room.item, room.drop = room.drop, None
                messages.append(f"{enemy.name} dejó una {room.item.name.lower()}.")
            if self._hero.max_mana:
                self._hero.restore_mana()
                messages.append("El enemigo derrotado restaura tu maná a 100.")
            if enemy.is_boss and room.is_final:
                self._status = self.STATUS_VICTORY
                messages.append("¡Victoria! Derrotaste al guardián final.")
        return messages

    def enemy_attack(self) -> List[str]:
        """Daño independiente; la vista decide el contacto y su frecuencia."""
        enemy = self._require_enemy()
        damage = self._hero.receive_damage(enemy.attack)
        messages = [f"{enemy.name} causa {damage} de daño a {self._hero.name}."]
        if not self._hero.is_alive:
            self._status = self.STATUS_DEFEAT
            messages.append("Derrota. Tu héroe ha caído.")
        return messages

    def advance(self) -> List[str]:
        """Avanza a la siguiente habitación cuando el encuentro está resuelto."""
        self._require_playing()
        self._require_no_projectiles()
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
            data = self._migrate_state(data)
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
        self._pending_fire.clear()
        return ["Partida restaurada correctamente."]

    def save_game(self) -> List[str]:
        """Delega el guardado al administrador de datos recibido."""
        self._require_no_projectiles()
        save = self._require_data_manager_method("save")
        try:
            save(self.export_state())
        except PersistenceError as exc:
            raise ApplicationError(str(exc)) from exc
        return ["Partida guardada correctamente."]

    def load_game(self) -> List[str]:
        """Carga un estado y reconstruye los modelos de dominio."""
        self._require_no_projectiles()
        exists = self._require_data_manager_method("exists")
        load = self._require_data_manager_method("load")
        try:
            if not exists():
                raise InvalidActionError("No existe una partida guardada.")
            return self.restore_state(load())
        except PersistenceError as exc:
            raise ApplicationError(str(exc)) from exc

    @staticmethod
    def _build_rooms(hero_class="warrior") -> List[Room]:
        weapon = Item("Bastón de fuego" if hero_class == "mage" else "Espada", "weapon",
                      attack_bonus=3, weapon_kind="staff" if hero_class == "mage" else "sword")
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
                "Entrada de la cueva · los restos del caído",
                item=weapon,
            ),
            Room(
                1,
                "Gruta del Goblin",
                enemy=goblin,
                drop=armor,
            ),
            Room(
                2,
                "Profundidades · el guardián de los goblins",
                enemy=boss,
                is_final=True,
            ),
        ]

    def _require_no_projectiles(self):
        if self._pending_fire:
            raise InvalidActionError("Espera a que termine el proyectil de fuego.")

    @classmethod
    def _migrate_state(cls, data):
        """Migra partidas v1 sin volver a otorgar recompensas ya consumidas."""
        if not isinstance(data, dict):
            return data
        result = deepcopy(data)
        if type(result.get("version")) is not int or result["version"] != 1:
            return result
        hero = result.get("hero")
        if not isinstance(hero, dict) or not isinstance(result.get("rooms"), list):
            return result
        mage = hero.get("hero_class") == "mage"
        hero.setdefault("mana", 100 if mage else 0)
        hero.setdefault("max_mana", 100 if mage else 0)
        items = list(hero.get("inventory", [])) if isinstance(hero.get("inventory"), list) else []
        if hero.get("weapon") is not None:
            items.append(hero["weapon"])
        for room in result["rooms"]:
            if not isinstance(room, dict):
                continue
            item, enemy = room.get("item"), room.get("enemy")
            if isinstance(item, dict):
                items.append(item)
                if (item.get("item_type") == "armor" and isinstance(enemy, dict) and
                        isinstance(enemy.get("health"), int) and enemy["health"] > 0):
                    room["drop"], room["item"] = item, None
            room.setdefault("drop", None)
        for item in items:
            if isinstance(item, dict) and item.get("item_type") == "weapon":
                item.setdefault("weapon_kind", "staff" if mage else "sword")
                if mage and item.get("name") == "Espada":
                    item["name"] = "Bastón de fuego"
        result["version"] = cls.SAVE_VERSION
        return result

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
        drop_data = room_data.get("drop")
        if drop_data is not None and not isinstance(drop_data, dict):
            raise InvalidActionError("El botín guardado no es válido.")

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
        for room in rooms:
            if room.drop is not None and (room.enemy is None or not room.enemy.is_alive or room.item is not None):
                raise InvalidActionError("El botín pendiente no coincide con el enemigo guardado.")
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
