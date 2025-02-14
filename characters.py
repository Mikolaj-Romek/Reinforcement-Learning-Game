import pygame
import random
import os
import math
import time
import json
import glob

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, RED, GREEN, BLUE,
    FPS, GRAVITY, JUMP_STRENGTH
)

class Character(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 30, 50)
        self.vel_y = 0
        self.jumping = False
        self.falling = False

    def move(self, dx, tile_map):
        self.rect.x += dx
        for tile in tile_map.obstacle_tiles:
            if self.rect.colliderect(tile.rect):
                if dx > 0:
                    self.rect.right = tile.rect.left
                elif dx < 0:
                    self.rect.left = tile.rect.right

    def jump(self):
        if not self.jumping and not self.falling:
            self.vel_y = JUMP_STRENGTH
            self.jumping = True
            return True
        return False

    def update(self, tile_map):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        for tile in tile_map.obstacle_tiles:
            if self.rect.colliderect(tile.rect):
                if self.vel_y > 0:
                    self.rect.bottom = tile.rect.top
                    self.jumping = False
                    self.falling = False
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = tile.rect.bottom
                    self.vel_y = 0

        if self.vel_y > 0:
            self.falling = True


class Player(Character):
    animation_lists = None

    @classmethod
    def load_animations(cls):
        if cls.animation_lists is None:
            cls.animation_lists = []
            animation_types = ["Idle", "Run", "Jump", "Death", "Attack", "Fall", "Hurt"]
            for animation in animation_types:
                temp_list = []
                num_of_frames = len(os.listdir(f"img/Player/{animation}"))
                for i in range(num_of_frames):
                    img = pygame.image.load(f"img/Player/{animation}/{i}.png").convert_alpha()
                    img = pygame.transform.scale(img, (int(img.get_width() * 2), int(img.get_height() * 2)))
                    temp_list.append(img)
                cls.animation_lists.append(temp_list)

    def __init__(self, x, y):
        super().__init__(x, y)
        if Player.animation_lists is None:
            Player.load_animations()
        self.animation_list = Player.animation_lists
        self.health = 100
        self.max_health = self.health
        self.speed = 6
        self.action = 0  # 0: Idle, 1: Run, 2: Jump, 3: Death, 4: Attack, 5: Fall, 6: Hurt
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.attacking = False
        self.attack_cooldown = 0
        self.facing_right = True
        self.alive = True
        self.hit_timer = 0
        self.knockback_speed = 0
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)
        self.shielded = False
        self.shield_blocked_attack = False
        self.attack_range = 50
        self.has_hit_enemy = False

        # For resetting:
        self.initial_x = x
        self.initial_y = y

    def update(self, tile_map):
        super().update(tile_map)
        if self.alive:
            self.update_animation()
            if self.attack_cooldown > 0:
                self.attack_cooldown -= 1
            
            if self.hit_timer > 0:
                self.hit_timer -= 1
                self.rect.x += self.knockback_speed
                self.knockback_speed *= 0.9  # Decelerate the knockback
            
            # If we land (no more jumping/falling), revert to Idle if we were in jump/fall/hurt
            if not self.jumping and not self.falling and self.hit_timer == 0:
                if self.action in [2, 5, 6]:
                    self.update_action(0)
            elif self.vel_y > 0 and not self.falling:
                self.falling = True
                self.update_action(5)
        else:
            # If not alive, only update the death animation
            self.update_death_animation()

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        self.image = self.animation_list[self.action][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        if self.frame_index >= len(self.animation_list[self.action]):
            if self.action == 4:  # Attack finished
                self.attacking = False
                self.update_action(0)  # Return to Idle
            elif self.action in [2, 5]:  # Jump or Fall
                self.frame_index = len(self.animation_list[self.action]) - 1
            elif self.action == 6:  # Hurt
                self.update_action(0)
            else:
                self.frame_index = 0

    def update_death_animation(self):
        ANIMATION_COOLDOWN = 150
        self.image = self.animation_list[3][self.frame_index]  # 3 => Death
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            if self.frame_index < len(self.animation_list[3]) - 1:
                self.frame_index += 1

    def move(self, dx, tile_map):
        if self.alive and not self.attacking and self.hit_timer == 0:
            super().move(dx, tile_map)
            if dx != 0:
                self.facing_right = (dx > 0)
                if not self.jumping and not self.falling:
                    self.update_action(1)  # Run
            else:
                if not self.jumping and not self.falling:
                    self.update_action(0)  # Idle

    def jump(self):
        if self.alive and super().jump():
            self.update_action(2)  # Jump
            return True
        return False

    def attack(self):
        if (self.alive and self.attack_cooldown == 0 and 
            not self.attacking and not self.jumping and not self.falling and self.hit_timer == 0):
            self.attacking = True
            self.attack_cooldown = 20
            self.update_action(4)  # Attack
            self.has_hit_enemy = False
            return True
        return False

    def update_action(self, new_action):
        if self.alive and new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def take_damage(self, amount, knockback_direction):
        if self.alive and not self.shielded:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(3)  # Death
                self.frame_index = 0
            else:
                self.hit_timer = 30
                self.knockback_speed = knockback_direction * 5
                self.update_action(6)  # Hurt
                self.attacking = False
                self.attack_cooldown = 0
        elif self.shielded:
            self.shield_blocked_attack = True

    def reset(self):
        self.rect.midbottom = (self.initial_x, self.initial_y)
        self.health = self.max_health
        self.alive = True
        self.action = 0
        self.frame_index = 0
        self.attacking = False
        self.attack_cooldown = 0
        self.facing_right = True
        self.hit_timer = 0
        self.knockback_speed = 0
        self.jumping = False
        self.falling = False
        self.vel_y = 0
        self.shielded = False
        self.shield_blocked_attack = False
        self.update_time = pygame.time.get_ticks()
        self.image = self.animation_list[self.action][self.frame_index]

    def reset_shield(self):
        self.shielded = False
        self.shield_blocked_attack = False


class AIPlayer(Player):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.decision_cooldown = 0
        self.attack_idle_time = 0
        self.has_hit_enemy = False

    def make_decision(self, enemy):
        if self.attack_idle_time > 0:
            self.attack_idle_time -= 1
            return

        if self.decision_cooldown > 0:
            self.decision_cooldown -= 1
            return

        dx = enemy.rect.centerx - self.rect.centerx

        # Approach the enemy
        if abs(dx) > 45:
            if dx > 0:
                self.move(self.speed, enemy)  # We would pass tile_map if needed
            else:
                self.move(-self.speed, enemy)
        else:
            # Attack with some probability
            if random.random() < 0.8:
                if self.attack():
                    self.attack_idle_time = 10
            else:
                # Occasionally step away
                self.move(-self.speed if dx > 0 else self.speed, enemy)
        self.decision_cooldown = 3

    def update(self, enemy, tile_map):
        super().update(tile_map)
        self.make_decision(enemy)

        # Check for hitting the enemy
        if self.attacking and not self.has_hit_enemy:
            if (abs(self.rect.centerx - enemy.rect.centerx) < 50 and
                abs(self.rect.centery - enemy.rect.centery) < 50):
                knockback_direction = 1 if self.facing_right else -1
                enemy.take_damage(5, knockback_direction)
                self.has_hit_enemy = True

        # Reset when attack ends
        if not self.attacking:
            self.has_hit_enemy = False

    def move(self, dx, _unused):
        if self.alive and not self.attacking and self.hit_timer == 0:
            self.rect.x += dx
            self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
            if dx != 0:
                self.facing_right = (dx > 0)
                if not self.jumping and not self.falling:
                    self.update_action(1)  # Run
            else:
                if not self.jumping and not self.falling:
                    self.update_action(0)  # Idle

    def attack(self):
        if super().attack():
            self.attack_idle_time = 30
            self.has_hit_enemy = False
            return True
        return False

    def reset(self):
        self.rect.x = random.randint(50, 750)
        self.rect.bottom = SCREEN_HEIGHT - 50
        self.health = self.max_health
        self.alive = True
        self.action = 0
        self.frame_index = 0
        self.attacking = False
        self.jumping = False
        self.falling = False
        self.vel_y = 0
        self.facing_right = True
        self.decision_cooldown = 0
        self.attack_idle_time = 0
        self.has_hit_enemy = False
