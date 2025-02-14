import pygame
import os

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, RED, GREEN, BLUE,
    FPS, GRAVITY, JUMP_STRENGTH
)

class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, image):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y


class TileMap:
    def __init__(self):
        self.tile_size = 32
        self.wall_img = pygame.image.load("img/tiles/wall.png").convert_alpha()
        self.ground_img = pygame.image.load("img/tiles/ground.png").convert_alpha()
        self.platform_img = pygame.image.load("img/tiles/platform.png").convert_alpha()
        self.tiles = pygame.sprite.Group()
        self.obstacle_tiles = pygame.sprite.Group()
        self.create_map()

    def create_map(self):
        level = [
            "                        ",
            "                        ",
            "                        ",
            "                              ",
            "                   PPPPP      ",
            "                              ",
            "             PPPPPP           ",
            "                              ",
            "       PPPP                   ",
            "                              ",
            "                              ",
            "                              ",
            "                              ",
            "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"
        ]

        for row, tiles in enumerate(level):
            for col, tile in enumerate(tiles):
                if tile == "W":
                    wall_tile = Tile(col * self.tile_size, row * self.tile_size, self.wall_img)
                    self.tiles.add(wall_tile)
                    self.obstacle_tiles.add(wall_tile)
                elif tile == "G":
                    ground_tile = Tile(col * self.tile_size, row * self.tile_size, self.ground_img)
                    self.tiles.add(ground_tile)
                    self.obstacle_tiles.add(ground_tile)
                elif tile == "P":
                    platform_tile = Tile(col * self.tile_size, row * self.tile_size, self.platform_img)
                    self.tiles.add(platform_tile)
                    self.obstacle_tiles.add(platform_tile)

    def draw(self, surface):
        self.tiles.draw(surface)
