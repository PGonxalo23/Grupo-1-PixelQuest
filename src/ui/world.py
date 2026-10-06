"""Geometría, navegación y proyectiles comprobables sin Pygame.

El mundo determina contacto/alcance; GameService aplica daño, maná y recompensas.
"""

import math
from collections import deque
from dataclasses import dataclass


@dataclass
class FireProjectile:
    spell_id: int
    position: tuple
    velocity: tuple
    remaining: float = 420.0


class ExplorationWorld:
    WIDTH, HEIGHT, TILE = 864, 480, 32
    RADIUS, ENEMY_RADIUS = 12, 24
    SPEED, ENEMY_SPEED = 220, 105
    HERO_HEIGHT = 72  # Sprite normal de 18 píxeles, dibujado a escala 4.
    ATTACK_RANGE = HERO_HEIGHT * 2
    FIRE_RANGE, FIRE_SPEED = 420, 420
    CONTACT_RANGE, ENEMY_INTERVAL = 48, 1.15
    SWORD_INTERVAL, FIRE_INTERVAL = 0.55, 0.75
    SPAWN, ENEMY = (96.0, 240.0), (576.0, 240.0)
    ITEM, EXIT = (352.0, 240.0), (816.0, 240.0)
    INTERACT_RANGE = 76

    def __init__(self):
        self.enter_room(0)

    @property
    def obstacles(self):
        rocks = [(224, 96, 48, 64), (224, 336, 48, 64),
                 (672, 96, 48, 64), (672, 336, 48, 64)]
        if self.room_index == 1:
            rocks += [(416, 80, 64, 48), (416, 352, 64, 48)]
        return rocks

    @property
    def item_position(self):
        return self.ITEM if self.room_index == 0 else self.loot_position or self.enemy_position

    def enter_room(self, room_index):
        self.room_index = room_index
        self.position, self.enemy_position = self.SPAWN, self.ENEMY
        self.loot_position = None
        self.facing, self.walking = "right", False
        self.hero_cooldown, self.enemy_cooldown = 0.0, 1.0
        self.projectiles = []
        self._path, self._path_timer = [], 0.0
        self._nodes = {(x, y) for x in range(48, self.WIDTH - 32, 32)
                       for y in range(48, self.HEIGHT - 32, 32)
                       if self._static_valid((x, y), self.ENEMY_RADIUS)}

    def distance_to(self, target):
        return math.dist(self.position, target)

    def can_attack(self, snapshot):
        enemy, hero = snapshot["room"].get("enemy"), snapshot["hero"]
        if not (snapshot["status"] == "playing" and enemy and enemy["health"] > 0 and hero["weapon"]):
            return False
        reach = self.FIRE_RANGE if hero["hero_class"] == "mage" else self.ATTACK_RANGE
        return (self.distance_to(self.enemy_position) <= reach and
                self.line_clear(self.position, self.enemy_position, 4))

    def context_action(self, snapshot):
        if snapshot["room"].get("item") and self.distance_to(self.item_position) <= self.INTERACT_RANGE:
            return "collect"
        if self.distance_to(self.EXIT) <= self.INTERACT_RANGE:
            return "advance"
        if self.can_attack(snapshot):
            return "attack"
        return None

    def _static_valid(self, position, radius):
        x, y = position
        if not (32 + radius <= x <= self.WIDTH - 32 - radius and
                32 + radius <= y <= self.HEIGHT - 32 - radius):
            return False
        return not any(x + radius > left and x - radius < left + width and
                       y + radius > top and y - radius < top + height
                       for left, top, width, height in self.obstacles)

    def _valid_position(self, position, enemy_alive=False):
        return (self._static_valid(position, self.RADIUS) and
                (not enemy_alive or math.dist(position, self.enemy_position) >= self.RADIUS + self.ENEMY_RADIUS))

    def line_clear(self, start, end, radius=4):
        steps = max(1, math.ceil(math.dist(start, end) / 8))
        return all(self._static_valid((start[0] + (end[0] - start[0]) * i / steps,
                                       start[1] + (end[1] - start[1]) * i / steps), radius)
                   for i in range(steps + 1))

    def move(self, dx, dy, dt, enemy_alive=False):
        self.walking = bool(dx or dy)
        if not self.walking:
            return
        self.facing = ("right" if dx > 0 else "left") if abs(dx) >= abs(dy) else ("down" if dy > 0 else "up")
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

    def tick_cooldowns(self, dt):
        self.hero_cooldown = max(0.0, self.hero_cooldown - dt)
        self.enemy_cooldown = max(0.0, self.enemy_cooldown - dt)

    def _find_path(self):
        start = min(self._nodes, key=lambda p: (math.dist(p, self.enemy_position), p))
        goal = min(self._nodes, key=lambda p: (math.dist(p, self.position), p))
        queue, previous = deque([start]), {start: None}
        while queue:
            node = queue.popleft()
            if node == goal:
                break
            for dx, dy in ((32, 0), (-32, 0), (0, 32), (0, -32)):
                nxt = (node[0] + dx, node[1] + dy)
                if nxt in self._nodes and nxt not in previous:
                    previous[nxt] = node
                    queue.append(nxt)
        if goal not in previous:
            return []
        path, node = [], goal
        while node is not None:
            path.append(node)
            node = previous[node]
        return list(reversed(path))

    def update_enemy(self, dt, enemy_alive):
        """Persigue evitando rocas; devuelve True cuando corresponde un golpe."""
        if not enemy_alive:
            return False
        dt = max(0, min(dt, 0.1))
        distance = self.distance_to(self.enemy_position)
        if distance > self.RADIUS + self.ENEMY_RADIUS + 3:
            self._path_timer -= dt
            if self.line_clear(self.enemy_position, self.position, self.ENEMY_RADIUS):
                target = self.position
            else:
                if self._path_timer <= 0 or not self._path:
                    self._path, self._path_timer = self._find_path(), 0.4
                while self._path and math.dist(self.enemy_position, self._path[0]) < 5:
                    self._path.pop(0)
                target = self._path[0] if self._path else self.enemy_position
            ex, ey = self.enemy_position
            dx, dy = target[0] - ex, target[1] - ey
            length = math.hypot(dx, dy)
            if length:
                step = min(self.ENEMY_SPEED * dt, length)
                candidate = (ex + dx / length * step, ey + dy / length * step)
                if (self._static_valid(candidate, self.ENEMY_RADIUS) and
                        math.dist(candidate, self.position) >= self.RADIUS + self.ENEMY_RADIUS):
                    self.enemy_position = candidate
        if (self.distance_to(self.enemy_position) <= self.CONTACT_RANGE and
                self.enemy_cooldown <= 0 and self.line_clear(self.position, self.enemy_position, 4)):
            self.enemy_cooldown = self.ENEMY_INTERVAL
            return True
        return False

    def launch_fire(self, spell_id):
        dx, dy = self.enemy_position[0] - self.position[0], self.enemy_position[1] - self.position[1]
        length = math.hypot(dx, dy) or 1
        self.projectiles.append(FireProjectile(spell_id, self.position,
                                               (dx / length * self.FIRE_SPEED, dy / length * self.FIRE_SPEED)))
        self.hero_cooldown = self.FIRE_INTERVAL

    def update_projectiles(self, dt, enemy_alive):
        dt = max(0, min(dt, 0.1))
        hits, misses, survivors = [], [], []
        for projectile in self.projectiles:
            distance = self.FIRE_SPEED * max(0, min(dt, 0.1))
            steps = max(1, math.ceil(distance / 6))
            hit, ended = False, False
            for _ in range(steps):
                x, y = projectile.position
                projectile.position = (x + projectile.velocity[0] * dt / steps,
                                       y + projectile.velocity[1] * dt / steps)
                projectile.remaining -= distance / steps
                if not self._static_valid(projectile.position, 5) or projectile.remaining <= 0:
                    ended = True
                    break
                if enemy_alive and math.dist(projectile.position, self.enemy_position) <= self.ENEMY_RADIUS + 7:
                    hit, ended = True, True
                    break
            if ended:
                (hits if hit else misses).append(projectile.spell_id)
            else:
                survivors.append(projectile)
        self.projectiles = survivors
        return hits, misses

    def mark_enemy_defeated(self):
        self.loot_position = self.enemy_position

    def to_dict(self):
        return {"version": 2, "room_index": self.room_index,
                "position": list(self.position), "facing": self.facing,
                "enemy_position": list(self.enemy_position),
                "loot_position": list(self.loot_position) if self.loot_position else None,
                "hero_cooldown": self.hero_cooldown, "enemy_cooldown": self.enemy_cooldown}

    @staticmethod
    def _coordinates(value):
        return (isinstance(value, list) and len(value) == 2 and
                all(type(v) in (int, float) and math.isfinite(v) for v in value))

    def restore(self, data, room_index, enemy_alive=False):
        self.enter_room(room_index)
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] not in (1, 2):
            return False
        if type(data.get("room_index")) is not int or data["room_index"] != room_index:
            return False
        position, facing = data.get("position"), data.get("facing")
        enemy = data.get("enemy_position", list(self.ENEMY))
        loot = data.get("loot_position")
        if not self._coordinates(enemy) or not self._static_valid(enemy, self.ENEMY_RADIUS):
            return False
        if not self._coordinates(position) or not self._static_valid(position, self.RADIUS):
            return False
        if facing not in ("up", "down", "left", "right"):
            return False
        if enemy_alive and math.dist(position, enemy) < self.RADIUS + self.ENEMY_RADIUS:
            return False
        if loot is not None and (not self._coordinates(loot) or not self._static_valid(loot, 5)):
            return False
        cooldowns = (data.get("hero_cooldown", 0.0), data.get("enemy_cooldown", 1.0))
        if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 2 for v in cooldowns):
            return False
        self.position, self.enemy_position, self.facing = tuple(position), tuple(enemy), facing
        self.loot_position = tuple(loot) if loot is not None else None
        self.hero_cooldown, self.enemy_cooldown = cooldowns
        return True
