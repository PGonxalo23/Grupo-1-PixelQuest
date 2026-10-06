from typing import List, Optional, Dict, Any

from src.domain.exceptions import (
    ValidationError, InvalidNameError, InvalidStatError, InvalidItemError, InventoryError
)
from src.domain.validators import (
    validate_name, validate_positive_int, validate_non_negative_int,
    validate_item_type, validate_color
)


class Item:
    def __init__(self, name: str, item_type: str, attack_bonus: int = 0, defense_bonus: int = 0,
                 weapon_kind: Optional[str] = None):
        self._name = validate_name(name)
        self._item_type = validate_item_type(item_type)
        self._attack_bonus = validate_non_negative_int(attack_bonus, "attack_bonus")
        self._defense_bonus = validate_non_negative_int(defense_bonus, "defense_bonus")
        self._weapon_kind = weapon_kind
        if self._item_type == "weapon":
            self._weapon_kind = weapon_kind if weapon_kind is not None else "sword"
            if self._weapon_kind not in ("sword", "staff"):
                raise InvalidItemError("El arma debe ser una espada o un bastón.")
        elif weapon_kind is not None:
            raise InvalidItemError("Una armadura no puede tener un tipo de arma.")

        # Regla: Un arma no aporta defensa y una armadura no aporta ataque
        if self._item_type == "weapon":
            self._defense_bonus = 0
        elif self._item_type == "armor":
            self._attack_bonus = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def item_type(self) -> str:
        return self._item_type

    @property
    def attack_bonus(self) -> int:
        return self._attack_bonus

    @property
    def defense_bonus(self) -> int:
        return self._defense_bonus

    @property
    def weapon_kind(self) -> Optional[str]:
        return self._weapon_kind

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "item_type": self._item_type,
            "attack_bonus": self._attack_bonus,
            "defense_bonus": self._defense_bonus,
            "weapon_kind": self._weapon_kind,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        return cls(
            name=data["name"],
            item_type=data["item_type"],
            attack_bonus=data.get("attack_bonus", 0),
            defense_bonus=data.get("defense_bonus", 0),
            weapon_kind=data.get("weapon_kind"),
        )


class Character:
    def __init__(self, name: str, max_health: int, attack: int, defense: int):
        self._name = validate_name(name)
        self._max_health = validate_positive_int(max_health, "max_health")
        self._health = self._max_health
        self._base_attack = validate_positive_int(attack, "attack")
        self._base_defense = validate_positive_int(defense, "defense")

    @property
    def name(self) -> str:
        return self._name

    @property
    def max_health(self) -> int:
        return self._max_health

    @property
    def health(self) -> int:
        return self._health

    @property
    def attack(self) -> int:
        return self._base_attack

    @property
    def defense(self) -> int:
        return self._base_defense

    @property
    def is_alive(self) -> bool:
        return self._health > 0

    def receive_damage(self, raw_attack: int) -> int:
        effective_damage = max(1, raw_attack - self.defense)
        self._health = max(0, self._health - effective_damage)
        return effective_damage


class Hero(Character):
    DEFAULT_COLORS = {"warrior": "#59C9A5", "mage": "#A78BFA"}
    FIRE_COST = 15

    CLASS_STATS = {
        "warrior": {"max_health": 30, "attack": 7, "defense": 4},
        "mage": {"max_health": 22, "attack": 10, "defense": 2},
    }

    def __init__(self, name: str, hero_class: str, color: Optional[str] = None):
        normalized_class = str(hero_class).lower().strip()
        if normalized_class not in self.CLASS_STATS:
            raise ValidationError(f"Clase de héroe inválida: {hero_class}")

        stats = self.CLASS_STATS[normalized_class]
        super().__init__(name, stats["max_health"], stats["attack"], stats["defense"])

        self._hero_class = normalized_class
        self._color = validate_color(
            self.DEFAULT_COLORS[normalized_class] if color is None else color
        )
        self._inventory: List[Item] = []
        self._weapon: Optional[Item] = None
        self._armor: Optional[Item] = None
        self._max_mana = 100 if normalized_class == "mage" else 0
        self._mana = self._max_mana

    @property
    def hero_class(self) -> str:
        return self._hero_class

    @property
    def color(self) -> str:
        return self._color

    def change_color(self, color: str) -> None:
        self._color = validate_color(color)

    @property
    def mana(self) -> int:
        return self._mana

    @property
    def max_mana(self) -> int:
        return self._max_mana

    def spend_mana(self, amount: int) -> None:
        validate_positive_int(amount, "mana_cost")
        if amount > self._mana:
            raise ValidationError("Maná insuficiente: el hechizo de fuego requiere 15.")
        self._mana -= amount

    def restore_mana(self) -> None:
        self._mana = self._max_mana

    @property
    def inventory(self) -> List[Item]:
        return list(self._inventory)

    @property
    def weapon(self) -> Optional[Item]:
        return self._weapon

    @property
    def armor(self) -> Optional[Item]:
        return self._armor

    @property
    def attack(self) -> int:
        bonus = self._weapon.attack_bonus if self._weapon else 0
        return self._base_attack + bonus

    @property
    def defense(self) -> int:
        bonus = self._armor.defense_bonus if self._armor else 0
        return self._base_defense + bonus

    def add_item(self, item: Item) -> None:
        # Rechazar items con nombre duplicado en el inventario
        if any(existing.name == item.name for existing in self._inventory):
            raise InventoryError(f"El objeto '{item.name}' ya está en el inventario.")
        self._inventory.append(item)

    def equip_item(self, index: int) -> None:
        if index < 0 or index >= len(self._inventory):
            raise InventoryError("Índice de inventario inválido.")
        item = self._inventory[index]
        if item.item_type == "weapon":
            self._weapon = item
        elif item.item_type == "armor":
            self._armor = item

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "hero_class": self._hero_class,
            "color": self._color,
            "health": self._health,
            "max_health": self._max_health,
            "mana": self._mana,
            "max_mana": self._max_mana,
            "base_attack": self._base_attack,
            "base_defense": self._base_defense,
            "inventory": [item.to_dict() for item in self._inventory],
            "weapon": self._weapon.to_dict() if self._weapon else None,
            "armor": self._armor.to_dict() if self._armor else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Hero":
        hero = cls(data["name"], data["hero_class"], data.get("color"))
        hero._health = data.get("health", hero._max_health)
        mana = validate_non_negative_int(data.get("mana", hero.max_mana), "mana")
        max_mana = validate_non_negative_int(data.get("max_mana", hero.max_mana), "max_mana")
        if max_mana != hero.max_mana or mana > max_mana:
            raise ValidationError("El maná guardado no coincide con la clase del héroe.")
        hero._mana = mana
        hero._inventory = [Item.from_dict(i) for i in data.get("inventory", [])]
        if data.get("weapon"):
            hero._weapon = Item.from_dict(data["weapon"])
        if data.get("armor"):
            hero._armor = Item.from_dict(data["armor"])
        return hero


class Enemy(Character):
    def __init__(self, name: str, max_health: int, attack: int, defense: int, is_boss: bool = False):
        super().__init__(name, max_health, attack, defense)
        self._is_boss = is_boss

    @property
    def is_boss(self) -> bool:
        return self._is_boss

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self._name,
            "max_health": self._max_health,
            "health": self._health,
            "attack": self._base_attack,
            "defense": self._base_defense,
            "is_boss": self._is_boss
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Enemy":
        enemy = cls(
            name=data["name"],
            max_health=data["max_health"],
            attack=data["attack"],
            defense=data["defense"],
            is_boss=data.get("is_boss", False)
        )
        enemy._health = data.get("health", enemy._max_health)
        return enemy


class Room:
    def __init__(self, number: int, description: str, enemy: Optional[Enemy] = None,
                 item: Optional[Item] = None, is_final: bool = False, drop: Optional[Item] = None):
        self._number = validate_non_negative_int(number, "number")
        self._description = description
        self.enemy = enemy
        self.item = item
        self._is_final = is_final
        self.drop = drop

    @property
    def number(self) -> int:
        return self._number

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_final(self) -> bool:
        return self._is_final

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self._number,
            "description": self._description,
            "enemy": self.enemy.to_dict() if self.enemy else None,
            "item": self.item.to_dict() if self.item else None,
            "drop": self.drop.to_dict() if self.drop else None,
            "is_final": self._is_final
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        enemy = Enemy.from_dict(data["enemy"]) if data.get("enemy") else None
        item = Item.from_dict(data["item"]) if data.get("item") else None
        return cls(
            number=data["number"],
            description=data["description"],
            enemy=enemy,
            item=item,
            is_final=data.get("is_final", False),
            drop=Item.from_dict(data["drop"]) if data.get("drop") else None,
        )
