"""RPG 2D de exploración con combate por turnos, conectado a GameService."""

import math
from collections import deque
from dataclasses import dataclass

import pygame

from src.domain.exceptions import DomainError
from src.services.app_service import ApplicationError
from src.ui import pixel_art as art


@dataclass
class Button:
    rect: pygame.Rect
    action: str
    enabled: bool = True


class GraphicalGame:
    WIDTH, HEIGHT = 1280, 800
    MAP_ORIGIN = (32, 140)
    TURN_DURATION = 0.85

    def __init__(self, service, world, visual_data_manager, window_size=(1152, 720)):
        pygame.display.init()
        pygame.font.init()
        pygame.display.set_caption("Pixel Quest · RPG 2D")
        self.window = pygame.display.set_mode(window_size, pygame.RESIZABLE)
        self.canvas = pygame.Surface((self.WIDTH, self.HEIGHT))
        self.service = service
        self.world = world
        self.data_manager = visual_data_manager
        self.screen = "menu"
        self.running = True
        self.time = 0.0
        self.turn_remaining = 0.0
        self.combat = None
        self.buttons = []
        self.fonts = {}
        self.messages = deque(maxlen=30)
        self.notification = ""
        self.notification_remaining = 0.0
        self.name = ""
        self.hero_class = "warrior"
        self.class_stats = self.service.get_hero_classes()
        self.selected_color = "#59C9A5"
        self.name_focused = True
        self.render()

    def run(self, frame_limit=None):
        clock = pygame.time.Clock()
        frames = 0
        try:
            while self.running:
                dt = min(clock.tick(60) / 1000, 0.05)
                for event in pygame.event.get():
                    self.process_event(event)
                self.update(dt)
                self.render()
                self.present()
                frames += 1
                if frame_limit is not None and frames >= frame_limit:
                    break
        finally:
            pygame.quit()

    def _viewport(self):
        width, height = self.window.get_size()
        scale = min(width / self.WIDTH, height / self.HEIGHT)
        size = (max(1, round(self.WIDTH * scale)), max(1, round(self.HEIGHT * scale)))
        return scale, size, ((width - size[0]) // 2, (height - size[1]) // 2)

    def logical_mouse(self, position=None):
        scale, _, (left, top) = self._viewport()
        x, y = position if position is not None else pygame.mouse.get_pos()
        return ((x - left) / scale, (y - top) / scale)

    def present(self):
        _, size, offset = self._viewport()
        self.window.fill(art.BG)
        self.window.blit(pygame.transform.scale(self.canvas, size), offset)
        pygame.display.flip()

    def _font(self, size, heading=False):
        key = (size, heading)
        if key not in self.fonts:
            self.fonts[key] = pygame.font.SysFont("segoeui" if heading else "consolas",
                                                size, bold=heading)
        return self.fonts[key]

    def text(self, value, position, size=18, color=art.TEXT, heading=False,
             center=False, max_width=None):
        font = self._font(size, heading)
        value = str(value)
        if max_width is not None and font.size(value)[0] > max_width:
            while value and font.size(value + "…")[0] > max_width:
                value = value[:-1]
            value += "…"
        image = font.render(value, True, color)
        rect = image.get_rect(center=position) if center else image.get_rect(topleft=position)
        self.canvas.blit(image, rect)
        return rect

    def wrapped(self, value, position, width, size=17, color=art.MUTED, max_lines=4):
        font = self._font(size)
        line, lines = "", []
        for word in value.split():
            candidate = (line + " " + word).strip()
            if font.size(candidate)[0] > width and line:
                lines.append(line)
                line = word
            else:
                line = candidate
        if line:
            lines.append(line)
        for index, line in enumerate(lines[:max_lines]):
            self.text(line, (position[0], position[1] + index * (size + 7)), size, color,
                      max_width=width)
        return min(len(lines), max_lines) * (size + 7)

    def panel(self, rect, color=art.PANEL, border=art.BORDER):
        pygame.draw.rect(self.canvas, color, rect, border_radius=12)
        pygame.draw.rect(self.canvas, border, rect, 1, border_radius=12)

    def button(self, label, rect, action, enabled=True, primary=False, selected=False):
        rect = pygame.Rect(rect)
        hovered = rect.collidepoint(self.logical_mouse()) and enabled
        fill = (34, 53, 63) if selected else (25, 39, 54)
        if primary:
            fill = art.MINT if enabled else (35, 52, 56)
        if hovered:
            fill = art.tint(fill, 1.15)
        pygame.draw.rect(self.canvas, fill, rect, border_radius=7)
        pygame.draw.rect(self.canvas, art.MINT if selected or hovered else art.BORDER,
                         rect, 1, border_radius=7)
        color = art.BG if primary and enabled else art.TEXT if enabled else (92, 111, 124)
        self.text(label, rect.center, 18, color, center=True, max_width=rect.w - 18)
        self.buttons.append(Button(rect, action, enabled))

    def notify(self, message):
        self.notification = str(message)
        self.notification_remaining = 4.0

    def record(self, messages):
        self.messages.extend(messages)

    def process_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.VIDEORESIZE:
            self.window = pygame.display.set_mode((max(640, event.w), max(400, event.h)),
                                                  pygame.RESIZABLE)
            return
        if event.type == pygame.WINDOWFOCUSLOST and self.screen == "playing":
            self.screen = "pause"
            return
        if event.type == pygame.TEXTINPUT and self.screen == "create" and self.name_focused:
            self.name = (self.name + "".join(c for c in event.text if c.isprintable()))[:24]
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse = self.logical_mouse(event.pos)
            if self.screen == "create":
                self.name_focused = pygame.Rect(174, 251, 510, 56).collidepoint(mouse)
            for button in reversed(self.buttons):
                if button.enabled and button.rect.collidepoint(mouse):
                    self.handle_action(button.action)
                    break
            # Una segunda entrada en el mismo frame no puede activar botones de otra pantalla.
            self.render()
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event.key)

    def _handle_key(self, key):
        if self.screen == "create":
            if key == pygame.K_BACKSPACE and self.name_focused:
                self.name = self.name[:-1]
            elif key == pygame.K_RETURN:
                self.handle_action("start")
            elif key == pygame.K_ESCAPE:
                self.handle_action("menu")
            return
        if key == pygame.K_ESCAPE:
            if self.screen == "playing":
                self.screen = "pause"
            elif self.screen in ("pause", "inventory", "appearance"):
                self.handle_action("resume")
            elif self.screen == "ending":
                self.handle_action("menu")
            return
        if self.screen == "inventory":
            if key == pygame.K_i:
                self.handle_action("resume")
            elif pygame.K_1 <= key <= pygame.K_9:
                self.handle_action(f"equip:{key - pygame.K_1}")
            return
        if self.screen != "playing":
            return
        action = {pygame.K_e: "interact", pygame.K_SPACE: "attack",
                  pygame.K_i: "inventory", pygame.K_c: "appearance",
                  pygame.K_F5: "save", pygame.K_F9: "load"}.get(key)
        if action:
            self.handle_action(action)

    def handle_action(self, action):
        try:
            self._execute_action(action)
        except (DomainError, ApplicationError) as exc:
            self.notify(str(exc))

    def _execute_action(self, action):
        if action == "quit":
            self.running = False
        elif action == "create":
            self.screen = "create"
            self.name = ""
            self.hero_class = "warrior"
            self.selected_color = "#59C9A5"
            self.name_focused = True
            pygame.key.start_text_input()
        elif action == "menu":
            self.screen = "menu"
            pygame.key.stop_text_input()
        elif action.startswith("class:"):
            self.hero_class = action.split(":")[1]
        elif action.startswith("color:"):
            self.selected_color = action.split(":")[1]
        elif action == "start":
            self.start_game()
        elif action == "load":
            if self.turn_remaining > 0:
                self.notify("Espera a que termine la animación del turno.")
                return
            messages = self.service.load_game()
            self.data_manager.restore_view(self.service.get_snapshot())
            self.turn_remaining, self.combat = 0.0, None
            self.messages.clear()
            self.record(messages)
            self.screen = "playing" if self.service.status == "playing" else "ending"
            self.notify(messages[-1])
        elif action == "resume":
            self.screen = "playing" if self.service.status == "playing" or self.turn_remaining > 0 else "ending"
        elif action == "pause":
            self.screen = "pause"
        elif action == "save":
            if self.turn_remaining > 0:
                self.notify("Espera a que termine la animación del turno.")
                return
            messages = self.service.save_game()
            self.record(messages)
            self.notify(messages[-1])
        elif action in ("inventory", "appearance"):
            if self.turn_remaining > 0:
                return
            self.screen = action
            self.selected_color = self.service.get_snapshot()["hero"]["color"]
        elif action == "apply_color":
            messages = self.service.change_hero_color(self.selected_color)
            self.record(messages)
            self.screen = "playing" if self.service.status == "playing" else "ending"
            self.notify(messages[-1])
        elif action.startswith("equip:"):
            self.record(self.service.equip_item(int(action.split(":")[1])))
            self.notify("Objeto equipado. Tus estadísticas se actualizaron.")
        elif action in ("attack", "interact"):
            if self.turn_remaining > 0 or self.service.status != "playing":
                return
            snapshot = self.service.get_snapshot()
            if action == "interact":
                action = self.world.context_action(snapshot)
            if action == "attack":
                self.attack()
            elif action == "collect":
                self.record(self.service.collect_item())
                self.notify("Objeto recogido. Pulsa I para equiparlo.")
            elif action == "advance":
                self.record(self.service.advance())
                self.world.enter_room(self.service.get_snapshot()["current_room_index"])
            else:
                self.notify("Acércate a un objeto, enemigo o puerta y pulsa E.")

    def start_game(self):
        messages = self.service.start_new_game(self.name, self.hero_class, self.selected_color)
        self.world.enter_room(0)
        self.messages.clear()
        self.record(messages)
        self.combat, self.turn_remaining = None, 0.0
        self.screen = "playing"
        pygame.key.stop_text_input()
        self.notify("Recoge la espada con E y equípala con I antes de avanzar.")

    def attack(self):
        before = self.service.get_snapshot()
        if not self.world.can_attack(before):
            self.notify("Acércate al enemigo para atacar. Usa WASD o las flechas.")
            return
        self.record(self.service.attack())
        after = self.service.get_snapshot()
        self.combat = {"before": before, "after": after,
                       "enemy_damage": before["room"]["enemy"]["health"] - after["room"]["enemy"]["health"],
                       "hero_damage": before["hero"]["health"] - after["hero"]["health"]}
        self.turn_remaining = self.TURN_DURATION

    def update(self, dt, movement=None):
        self.time += dt
        self.notification_remaining = max(0, self.notification_remaining - dt)
        if self.screen != "playing":
            return
        self.turn_remaining = max(0, self.turn_remaining - dt)
        if self.turn_remaining == 0:
            self.combat = None
            if self.service.status in ("victory", "defeat"):
                self.screen = "ending"
                return
        if self.turn_remaining > 0:
            self.world.walking = False
            return
        if movement is None:
            keys = pygame.key.get_pressed()
            movement = (int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) -
                        int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
                        int(keys[pygame.K_s] or keys[pygame.K_DOWN]) -
                        int(keys[pygame.K_w] or keys[pygame.K_UP]))
        enemy = self.service.get_snapshot()["room"].get("enemy")
        self.world.move(*movement, dt, enemy_alive=bool(enemy and enemy["health"] > 0))

    def render(self):
        self.canvas.fill(art.BG)
        self.buttons = []
        if self.screen == "menu":
            self._draw_menu()
        elif self.screen == "create":
            self._draw_creation()
        else:
            self._draw_game()
            if self.screen in ("pause", "inventory", "appearance", "ending"):
                shade = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
                shade.fill((6, 12, 21, 205))
                self.canvas.blit(shade, (0, 0))
                self.buttons = []
                {"pause": self._draw_pause, "inventory": self._draw_inventory,
                 "appearance": self._draw_appearance, "ending": self._draw_ending}[self.screen]()
        if self.notification_remaining > 0:
            self.panel((180, 738, 920, 43), border=art.GOLD)
            self.text(self.notification, (640, 759), 17, art.GOLD,
                      center=True, max_width=888)

    def _draw_menu(self):
        pygame.draw.rect(self.canvas, (14, 24, 35), (720, 0, 560, 800))
        self.text("GRUPO 1 / CONSTRUCCIÓN DE SOFTWARE", (86, 87), 17, art.MINT)
        self.text("PIXEL", (80, 156), 87, heading=True)
        self.text("QUEST", (80, 244), 87, art.MINT, heading=True)
        self.wrapped("Una mazmorra. Dos caminos. Tu propia aventura.",
                     (88, 363), 490, 23, art.MUTED)
        self.button("Nueva aventura     →", (88, 457, 442, 58), "create", primary=True)
        self.button("Cargar partida", (88, 529, 214, 50), "load")
        self.button("Continuar", (316, 529, 214, 50), "resume",
                    enabled=self.service.status != "not_started")
        self.button("Salir", (88, 594, 442, 46), "quit")
        self.text("EXPLORA · EQUIPA · COMBATE POR TURNOS", (88, 700), 16, art.MUTED)
        preview = pygame.transform.scale(art.room_background(2), (470, 262))
        self.canvas.blit(preview, (755, 314))
        art.draw_actor(self.canvas, art.hero_sprite("warrior", "#59C9A5", equipped=True, scale=7),
                       (870, 504), math.sin(self.time * 2) * 3)
        art.draw_actor(self.canvas, art.enemy_sprite(True), (1110, 498), math.sin(self.time * 2 + 1) * 3)
        self.text("EL GUARDIÁN TE ESPERA", (986, 624), 20, art.GOLD, center=True)
        self.text("2D / PIXEL ART / PARTIDA LOCAL", (986, 662), 15, art.MUTED, center=True)

    def _draw_creation(self):
        self.text("01 / CREA TU HÉROE", (132, 82), 18, art.MINT)
        self.text("Toda aventura tiene un nombre.", (132, 124), 38, heading=True)
        self.panel((132, 209, 596, 478))
        self.text("NOMBRE", (174, 225), 15, art.MUTED)
        self.panel((174, 251, 510, 56), color=(11, 20, 31),
                   border=art.MINT if self.name_focused else art.BORDER)
        displayed_name = self.name + ("│" if self.name_focused and int(self.time * 2) % 2 == 0 else "")
        self.text(displayed_name or "Escribe el nombre de tu héroe", (190, 265), 23,
                  art.TEXT if self.name else art.MUTED, max_width=478)
        self.text("CLASE", (174, 335), 15, art.MUTED)
        self.button("Guerrero", (174, 365, 248, 56), "class:warrior", selected=self.hero_class == "warrior")
        self.button("Mago", (436, 365, 248, 56), "class:mage", selected=self.hero_class == "mage")
        self.text("COLOR DEL PERSONAJE", (174, 451), 15, art.MUTED)
        self._draw_color_choices(174, 483)
        self.button("Comenzar aventura  →", (174, 585, 510, 58), "start", primary=True)
        self.button("← Volver", (132, 709, 180, 42), "menu")
        self.panel((758, 209, 390, 478))
        pygame.draw.ellipse(self.canvas, (9, 16, 24), (838, 483, 230, 42))
        sprite = art.hero_sprite(self.hero_class, self.selected_color, equipped=True, scale=10)
        art.draw_actor(self.canvas, sprite, (953, 505), math.sin(self.time * 3) * 4)
        self.text("GUERRERO" if self.hero_class == "warrior" else "MAGO",
                  (953, 556), 27, heading=True, center=True)
        stats = self.class_stats[self.hero_class]
        self.text(f"VIDA {stats['max_health']}   ATQ {stats['attack']}   DEF {stats['defense']}", (953, 609), 18,
                  art.MINT, center=True)
        self.text("Tu color no altera las estadísticas.", (953, 650), 14, art.MUTED, center=True)

    def _draw_color_choices(self, x, y):
        for index, (name, color) in enumerate(art.COLORS):
            rect = pygame.Rect(x + index * 84, y, 68, 54)
            selected = color == self.selected_color
            pygame.draw.rect(self.canvas, pygame.Color(color), rect, border_radius=6)
            if selected:
                pygame.draw.rect(self.canvas, art.TEXT, rect.inflate(8, 8), 2, border_radius=8)
                cx, cy = rect.center
                pygame.draw.lines(self.canvas, art.BG, False,
                                  [(cx - 9, cy), (cx - 2, cy + 7), (cx + 11, cy - 9)], 3)
            self.buttons.append(Button(rect, f"color:{color}"))
            self.text(name, (rect.centerx, rect.bottom + 15), 13, art.MUTED, center=True)

    def _health_bar(self, x, y, width, health, maximum, color=art.MINT, height=9):
        pygame.draw.rect(self.canvas, (29, 39, 51), (x, y, width, height), border_radius=4)
        amount = round(width * max(0, min(1, health / maximum)))
        if amount:
            pygame.draw.rect(self.canvas, color, (x, y, amount, height), border_radius=4)

    def _draw_game(self):
        snapshot = self.service.get_snapshot()
        hero, room = snapshot["hero"], snapshot["room"]
        self.text("PIXEL QUEST", (32, 21), 27, heading=True)
        self.text("LA MAZMORRA DEL GUARDIÁN", (33, 61), 15, art.MUTED)
        for index in range(snapshot["total_rooms"]):
            x = 506 + index * 83
            current = index == snapshot["current_room_index"]
            pygame.draw.circle(self.canvas, art.MINT if current else art.BORDER, (x, 51), 16)
            self.text(str(index + 1), (x, 51), 17, art.BG if current else art.TEXT, center=True)
            if index < snapshot["total_rooms"] - 1:
                pygame.draw.line(self.canvas, art.BORDER, (x + 23, 51), (x + 60, 51), 2)
        self.button("Guardar [F5]", (835, 27, 176, 44), "save", enabled=self.turn_remaining == 0)
        self.button("Pausa [Esc]", (1027, 27, 221, 44), "pause")
        self.text(f"{snapshot['current_room_index'] + 1:02} / {room['description']}",
                  (32, 104), 18, art.GOLD)
        self._draw_world(snapshot)
        self._draw_sidebar(snapshot)
        self.panel((32, 640, 864, 116))
        self.text("BITÁCORA DE LA AVENTURA", (50, 652), 13, art.MINT)
        for index, message in enumerate(list(self.messages)[-3:]):
            self.text(message, (50, 680 + index * 23), 16, art.TEXT, max_width=822)
        self.text("WASD / ↑↓←→ Mover   E Interactuar   ESPACIO Atacar   I Inventario   C Color",
                  (32, 775), 14, art.MUTED)

    def _draw_world(self, snapshot):
        world, room, hero = self.world, snapshot["room"], snapshot["hero"]
        image = art.room_background(world.room_index).copy()
        art.draw_torches(image, self.time)
        ox, oy = self.MAP_ORIGIN
        enemy = room.get("enemy")
        enemy_alive = bool(enemy and enemy["health"] > 0)
        unlocked = not enemy_alive
        door = pygame.Rect(792, 194, 49, 92)
        pygame.draw.rect(image, (14, 21, 31), door)
        pygame.draw.rect(image, art.MINT if unlocked else art.RED, door, 3)
        if not unlocked:
            for x in range(door.x + 8, door.right - 2, 10):
                pygame.draw.line(image, (125, 119, 126), (x, door.y + 3), (x, door.bottom - 3), 3)
        else:
            pygame.draw.polygon(image, art.MINT, [(810, 224), (823, 240), (810, 256)])
        self.canvas.blit(image, self.MAP_ORIGIN)
        elapsed = self.TURN_DURATION - self.turn_remaining if self.combat else 0
        visual = snapshot
        if self.combat and elapsed < 0.23:
            visual = self.combat["before"]
        v_enemy = visual["room"].get("enemy")
        hero_position = (ox + world.position[0], oy + world.position[1])
        enemy_position = (ox + world.ENEMY[0], oy + world.ENEMY[1])
        if room.get("item"):
            ix, iy = world.ITEM
            pygame.draw.ellipse(self.canvas, (22, 29, 38), (ox + ix - 24, oy + iy - 3, 48, 14))
            sprite = art.item_sprite(room["item"]["item_type"])
            self.canvas.blit(sprite, sprite.get_rect(midbottom=(ox + ix, oy + iy - 7 + math.sin(self.time * 3) * 4)))
            self.text(room["item"]["name"], (ox + ix, oy + iy + 28), 15, art.GOLD, center=True)
        if enemy:
            art.draw_actor(self.canvas, art.enemy_sprite(enemy["is_boss"]), enemy_position,
                           math.sin(self.time * 3) * 2,
                           flash=bool(self.combat and 0.23 <= elapsed <= 0.4),
                           dead=v_enemy["health"] == 0)
            self.text(enemy["name"], (enemy_position[0], enemy_position[1] - 123),
                      16, art.RED if enemy_alive else art.MUTED, center=True)
            self._health_bar(enemy_position[0] - 47, enemy_position[1] - 98, 94,
                             v_enemy["health"], v_enemy["max_health"], art.RED, 7)
        sprite = art.hero_sprite(hero["hero_class"], hero["color"], world.facing,
                                 bool(hero.get("weapon")), bool(hero.get("armor")))
        bob = math.sin(self.time * (16 if world.walking else 3)) * (3 if world.walking else 1)
        direction = 1 if enemy_position[0] >= hero_position[0] else -1
        lunge = direction * math.sin(min(1, elapsed / 0.4) * math.pi) * 18 if self.combat else 0
        art.draw_actor(self.canvas, sprite, (hero_position[0] + lunge, hero_position[1]), bob,
                       flash=bool(self.combat and self.combat["hero_damage"] and 0.5 < elapsed < 0.68),
                       dead=bool(hero["health"] == 0 and self.turn_remaining == 0))
        self.text(hero["name"], (hero_position[0], hero_position[1] - 88), 14,
                  art.TEXT, center=True, max_width=165)
        if self.combat:
            self._draw_combat_effects(hero_position, enemy_position, elapsed, hero["hero_class"])
        if snapshot["status"] == "playing" and not self.combat:
            action = world.context_action(snapshot)
            prompts = {"attack": "ESPACIO / E · Atacar", "collect": "E · Recoger objeto",
                       "advance": "E · Salir" if unlocked else "Puerta bloqueada: derrota al enemigo"}
            prompt = prompts.get(action, "Explora la sala con WASD o las flechas")
            self.panel((219, 582, 490, 30), color=(14, 22, 33))
            self.text(prompt, (464, 597), 14, art.GOLD if action else art.MUTED,
                      center=True, max_width=470)
        pygame.draw.rect(self.canvas, art.BORDER, (ox, oy, world.WIDTH, world.HEIGHT), 2)

    def _draw_combat_effects(self, hero_position, enemy_position, elapsed, hero_class):
        if elapsed < 0.4:
            t = min(1, elapsed / 0.24)
            if hero_class == "mage":
                x = hero_position[0] + (enemy_position[0] - hero_position[0]) * t
                y = hero_position[1] - 38 + (enemy_position[1] - hero_position[1]) * t
                pygame.draw.circle(self.canvas, (61, 127, 134), (int(x), int(y)), 15)
                pygame.draw.circle(self.canvas, art.MINT, (int(x), int(y)), 9)
                pygame.draw.circle(self.canvas, art.TEXT, (int(x), int(y)), 4)
            else:
                rect = pygame.Rect(enemy_position[0] - 43, enemy_position[1] - 76, 80, 68)
                pygame.draw.arc(self.canvas, art.GOLD, rect, -0.6, 1.9, 7)
        if elapsed >= 0.23:
            self.text(f"−{self.combat['enemy_damage']}",
                      (enemy_position[0], enemy_position[1] - 142 - (elapsed - 0.23) * 30),
                      28, art.GOLD, heading=True, center=True)
        if elapsed >= 0.48 and self.combat["hero_damage"]:
            self.text(f"−{self.combat['hero_damage']}",
                      (hero_position[0], hero_position[1] - 108 - (elapsed - 0.48) * 30),
                      26, art.RED, heading=True, center=True)
        self.text("TU ATAQUE" if elapsed < 0.45 else "RESPUESTA ENEMIGA" if self.combat["hero_damage"] else "ENEMIGO DERROTADO",
                  (464, 170), 16, art.GOLD, center=True)

    def _draw_sidebar(self, snapshot):
        hero, room = snapshot["hero"], snapshot["room"]
        self.panel((920, 140, 328, 616))
        self.text("TU HÉROE", (942, 159), 14, art.MINT)
        self.text(hero["name"], (942, 187), 26, heading=True, max_width=282)
        self.text("GUERRERO" if hero["hero_class"] == "warrior" else "MAGO", (943, 225), 14, art.MUTED)
        self.text(f"VIDA  {hero['health']} / {hero['max_health']}", (943, 263), 17)
        self._health_bar(943, 292, 280, hero["health"], hero["max_health"])
        attack = hero["base_attack"] + (hero["weapon"]["attack_bonus"] if hero["weapon"] else 0)
        defense = hero["base_defense"] + (hero["armor"]["defense_bonus"] if hero["armor"] else 0)
        self.text(f"ATQ {attack:02}        DEF {defense:02}", (943, 321), 21, art.GOLD)
        pygame.draw.line(self.canvas, art.BORDER, (943, 360), (1226, 360))
        self.text("EQUIPAMIENTO", (943, 380), 14, art.MUTED)
        self.text("Arma: " + (hero["weapon"]["name"] if hero["weapon"] else "Sin equipar"),
                  (943, 409), 16, max_width=280)
        self.text("Armadura: " + (hero["armor"]["name"] if hero["armor"] else "Sin equipar"),
                  (943, 438), 16, max_width=280)
        self.button("Inventario [I]", (943, 478, 280, 43), "inventory", enabled=self.turn_remaining == 0)
        self.button("Cambiar color [C]", (943, 533, 280, 43), "appearance", enabled=self.turn_remaining == 0)
        can_attack = self.world.can_attack(snapshot) and self.turn_remaining == 0
        self.button("Atacar [ESPACIO]", (943, 588, 280, 48), "attack", enabled=can_attack, primary=True)
        enemy = room.get("enemy")
        goal = ("Derrota al guardián final." if room["is_final"] else "Derrota al Goblin y recoge la armadura.") if enemy and enemy["health"] > 0 else "Recoge y equipa el objeto; luego busca la puerta."
        if snapshot["status"] != "playing":
            goal = "Aventura completada." if snapshot["status"] == "victory" else "Tu héroe ha caído."
        self.text("OBJETIVO", (943, 660), 13, art.MINT)
        self.wrapped(goal, (943, 685), 276, 15, max_lines=2)

    def _draw_pause(self):
        self.panel((414, 178, 452, 456))
        self.text("UN RESPIRO", (640, 225), 32, heading=True, center=True)
        self.text("La aventura te espera.", (640, 270), 18, art.MUTED, center=True)
        self.button("Continuar", (458, 318, 364, 50), "resume", primary=True)
        self.button("Guardar partida", (458, 382, 364, 48), "save", enabled=self.turn_remaining == 0)
        self.button("Cargar último guardado", (458, 444, 364, 48), "load", enabled=self.turn_remaining == 0)
        self.button("Menú principal", (458, 506, 364, 48), "menu", enabled=self.turn_remaining == 0)
        self.text("F5 guarda · F9 carga · Esc continúa", (640, 593), 14, art.MUTED, center=True)

    def _draw_inventory(self):
        hero = self.service.get_snapshot()["hero"]
        self.panel((260, 156, 760, 482))
        self.text("TU INVENTARIO", (296, 190), 31, heading=True)
        self.text("Equipar reemplaza el objeto del mismo tipo; los bonos no se acumulan.",
                  (296, 245), 15, art.MUTED, max_width=688)
        if not hero["inventory"]:
            self.text("Aún no tienes objetos. Explora y recoge la espada con E.", (640, 390),
                      19, art.MUTED, center=True)
        for index, item in enumerate(hero["inventory"]):
            y = 290 + index * 102
            self.panel((296, y, 688, 88), color=(13, 23, 35))
            self.canvas.blit(art.item_sprite(item["item_type"]), (315, y + 19))
            self.text(item["name"], (387, y + 17), 22, heading=True)
            bonus = f"+{item['attack_bonus']} ataque" if item["item_type"] == "weapon" else f"+{item['defense_bonus']} defensa"
            self.text(bonus, (387, y + 52), 16, art.MINT)
            equipped = hero.get("weapon" if item["item_type"] == "weapon" else "armor") == item
            self.button("Equipado" if equipped else f"Equipar [{index + 1}]",
                        (782, y + 20, 180, 47), f"equip:{index}",
                        enabled=not equipped and self.service.status == "playing", selected=equipped)
        self.button("Volver [I / Esc]", (744, 562, 240, 46), "resume")

    def _draw_appearance(self):
        hero = self.service.get_snapshot()["hero"]
        self.panel((260, 167, 760, 470))
        self.text("DALE TU COLOR", (640, 212), 32, heading=True, center=True)
        self.text("La apariencia es tuya. La fuerza la decide tu equipo.",
                  (640, 260), 17, art.MUTED, center=True)
        art.draw_actor(self.canvas, art.hero_sprite(hero["hero_class"], self.selected_color,
                       equipped=bool(hero["weapon"]), armor=bool(hero["armor"]), scale=6),
                       (640, 411), math.sin(self.time * 3) * 3)
        self._draw_color_choices(396, 446)
        self.button("Cancelar", (396, 552, 230, 48), "resume")
        self.button("Aplicar color", (646, 552, 238, 48), "apply_color", primary=True)

    def _draw_ending(self):
        victory = self.service.status == "victory"
        self.panel((328, 177, 624, 456), border=art.MINT if victory else art.RED)
        self.text("MAZMORRA COMPLETADA" if victory else "EL HÉROE HA CAÍDO",
                  (640, 219), 16, art.MINT if victory else art.RED, center=True)
        self.text("¡VICTORIA!" if victory else "DERROTA", (640, 285), 58,
                  art.MINT if victory else art.RED, heading=True, center=True)
        self.text("Venciste al guardián. Tu historia acaba de comenzar." if victory else
                  "Cada aventura enseña algo. Equipa tus objetos y vuelve a intentarlo.",
                  (640, 356), 16, art.MUTED, center=True, max_width=578)
        self.button("Nueva aventura", (394, 418, 492, 52), "create", primary=True)
        self.button("Guardar resultado", (394, 487, 236, 48), "save")
        self.button("Menú principal", (650, 487, 236, 48), "menu")
        self.text("El resultado también puede guardarse y cargarse.", (640, 588),
                  15, art.MUTED, center=True)
