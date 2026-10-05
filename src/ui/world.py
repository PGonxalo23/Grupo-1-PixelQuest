"""Exploración de la vista 2D; no contiene reglas de daño o inventario.

Las coordenadas son locales a la sala y no dependen de la resolución de ventana.
Este módulo no necesita Pygame y se puede verificar sin una pantalla.
"""

import math


class ExplorationWorld:
    WIDTH = 864
    HEIGHT = 480
    TILE = 32
    RADIUS = 12
    SPEED = 220
    SPAWN = (96.0, 240.0)
    ENEMY = (576.0, 240.0)
    ITEM = (352.0, 240.0)
    EXIT = (816.0, 240.0)
    ATTACK_RANGE = 104
    INTERACT_RANGE = 76

    def __init__(self):
        self.room_index = 0
        self.position = self.SPAWN
        self.facing = "down"
        self.walking = False

    @property
    def obstacles(self):
        # Columnas de piedra; siempre existe un corredor central transitable.
        pillars = [(224, 96, 48, 64), (224, 336, 48, 64),
                   (672, 96, 48, 64), (672, 336, 48, 64)]
        if self.room_index == 1:
            pillars += [(416, 80, 64, 48), (416, 352, 64, 48)]
        return pillars

    def enter_room(self, room_index):
        self.room_index = room_index
        self.position = self.SPAWN
        self.facing = "right"
        self.walking = False

    def distance_to(self, target):
        return math.dist(self.position, target)

    def can_attack(self, snapshot):
        enemy = snapshot["room"].get("enemy")
        return bool(snapshot["status"] == "playing" and enemy and
                    enemy["health"] > 0 and
                    self.distance_to(self.ENEMY) <= self.ATTACK_RANGE)

    def context_action(self, snapshot):
        room = snapshot["room"]
        if self.can_attack(snapshot):
            return "attack"
        if room.get("item") and self.distance_to(self.ITEM) <= self.INTERACT_RANGE:
            return "collect"
        if self.distance_to(self.EXIT) <= self.INTERACT_RANGE:
            return "advance"
        return None

    def move(self, dx, dy, dt, enemy_alive=False):
        self.walking = bool(dx or dy)
        if not self.walking:
            return
        if abs(dx) >= abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"
        length = math.hypot(dx, dy)
        distance = self.SPEED * max(0, min(dt, 0.1))
        x, y = self.position
        candidate = (x + dx / length * distance, y)
        if self._valid_position(candidate, enemy_alive):
            x = candidate[0]
        candidate = (x, y + dy / length * distance)
        if self._valid_position(candidate, enemy_alive):
            y = candidate[1]
        self.position = (x, y)

    def _valid_position(self, position, enemy_alive=False):
        x, y = position
        r = self.RADIUS
        if not (32 + r <= x <= self.WIDTH - 32 - r and
                32 + r <= y <= self.HEIGHT - 32 - r):
            return False
        obstacles = list(self.obstacles)
        if enemy_alive:
            ex, ey = self.ENEMY
            obstacles.append((ex - 24, ey - 24, 48, 48))
        return not any(x + r > left and x - r < left + width and
                       y + r > top and y - r < top + height
                       for left, top, width, height in obstacles)

    def to_dict(self):
        return {"version": 1, "room_index": self.room_index,
                "position": list(self.position), "facing": self.facing}

    def restore(self, data, room_index, enemy_alive=False):
        """Si faltan metadatos visuales válidos, usa la entrada de la sala.

        Una vista dañada no invalida una partida cuyo dominio sí es válido.
        """
        self.enter_room(room_index)
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
            return False
        index = data.get("room_index")
        if isinstance(index, bool) or not isinstance(index, int) or index != room_index:
            return False
        position = data.get("position")
        if not isinstance(position, list) or len(position) != 2 or any(
            isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in position
        ):
            return False
        facing = data.get("facing")
        if facing not in ("up", "down", "left", "right"):
            return False
        if not self._valid_position(position, enemy_alive):
            return False
        self.position = tuple(position)
        self.facing = facing
        return True
