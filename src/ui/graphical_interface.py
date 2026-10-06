"""RPG 2D cinematográfico con combate en tiempo real y reglas en GameService."""

import math
from collections import deque
from dataclasses import dataclass

import pygame

from src.domain.exceptions import DomainError
from src.services.app_service import ApplicationError
from src.ui import pixel_art as art
from src.ui.cinematic import OpeningCinematic


@dataclass
class Button:
    rect: pygame.Rect
    action: str
    enabled: bool = True


class GraphicalGame:
    WIDTH, HEIGHT = 1280, 800
    MAP_ORIGIN = (32, 140)

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
        self.intro = None
        self.paused_from = "playing"
        self.swing_remaining = 0.0
        self.hit_effects = []
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
        if event.type == pygame.WINDOWFOCUSLOST and self.screen in ("playing", "intro"):
            self.paused_from = self.screen
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
        if self.screen == "intro":
            if key == pygame.K_RETURN:
                self._finish_intro()
            elif key == pygame.K_ESCAPE:
                self.handle_action("pause")
            return
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
                self.handle_action("pause")
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
            if self.world.projectiles:
                self.notify("Reanuda la partida y espera a que termine el fuego.")
                return
            self.screen = "menu"
            pygame.key.stop_text_input()
        elif action.startswith("class:"):
            self.hero_class = action.split(":")[1]
        elif action.startswith("color:"):
            self.selected_color = action.split(":")[1]
        elif action == "start":
            self.start_game()
        elif action == "load":
            if self.world.projectiles:
                self.notify("Espera a que termine el proyectil de fuego.")
                return
            messages = self.service.load_game()
            self.data_manager.restore_view(self.service.get_snapshot())
            self.swing_remaining, self.hit_effects, self.intro = 0.0, [], None
            self.messages.clear()
            self.record(messages)
            self.screen = "playing" if self.service.status == "playing" else "ending"
            self.notify(messages[-1])
        elif action == "resume":
            self.screen = ("intro" if self.intro and not self.intro.finished else
                           "playing" if self.service.status == "playing" else "ending")
        elif action == "pause":
            self.paused_from = self.screen
            self.screen = "pause"
        elif action == "save":
            if self.world.projectiles or (self.intro and not self.intro.finished):
                self.notify("Termina la introducción o espera a que se resuelva el fuego.")
                return
            messages = self.service.save_game()
            self.record(messages)
            self.notify(messages[-1])
        elif action in ("inventory", "appearance"):
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
            if self.screen != "playing" or self.service.status != "playing":
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
                if snapshot["hero"]["weapon"] is None:
                    self.notify("Recoge el arma de los restos y equípala con I antes de avanzar.")
                    return
                self.record(self.service.advance())
                self.world.enter_room(self.service.get_snapshot()["current_room_index"])
                self.hit_effects, self.swing_remaining = [], 0.0
            else:
                self.notify("Acércate a un objeto, enemigo o puerta y pulsa E.")

    def start_game(self):
        messages = self.service.start_new_game(self.name, self.hero_class, self.selected_color)
        self.world.enter_room(0)
        self.messages.clear()
        self.record(messages)
        self.swing_remaining, self.hit_effects = 0.0, []
        self.intro = OpeningCinematic()
        self.screen = "intro"
        self.notification_remaining = 0
        pygame.key.stop_text_input()

    def _finish_intro(self):
        self.intro.skip()
        self.screen = "playing"
        self.notify("Busca los restos del caído. E recoge el arma; I permite equiparla.")

    def attack(self):
        if self.world.hero_cooldown > 0:
            return
        before = self.service.get_snapshot()
        if not before["hero"]["weapon"]:
            self.notify("Debes recoger y equipar tu arma desde el inventario.")
            return
        if not self.world.can_attack(before):
            self.notify("Enemigo fuera de alcance o detrás de una roca.")
            return
        if before["hero"]["hero_class"] == "mage":
            spell_id = self.service.cast_fire()
            self.world.launch_fire(spell_id)
            self.record(["Lanzaste fuego. −15 de maná."])
        else:
            self.record(self.service.melee_attack())
            self.world.hero_cooldown = self.world.SWORD_INTERVAL
            self.swing_remaining = 0.28
            self._enemy_hit(before)

    def _enemy_hit(self, before):
        after = self.service.get_snapshot()
        damage = before["room"]["enemy"]["health"] - after["room"]["enemy"]["health"]
        self.hit_effects.append({"target": "enemy", "damage": damage, "age": 0.0,
                                 "position": self.world.enemy_position})
        if after["room"]["enemy"]["health"] == 0:
            self.world.mark_enemy_defeated()
            if after["room"]["item"]:
                self.notify("El Goblin dejó una armadura. Recógela con E y equípala con I.")

    def _clear_projectiles(self):
        for projectile in self.world.projectiles:
            self.service.cancel_fire(projectile.spell_id)
        self.world.projectiles.clear()

    def update(self, dt, movement=None):
        dt = max(0, min(dt, 0.1))
        self.time += dt
        self.notification_remaining = max(0, self.notification_remaining - dt)
        if self.screen == "intro":
            self.intro.update(dt)
            if self.intro.finished:
                self._finish_intro()
            return
        if self.screen != "playing":
            return
        if self.service.status != "playing":
            self._clear_projectiles()
            self.screen = "ending"
            return
        self.swing_remaining = max(0, self.swing_remaining - dt)
        for effect in self.hit_effects:
            effect["age"] += dt
        self.hit_effects = [e for e in self.hit_effects if e["age"] < 0.8]
        self.world.tick_cooldowns(dt)
        if movement is None:
            keys = pygame.key.get_pressed()
            movement = (int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) -
                        int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
                        int(keys[pygame.K_s] or keys[pygame.K_DOWN]) -
                        int(keys[pygame.K_w] or keys[pygame.K_UP]))
        enemy = self.service.get_snapshot()["room"].get("enemy")
        alive = bool(enemy and enemy["health"] > 0)
        self.world.move(*movement, dt, enemy_alive=alive)
        hits, misses = self.world.update_projectiles(dt, alive)
        for spell_id in misses:
            self.service.cancel_fire(spell_id)
        for spell_id in hits:
            before = self.service.get_snapshot()
            if self.service.status != "playing" or before["room"]["enemy"]["health"] <= 0:
                self.service.cancel_fire(spell_id)
                continue
            self.record(self.service.resolve_fire(spell_id))
            self._enemy_hit(before)
        snapshot = self.service.get_snapshot()
        enemy = snapshot["room"].get("enemy")
        alive = bool(enemy and enemy["health"] > 0)
        if self.world.update_enemy(dt, alive) and self.service.status == "playing":
            health = snapshot["hero"]["health"]
            self.record(self.service.enemy_attack())
            damage = health - self.service.get_snapshot()["hero"]["health"]
            self.hit_effects.append({"target": "hero", "damage": damage, "age": 0.0,
                                     "position": self.world.position})
        if not alive:
            self._clear_projectiles()
        if self.service.status != "playing":
            self._clear_projectiles()
            self.screen = "ending"

    def render(self):
        self.canvas.fill(art.BG)
        self.buttons = []
        if self.screen == "menu":
            self._draw_menu()
        elif self.screen == "create":
            self._draw_creation()
        elif self.screen == "intro":
            self._draw_intro()
        else:
            self._draw_game()
            if self.screen in ("pause", "inventory", "appearance", "ending"):
                shade = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
                shade.fill((6, 12, 21, 205))
                self.canvas.blit(shade, (0, 0))
                self.buttons = []
                {"pause": self._draw_pause, "inventory": self._draw_inventory,
                 "appearance": self._draw_appearance, "ending": self._draw_ending}[self.screen]()
        if self.notification_remaining > 0 and self.screen != "intro":
            self.panel((180, 738, 920, 43), border=art.GOLD)
            self.text(self.notification, (640, 759), 17, art.GOLD,
                      center=True, max_width=888)

    def _draw_menu(self):
        pygame.draw.rect(self.canvas, (14, 24, 35), (720, 0, 560, 800))
        self.text("GRUPO 1 / CONSTRUCCIÓN DE SOFTWARE", (86, 87), 17, art.MINT)
        self.text("PIXEL", (80, 156), 87, heading=True)
        self.text("QUEST", (80, 244), 87, art.MINT, heading=True)
        self.wrapped("Una cueva. Una pérdida. Tu venganza.",
                     (88, 363), 490, 23, art.MUTED)
        self.button("Nueva aventura     →", (88, 457, 442, 58), "create", primary=True)
        self.button("Cargar partida", (88, 529, 214, 50), "load")
        self.button("Continuar", (316, 529, 214, 50), "resume",
                    enabled=self.service.status != "not_started")
        self.button("Salir", (88, 594, 442, 46), "quit")
        self.text("EXPLORA · EQUIPA · SOBREVIVE", (88, 700), 16, art.MUTED)
        preview = pygame.transform.scale(art.room_background(2), (470, 262))
        self.canvas.blit(preview, (755, 314))
        art.draw_actor(self.canvas, art.hero_sprite("warrior", "#59C9A5", equipped=True, scale=7),
                       (870, 504), math.sin(self.time * 2) * 3)
        art.draw_actor(self.canvas, art.enemy_sprite(True), (1110, 498), math.sin(self.time * 2 + 1) * 3)
        self.text("EL GUARDIÁN TE ESPERA", (986, 624), 20, art.GOLD, center=True)
        self.text("2D / PIXEL ART / PARTIDA LOCAL", (986, 662), 15, art.MUTED, center=True)

    def _draw_intro(self):
        self.canvas.fill((0, 0, 0))
        image = self._font(42, True).render(self.intro.message, True, (255, 255, 255))
        image.set_alpha(self.intro.alpha)
        self.canvas.blit(image, image.get_rect(center=(640, 385)))
        self.text("ENTER · Omitir     ESC · Pausar", (640, 746), 14,
                  (91, 91, 91), center=True)

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
        self.text("LA CUEVA DE LOS GOBLINS", (33, 61), 15, art.MUTED)
        for index in range(snapshot["total_rooms"]):
            x = 506 + index * 83
            current = index == snapshot["current_room_index"]
            pygame.draw.circle(self.canvas, art.MINT if current else art.BORDER, (x, 51), 16)
            self.text(str(index + 1), (x, 51), 17, art.BG if current else art.TEXT, center=True)
            if index < snapshot["total_rooms"] - 1:
                pygame.draw.line(self.canvas, art.BORDER, (x + 23, 51), (x + 60, 51), 2)
        self.button("Guardar [F5]", (835, 27, 176, 44), "save", enabled=not self.world.projectiles)
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
        pygame.draw.ellipse(image, (13, 18, 23), door.inflate(14, 12))
        pygame.draw.ellipse(image, art.MINT if unlocked else art.RED, door, 2)
        if not unlocked:
            for x in range(door.x + 8, door.right - 2, 10):
                pygame.draw.line(image, (125, 119, 126), (x, door.y + 3), (x, door.bottom - 3), 3)
        else:
            pygame.draw.polygon(image, art.MINT, [(810, 224), (823, 240), (810, 256)])
        if world.room_index == 0:
            remains = art.remains_sprite(hero["hero_class"])
            image.blit(remains, remains.get_rect(center=world.ITEM))
        if room.get("item"):
            ix, iy = world.item_position
            item = room["item"]
            sprite = art.item_sprite(item["item_type"], item.get("weapon_kind"))
            image.blit(sprite, sprite.get_rect(midbottom=(ix + (38 if world.room_index == 0 else 0),
                                                          iy - 6 + math.sin(self.time * 3) * 3)))
        if enemy_alive and world.distance_to(world.enemy_position) <= world.CONTACT_RANGE + 15:
            pygame.draw.circle(image, art.RED, tuple(map(int, world.enemy_position)),
                               world.CONTACT_RANGE, 2)
        sprite = art.hero_sprite(hero["hero_class"], hero["color"], world.facing,
                                 bool(hero.get("weapon")), bool(hero.get("armor")))
        bob = math.sin(self.time * (16 if world.walking else 3)) * (3 if world.walking else 1)
        hero_flash = any(e["target"] == "hero" and e["age"] < 0.18 for e in self.hit_effects)
        enemy_flash = any(e["target"] == "enemy" and e["age"] < 0.18 for e in self.hit_effects)
        actors = [(world.position[1], sprite, world.position, bob, hero_flash, hero["health"] == 0)]
        if enemy:
            actors.append((world.enemy_position[1], art.enemy_sprite(enemy["is_boss"]),
                           world.enemy_position, math.sin(self.time * 3) * 2,
                           enemy_flash, not enemy_alive))
        for _, actor, position, bounce, flash, dead in sorted(actors, key=lambda a: a[0]):
            art.draw_actor(image, actor, position, bounce, flash=flash, dead=dead)
        for projectile in world.projectiles:
            x, y = map(int, projectile.position)
            for distance in (18, 12, 6):
                tx = x - projectile.velocity[0] / world.FIRE_SPEED * distance
                ty = y - 35 - projectile.velocity[1] / world.FIRE_SPEED * distance
                pygame.draw.circle(image, (190, 76, 38), (int(tx), int(ty)), 5)
            pygame.draw.circle(image, (237, 113, 43), (x, y - 35), 12)
            pygame.draw.circle(image, (255, 198, 91), (x, y - 35), 8)
            pygame.draw.circle(image, (255, 241, 189), (x, y - 35), 4)
        if self.swing_remaining > 0:
            hx, hy = world.position
            ex, ey = world.enemy_position
            angle = math.atan2(-(ey - hy), ex - hx)
            radius = world.ATTACK_RANGE
            pygame.draw.arc(image, art.GOLD, (hx - radius, hy - 35 - radius,
                                             radius * 2, radius * 2), angle - 0.55, angle + 0.55, 5)
        art.illuminate(image, self.time, world.position, world.projectiles)
        self.canvas.blit(image, self.MAP_ORIGIN)
        hero_position = (ox + world.position[0], oy + world.position[1])
        enemy_position = (ox + world.enemy_position[0], oy + world.enemy_position[1])
        if room.get("item"):
            ix, iy = world.item_position
            label = "Restos del hechicero" if hero["hero_class"] == "mage" else "Restos del guerrero"
            self.text(label if world.room_index == 0 else room["item"]["name"],
                      (ox + ix, oy + iy + 37), 15, art.GOLD, center=True)
        if enemy:
            self.text(enemy["name"], (enemy_position[0], enemy_position[1] - 123),
                      16, art.RED if enemy_alive else art.MUTED, center=True)
            self._health_bar(enemy_position[0] - 47, enemy_position[1] - 98, 94,
                             enemy["health"], enemy["max_health"], art.RED, 7)
        self.text(hero["name"], (hero_position[0], hero_position[1] - 88), 14,
                  art.TEXT, center=True, max_width=165)
        for effect in self.hit_effects:
            px, py = effect["position"]
            self.text(f"−{effect['damage']}", (ox + px, oy + py - 110 - effect["age"] * 35),
                      27, art.GOLD if effect["target"] == "enemy" else art.RED,
                      heading=True, center=True)
        if snapshot["status"] == "playing":
            action = world.context_action(snapshot)
            prompts = {"attack": "ESPACIO / E · Atacar", "collect": "E · Recoger objeto",
                       "advance": "E · Salir" if unlocked else "Puerta bloqueada: derrota al enemigo"}
            prompt = prompts.get(action, "Explora la sala con WASD o las flechas")
            self.panel((219, 582, 490, 30), color=(14, 22, 33))
            self.text(prompt, (464, 597), 14, art.GOLD if action else art.MUTED,
                      center=True, max_width=470)
        pygame.draw.rect(self.canvas, art.BORDER, (ox, oy, world.WIDTH, world.HEIGHT), 2)

    def _draw_sidebar(self, snapshot):
        hero, room = snapshot["hero"], snapshot["room"]
        self.panel((920, 140, 328, 616))
        self.text("TU HÉROE", (942, 159), 14, art.MINT)
        self.text(hero["name"], (942, 187), 26, heading=True, max_width=282)
        self.text("GUERRERO" if hero["hero_class"] == "warrior" else "MAGO", (943, 225), 14, art.MUTED)
        self.text(f"VIDA  {hero['health']} / {hero['max_health']}", (943, 263), 17)
        self._health_bar(943, 292, 280, hero["health"], hero["max_health"])
        if hero["hero_class"] == "mage":
            self.text(f"MANÁ  {hero['mana']} / {hero['max_mana']}", (943, 313), 16, art.BLUE)
            self._health_bar(943, 340, 280, hero["mana"], hero["max_mana"], art.BLUE, 8)
        else:
            self.text(f"ESPADA · ALCANCE {self.world.ATTACK_RANGE}px", (943, 325), 15, art.MUTED)
        attack = hero["base_attack"] + (hero["weapon"]["attack_bonus"] if hero["weapon"] else 0)
        defense = hero["base_defense"] + (hero["armor"]["defense_bonus"] if hero["armor"] else 0)
        self.text(f"ATQ {attack:02}        DEF {defense:02}", (943, 368), 21, art.GOLD)
        pygame.draw.line(self.canvas, art.BORDER, (943, 402), (1226, 402))
        self.text("EQUIPAMIENTO", (943, 415), 14, art.MUTED)
        self.text("Arma: " + (hero["weapon"]["name"] if hero["weapon"] else "Sin equipar"),
                  (943, 442), 16, max_width=280)
        self.text("Armadura: " + (hero["armor"]["name"] if hero["armor"] else "Sin equipar"),
                  (943, 468), 16, max_width=280)
        self.button("Inventario [I]", (943, 507, 280, 40), "inventory")
        self.button("Cambiar color [C]", (943, 557, 280, 40), "appearance")
        can_attack = self.world.can_attack(snapshot) and self.world.hero_cooldown == 0
        if hero["hero_class"] == "mage" and hero["mana"] < 15:
            can_attack = False
        self.button("Fuego · 15 maná" if hero["hero_class"] == "mage" else "Atacar [ESPACIO]",
                    (943, 607, 280, 45), "attack", enabled=can_attack, primary=True)
        enemy = room.get("enemy")
        goal = ("Derrota al guardián final." if room["is_final"] else "Esquiva al Goblin y recoge su armadura al vencerlo.") if enemy and enemy["health"] > 0 else "Recoge el arma de los restos y equípala con I." if self.world.room_index == 0 else "Recoge el botín y busca la salida."
        if snapshot["status"] != "playing":
            goal = "Aventura completada." if snapshot["status"] == "victory" else "Tu héroe ha caído."
        if hero["hero_class"] == "mage" and hero["mana"] < 15 and enemy and enemy["health"] > 0:
            goal = "Sin maná: carga un guardado anterior o inicia otra aventura."
        self.text("OBJETIVO", (943, 674), 13, art.MINT)
        self.wrapped(goal, (943, 699), 276, 15, max_lines=2)

    def _draw_pause(self):
        self.panel((414, 178, 452, 456))
        self.text("UN RESPIRO", (640, 225), 32, heading=True, center=True)
        self.text("La aventura te espera.", (640, 270), 18, art.MUTED, center=True)
        self.button("Continuar", (458, 318, 364, 50), "resume", primary=True)
        self.button("Guardar partida", (458, 382, 364, 48), "save", enabled=not self.world.projectiles and not (self.intro and not self.intro.finished))
        self.button("Cargar último guardado", (458, 444, 364, 48), "load", enabled=not self.world.projectiles)
        self.button("Menú principal", (458, 506, 364, 48), "menu", enabled=not self.world.projectiles)
        self.text("F5 guarda · F9 carga · Esc continúa", (640, 593), 14, art.MUTED, center=True)

    def _draw_inventory(self):
        hero = self.service.get_snapshot()["hero"]
        self.panel((260, 156, 760, 482))
        self.text("TU INVENTARIO", (296, 190), 31, heading=True)
        self.text("Equipar reemplaza el objeto del mismo tipo; los bonos no se acumulan.",
                  (296, 245), 15, art.MUTED, max_width=688)
        if not hero["inventory"]:
            self.text("Explora los restos del caído y recoge tu arma con E.", (640, 390),
                      19, art.MUTED, center=True)
        for index, item in enumerate(hero["inventory"]):
            y = 290 + index * 102
            self.panel((296, y, 688, 88), color=(13, 23, 35))
            self.canvas.blit(art.item_sprite(item["item_type"], item.get("weapon_kind")), (315, y + 19))
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
        self.text("LA CUEVA HA SIDO LIBERADA" if victory else "EL HÉROE HA CAÍDO",
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
