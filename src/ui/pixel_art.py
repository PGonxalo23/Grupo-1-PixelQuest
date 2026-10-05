"""Pixel art original generado con Pygame; no requiere descargas de recursos."""

import math
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
            pygame.draw.circle(image, MINT, (13 * scale, 5 * scale), 2 * scale)
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
def item_sprite(item_type):
    image = pygame.Surface((48, 48), pygame.SRCALPHA)
    if item_type == "weapon":
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
    base = ((42, 51, 61), (42, 54, 56), (48, 44, 60))[room_index % 3]
    for row in range(world.HEIGHT // 32):
        for column in range(world.WIDTH // 32):
            tile = pygame.Rect(column * 32, row * 32, 32, 32)
            variation = ((row * 37 + column * 19) % 5 - 2) * 2
            color = tuple(c + variation for c in base)
            image.fill(color, tile)
            pygame.draw.rect(image, tint(base, 0.7), tile, 1)
            if (row * 11 + column * 17) % 13 == 0:
                pygame.draw.line(image, tint(base, 0.75), tile.topleft, (tile.x + 8, tile.y + 11), 1)
    # Paredes con bordes de piedra.
    for row in range(15):
        for column in range(27):
            if row in (0, 14) or column in (0, 26):
                tile = pygame.Rect(column * 32, row * 32, 32, 32)
                image.fill((25, 32, 43), tile)
                pygame.draw.rect(image, (64, 72, 84), tile.inflate(-3, -4), 2)
                pygame.draw.line(image, (79, 89, 98), (tile.x + 3, tile.y + 3),
                                 (tile.right - 3, tile.y + 3), 2)
    for x, y, w, h in world.obstacles:
        pygame.draw.rect(image, (24, 29, 39), (x + 8, y + 12, w, h))
        pygame.draw.rect(image, (65, 75, 90), (x, y, w, h))
        pygame.draw.rect(image, (102, 111, 124), (x, y, w, 9))
        pygame.draw.rect(image, (40, 48, 62), (x + 7, y + 15, w - 14, h - 21), 3)
        pygame.draw.line(image, (88, 96, 108), (x + 2, y + h - 5), (x + w - 3, y + h - 5), 3)
    if room_index == 2:
        pygame.draw.rect(image, (88, 46, 59), (480, 180, 160, 128))
        pygame.draw.rect(image, GOLD, (485, 185, 150, 118), 2)
    return image


def draw_torches(surface, time):
    for x, y in ((144, 51), (432, 51), (752, 51), (144, 438), (752, 438)):
        pygame.draw.rect(surface, (107, 75, 46), (x - 4, y, 8, 17))
        flame = 6 + int(math.sin(time * 9 + x) * 2)
        pygame.draw.circle(surface, (164, 82, 42), (x, y), flame + 4)
        pygame.draw.circle(surface, (237, 158, 75), (x, y - 3), flame)
        pygame.draw.circle(surface, (255, 220, 141), (x, y - 5), max(2, flame - 3))
