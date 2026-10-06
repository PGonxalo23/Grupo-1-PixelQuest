"""Pixel art original generado con Pygame; no requiere descargas de recursos."""

import math
import random
from functools import lru_cache

import pygame


BG = (10, 16, 26)
PANEL = (18, 28, 42)
BORDER = (40, 57, 73)
TEXT = (230, 235, 240)
MUTED = (140, 160, 175)
MINT = (89, 201, 165)
GOLD = (233, 187, 105)
RED = (232, 110, 117)
BLUE = (110, 160, 242)
TORCHES = ((144, 51), (432, 51), (752, 51), (144, 438), (432, 438), (752, 438))

COLORS = [
    ("Jade", "#59C9A5"), ("Amatista", "#A78BFA"),
    ("Ámbar", "#E9BB69"), ("Coral", "#E86E75"),
    ("Cielo", "#67B7EA"), ("Marfil", "#E6EBF0"),
]

WARRIOR = (
    "......HHHH......", ".....HHHHHH.....", "....HSSSSSSH....",
    "....HSKSSKSH....", ".....SSSSSS.....", "......SSSS......",
    "...DDCCCCDD.....", "..DDCCCCCCDD....", "..SDCCCCCCDS....",
    "..SSDCCCCDSS....", "..SSCCCCCCSS....", "...CCCCCCCC.....",
    "...CCCCCCCC.....", "....BBBBBB......", "....BBBBBB......",
    "....BB..BB......", "....BB..BB......", "...DDD..DDD.....",
)
MAGE = (
    ".......C........", "......CCC.......", ".....CCCCC......",
    "....CCCCCCC.....", "...CCCCCCCCC....", "..LLLLLLLLLLL...",
    "....HSSSSSH.....", "....HSKSKSH.....", ".....SSSSS......",
    "...CCCCCCCCC....", "..SCCCCCCCCCS...", "..SCCCLLLCCCS...",
    "...CCCLLLCCC....", "...CCCCCCCCC....", "...CCCCCCCCC....",
    "..CCCCCCCCCCC...", "..CCCCCCCCCCC...", "...DDD...DDD....",
)
GOBLIN = (
    "................", "...G........G...", "...GGGGGGGGGG...",
    "..GGGGGGGGGGGG..", "...GYKGGKYGGG...", "....GGGGGGGG....",
    ".....GSSSGG.....", "......GGGG......", "....BBBBBBBB....",
    "...GBBBBBBBBG...", "..GGBBBBBBBBGG..", "..GGBBBBBBBBGG..",
    "....LLLLLLLL....", "....BBBBBBBB....", "....BB..BB......",
    "....GG..GG......", "...GGG..GGG.....", "................",
)
BOSS = (
    "...D........D...", "...DD......DD...", "....DDDDDDDD....",
    "....DDDDDDDD....", "....DRKDDKRD....", ".....DDDDDD.....",
    "...DDDDDDDDDD...", "..DDDDDDDDDDDD..", ".DDDDLLLLLLDDDD.",
    ".DDDDLLRRLLDDDD.", ".DDDDLLLLLLDDDD.", "..DDDDDDDDDDDD..",
    "...DDDDDDDDDD...", "....BBBBBBBB....", "....BBB..BBB....",
    "....BBB..BBB....", "...DDDD..DDDD...", "................",
)


def tint(color, factor):
    return tuple(min(255, max(0, int(c * factor))) for c in color[:3])


def pattern_surface(pattern, palette, scale):
    image = pygame.Surface((max(map(len, pattern)), len(pattern)), pygame.SRCALPHA)
    for y, row in enumerate(pattern):
        for x, code in enumerate(row):
            if code in palette:
                image.set_at((x, y), palette[code])
    return pygame.transform.scale(image, (image.get_width() * scale,
                                         image.get_height() * scale))


@lru_cache(maxsize=128)
def hero_sprite(hero_class, color, facing="down", equipped=False, armor=False, scale=4):
    cloth = pygame.Color(color)
    palette = {"C": cloth, "L": GOLD, "S": (228, 184, 148),
               "H": (56, 45, 43), "K": (17, 28, 37), "B": (42, 53, 67),
               "D": (139, 163, 179) if armor else tint(cloth, 0.55)}
    image = pattern_surface(MAGE if hero_class == "mage" else WARRIOR, palette, scale)
    if equipped:
        if hero_class == "mage":
            pygame.draw.rect(image, (125, 88, 58), (13 * scale, 5 * scale, scale, 12 * scale))
            pygame.draw.circle(image, (255, 173, 75), (13 * scale, 5 * scale), 2 * scale)
        else:
            pygame.draw.rect(image, (205, 220, 229), (14 * scale, 6 * scale, scale, 8 * scale))
            pygame.draw.rect(image, GOLD, (13 * scale, 13 * scale, 3 * scale, scale))
    if facing == "up":
        # La nuca ocupa la misma zona de los ojos cuando el héroe mira hacia arriba.
        pygame.draw.rect(image, palette["H"], (5 * scale, (7 if hero_class == "mage" else 3) * scale,
                                               5 * scale, 2 * scale))
    if facing == "left":
        image = pygame.transform.flip(image, True, False)
    return image


@lru_cache(maxsize=4)
def enemy_sprite(boss=False):
    palette = {"G": (111, 156, 90), "Y": GOLD, "K": (16, 22, 29),
               "S": (215, 205, 169), "B": (64, 49, 45), "L": (154, 109, 62),
               "D": (113, 100, 145), "R": RED}
    return pattern_surface(BOSS if boss else GOBLIN, palette, 5 if boss else 4)


@lru_cache(maxsize=4)
def item_sprite(item_type, weapon_kind=None):
    image = pygame.Surface((48, 48), pygame.SRCALPHA)
    if item_type == "weapon" and weapon_kind == "staff":
        pygame.draw.line(image, (136, 93, 57), (13, 42), (31, 10), 5)
        pygame.draw.circle(image, (161, 75, 43), (32, 10), 10)
        pygame.draw.circle(image, (255, 167, 67), (32, 10), 7)
        pygame.draw.circle(image, (255, 236, 151), (33, 8), 3)
    elif item_type == "weapon":
        pygame.draw.polygon(image, (218, 230, 236), [(28, 3), (34, 9), (19, 34), (12, 29)])
        pygame.draw.line(image, (144, 168, 186), (29, 9), (17, 29), 3)
        pygame.draw.line(image, GOLD, (9, 27), (25, 36), 4)
        pygame.draw.line(image, (124, 84, 54), (15, 33), (9, 42), 5)
    else:
        pygame.draw.polygon(image, (169, 190, 204),
                            [(12, 7), (19, 11), (29, 11), (36, 7), (44, 15),
                             (36, 25), (33, 22), (34, 43), (14, 43), (15, 22), (10, 25), (4, 15)])
        pygame.draw.rect(image, (97, 125, 147), (18, 18, 12, 21))
        pygame.draw.rect(image, GOLD, (14, 33, 20, 4))
    return image


@lru_cache(maxsize=2)
def remains_sprite(hero_class):
    image = pygame.Surface((104, 60), pygame.SRCALPHA)
    bone = (198, 187, 157)
    pygame.draw.ellipse(image, (17, 19, 21), (0, 15, 104, 42))
    pygame.draw.polygon(image, (77, 58, 92) if hero_class == "mage" else (71, 95, 93),
                        [(27, 29), (67, 20), (80, 43), (35, 50)])
    pygame.draw.circle(image, bone, (18, 29), 10)
    pygame.draw.rect(image, (27, 26, 24), (13, 26, 4, 4))
    pygame.draw.rect(image, (27, 26, 24), (20, 26, 4, 4))
    pygame.draw.line(image, bone, (28, 30), (58, 33), 4)
    for x in (33, 40, 47, 54):
        pygame.draw.line(image, bone, (x, 24), (x, 39), 3)
    for start, end in (((29, 27), (42, 13)), ((30, 37), (46, 49)),
                       ((60, 31), (86, 17)), ((60, 35), (91, 47))):
        pygame.draw.line(image, bone, start, end, 4)
    if hero_class == "mage":
        pygame.draw.polygon(image, (113, 86, 138), [(5, 14), (15, 0), (30, 16)])
    else:
        pygame.draw.rect(image, (111, 126, 135), (4, 14, 26, 6))
    return image


def draw_actor(surface, sprite, position, bob=0, flash=False, dead=False):
    x, y = map(int, position)
    pygame.draw.ellipse(surface, (15, 20, 27), (x - 25, y - 7, 50, 16))
    if dead:
        image = pygame.transform.rotate(sprite, 90).copy()
        image.set_alpha(100)
        surface.blit(image, image.get_rect(center=(x, y - 7)))
        return
    image = sprite
    if flash:
        image = sprite.copy()
        image.fill((255, 130, 130, 0), special_flags=pygame.BLEND_RGBA_ADD)
    surface.blit(image, image.get_rect(midbottom=(x, y + int(bob))))


@lru_cache(maxsize=8)
def room_background(room_index):
    from src.ui.world import ExplorationWorld

    world = ExplorationWorld()
    world.enter_room(room_index)
    image = pygame.Surface((world.WIDTH, world.HEIGHT))
    rng = random.Random(413 + room_index)
    base = ((62, 58, 52), (55, 61, 57), (63, 54, 59))[room_index % 3]
    image.fill(base)
    for _ in range(450):
        x, y = rng.randrange(world.WIDTH), rng.randrange(world.HEIGHT)
        shade = tint(base, rng.choice((0.68, 0.83, 1.1, 1.25)))
        pygame.draw.ellipse(image, shade, (x, y, rng.randrange(3, 16), rng.randrange(2, 9)))
    for _ in range(26):
        x, y = rng.randrange(45, 800), rng.randrange(45, 430)
        pygame.draw.lines(image, tint(base, 0.6), False,
                          [(x, y), (x + 9, y + 5), (x + 22, y), (x + 29, y + 10)], 2)
    # Borde rocoso continuo con silueta irregular; coincide con el límite transitable.
    for row in range(15):
        for column in range(27):
            if row in (0, 14) or column in (0, 26):
                tile = pygame.Rect(column * 32, row * 32, 32, 32)
                image.fill((21, 24, 26), tile)
                points = [(tile.x + 2, tile.y + 14), (tile.x + 9, tile.y + 2),
                          (tile.x + 23, tile.y + 4), (tile.right - 1, tile.y + 19),
                          (tile.x + 25, tile.bottom - 2), (tile.x + 8, tile.bottom - 3)]
                pygame.draw.polygon(image, (76, 76, 73), points)
                pygame.draw.lines(image, (109, 106, 96), False, points[:3], 2)
    for x, y, w, h in world.obstacles:
        pygame.draw.ellipse(image, (24, 27, 28), (x - 5, y + h - 14, w + 22, 28))
        points = [(x, y + h - 8), (x + 7, y + 14), (x + w // 2, y),
                  (x + w - 9, y + 8), (x + w, y + h - 10), (x + w // 2, y + h)]
        pygame.draw.polygon(image, (81, 82, 78), points)
        pygame.draw.polygon(image, (116, 112, 99), points[:3] + [(x + w // 2, y + h - 7)])
        pygame.draw.line(image, (52, 56, 53), points[2], points[-1], 3)
    if room_index == 2:
        pygame.draw.ellipse(image, (64, 40, 40), (478, 178, 190, 142))
        pygame.draw.circle(image, (136, 84, 67), (573, 249), 47, 3)
        for angle in range(0, 360, 60):
            px, py = 573 + math.cos(math.radians(angle)) * 59, 249 + math.sin(math.radians(angle)) * 59
            pygame.draw.line(image, (170, 116, 76), (px - 4, py - 7), (px + 4, py + 7), 3)
    return image


def draw_torches(surface, time):
    for x, y in TORCHES:
        pygame.draw.rect(surface, (107, 75, 46), (x - 4, y, 8, 17))
        flame = 6 + int(math.sin(time * 9 + x) * 2)
        pygame.draw.circle(surface, (164, 82, 42), (x, y), flame + 4)
        pygame.draw.circle(surface, (237, 158, 75), (x, y - 3), flame)
        pygame.draw.circle(surface, (255, 220, 141), (x, y - 5), max(2, flame - 3))


@lru_cache(maxsize=16)
def light_pool(radius, color):
    pool = pygame.Surface((radius * 2, radius * 2))
    pool.fill((0, 0, 0))
    for r in range(radius, 0, -3):
        intensity = (1 - r / radius) ** 1.15
        pygame.draw.circle(pool, tuple(round(c * intensity) for c in color), (radius, radius), r)
    return pool


def illuminate(scene, time, hero_position, projectiles=()):
    light = pygame.Surface(scene.get_size())
    light.fill((82, 84, 91))
    for x, y in TORCHES:
        glow = light_pool(205, (160, 125, 75))
        offset = int(math.sin(time * 5 + x) * 2)
        light.blit(glow, (x - 205 + offset, y - 205), special_flags=pygame.BLEND_RGB_ADD)
    glow = light_pool(150, (83, 88, 95))
    light.blit(glow, (hero_position[0] - 150, hero_position[1] - 180), special_flags=pygame.BLEND_RGB_ADD)
    for projectile in projectiles:
        x, y = projectile.position
        light.blit(light_pool(95, (190, 135, 62)), (x - 95, y - 130), special_flags=pygame.BLEND_RGB_ADD)
    scene.blit(light, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
