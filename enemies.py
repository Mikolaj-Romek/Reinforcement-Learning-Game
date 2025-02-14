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
from characters import Character
from sarsa import SARSA


class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.image.load("img/archer/arrow/0.png").convert_alpha()
        self.image = pygame.transform.scale(
            self.image,
            (int(self.image.get_width() * 1.5), int(self.image.get_height() * 1.5))
        )
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 6
        self.direction = direction
        self.vel_y = 0
        self.angle = 0
        self.stopped = False

    def update(self):
        if not self.stopped:
            self.vel_y += GRAVITY * 0.05
            self.rect.x += self.speed * self.direction
            self.rect.y += self.vel_y

            # Rotate arrow
            self.angle = -math.atan2(self.vel_y, self.speed * self.direction)
            rotated_image = pygame.transform.rotate(
                pygame.image.load("img/archer/arrow/0.png").convert_alpha(),
                math.degrees(self.angle)
            )
            self.image = pygame.transform.scale(
                rotated_image,
                (int(rotated_image.get_width() * 1.5), int(rotated_image.get_height() * 1.5))
            )

            if self.rect.bottom >= SCREEN_HEIGHT - 60:
                self.rect.bottom = SCREEN_HEIGHT - 60
                self.stopped = True

        # Remove if off-screen
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()


class Enemy(Character):
    animation_lists = None

    @classmethod
    def load_animations(cls):
        if cls.animation_lists is None:
            cls.animation_lists = []
            animation_types = ["Idle", "Run", "Death", "Attack"]
            for animation in animation_types:
                temp_list = []
                num_of_frames = len(os.listdir(f"img/archer/{animation}"))
                for i in range(num_of_frames):
                    img = pygame.image.load(f"img/archer/{animation}/{i}.png").convert_alpha()
                    img = pygame.transform.scale(img, (int(img.get_width() * 1.5), int(img.get_height() * 1.5)))
                    temp_list.append(img)
                cls.animation_lists.append(temp_list)

    def __init__(self, x, y):
        super().__init__(x, y)
        if Enemy.animation_lists is None:
            Enemy.load_animations()
        self.animation_list = Enemy.animation_lists
        self.health = 50
        self.max_health = self.health
        self.previous_health = self.health
        self.speed = 5
        self.direction = 1
        self.action = 0  # 0: Idle, 1: Run, 2: Death, 3: Attack
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.alive = True
        self.death_timer = time.time()
        self.vertical_offset = 0
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.arrow_group = pygame.sprite.Group()
        self.attacking = False
        self.attack_frame = 0
        self.invulnerable_timer = 0
        self.invulnerable_duration = 60
        self.just_attacked = False
        self.death_penalty_applied = False

        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.x = max(0, min(x, SCREEN_WIDTH - self.rect.width))
        self.rect.bottom = y + self.vertical_offset

        self.sarsa = SARSA(character_type="enemy")
        self.previous_state = None
        self.previous_action = None
        self.episode_steps = 0
        self.total_reward = 0
        self.knockback_velocity = 0
        self.knockback_decay = 0.8

    def get_state(self, player):
        dx = player.rect.x - self.rect.x
        dy = player.rect.y - self.rect.y

        if abs(dx) <= 40:
            x_state = "melee_range"
        elif abs(dx) <= 80:
            x_state = "close"
        elif abs(dx) <= 120:
            x_state = "medium_close"
        elif abs(dx) <= 160:
            x_state = "medium"
        elif abs(dx) <= 200:
            x_state = "medium_far"
        elif abs(dx) <= 250:
            x_state = "far"
        elif abs(dx) <= 300:
            x_state = "very_far"
        else:
            x_state = "extreme_range"

        x_direction = "right" if dx > 0 else "left"

        if abs(dy) <= 50:
            y_state = "same_level"
        elif dy < -50:
            y_state = "above"
        else:
            y_state = "below"

        enemy_health = "high" if self.health > 35 else ("medium" if self.health > 15 else "low")
        player_health = "high" if player.health > 66 else ("medium" if player.health > 33 else "low")

        facing_player = "facing_player" if (
            (self.direction == 1 and dx > 0) or (self.direction == -1 and dx < 0)
        ) else "not_facing_player"

        attack_ready = "attack_ready" if self.attack_cooldown == 0 else "attack_cooldown"

        if self.rect.left <= 100:
            wall_state = "far_to_left_wall"
        elif self.rect.right >= SCREEN_WIDTH - 100:
            wall_state = "far_to_right_wall"
        else:
            wall_state = "no_wall"

        return f"{x_state}_{x_direction}_{y_state}_{enemy_health}_{player_health}_{facing_player}_{attack_ready}_{wall_state}"

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        max_frames = len(self.animation_list[self.action])
        self.frame_index = min(self.frame_index, max_frames - 1)

        self.image = self.animation_list[self.action][self.frame_index]
        if self.direction == -1:
            self.image = pygame.transform.flip(self.image, True, False)

        # Flash / invulnerable
        if self.flash_timer > 0 and self.flash_timer % 4 < 2:
            self.image = self.image.copy()
            self.image.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)
        elif self.invulnerable_timer > 0 and self.invulnerable_timer % 4 < 2:
            self.image = self.image.copy()
            self.image.fill((200, 200, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)

        if self.attacking:
            # Attack animation uses a separate index
            self.frame_index = self.attack_frame
        elif pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
            if self.frame_index >= max_frames:
                if self.action == 2:  # Death
                    self.frame_index = max_frames - 1
                elif self.action == 3:  # Attack
                    self.frame_index = 0
                    self.update_action(0)
                else:
                    self.frame_index = 0

    def update_action(self, new_action):
        if new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def update(self, player, tile_map):
        super().update(tile_map)
        self.update_animation()
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1

        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.alive:
            current_state = self.get_state(player)
            action = self.sarsa.get_action(current_state)

            # Only act if not heavily knocked back
            if abs(self.knockback_velocity) < 1:
                self.act(action, tile_map)

            # Apply knockback
            if self.knockback_velocity != 0:
                new_x = self.rect.x + int(self.knockback_velocity)
                if 0 <= new_x <= SCREEN_WIDTH - self.rect.width:
                    self.rect.x = new_x
                else:
                    self.rect.x = max(0, min(SCREEN_WIDTH - self.rect.width, new_x))
                    self.knockback_velocity = 0
                self.knockback_velocity *= self.knockback_decay
                if abs(self.knockback_velocity) < 0.5:
                    self.knockback_velocity = 0

            self.previous_state = current_state
            self.previous_action = action
            self.episode_steps += 1

        if self.attacking:
            self.attack_frame += 1
            if self.attack_frame >= len(self.animation_list[3]):
                self.attacking = False
                self.attack_frame = 0
                self.shoot_arrow()

        self.arrow_group.update()

    def act(self, action, tile_map):
        if self.alive and self.knockback_velocity == 0:
            if action == 'move_left':
                self.direction = -1
                self.move_ai(tile_map)
            elif action == 'move_right':
                self.direction = 1
                self.move_ai(tile_map)
            elif action == 'shoot':
                self.attack()

    def move_ai(self, tile_map):
        super().update(tile_map)
        if self.alive and not self.attacking:
            new_x = self.rect.x + self.direction * self.speed
            if 0 <= new_x <= SCREEN_WIDTH - self.rect.width:
                self.rect.x = new_x
            else:
                self.direction *= -1
            self.update_action(1)  # Run

    def attack(self):
        if self.attack_cooldown == 0 and self.alive and not self.attacking:
            self.attacking = True
            self.attack_frame = 0
            self.attack_cooldown = 90
            self.update_action(3)
            self.just_attacked = True
            return True
        return False

    def shoot_arrow(self):
        arrow_x = self.rect.centerx + (50 * self.direction)
        arrow_y = self.rect.centery - 10
        new_arrow = Arrow(arrow_x, arrow_y, self.direction)
        self.arrow_group.add(new_arrow)

    def take_damage(self, amount, knockback_direction):
        if self.alive and self.invulnerable_timer == 0:
            self.health -= amount
            self.flash_timer = 30
            self.update_action(0)
            self.invulnerable_timer = self.invulnerable_duration
            self.knockback_velocity = knockback_direction * 10

            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(2)

    def draw_arrows(self, surface):
        self.arrow_group.draw(surface)

    def check_arrow_hit(self, player):
        hit_player = False
        killed_player = False
        for arrow in self.arrow_group:
            if (player.alive and not player.shielded
                and not arrow.stopped
                and arrow.rect.colliderect(player.rect)):
                knockback_direction = 1 if arrow.direction > 0 else -1
                player.take_damage(10, knockback_direction)
                arrow.kill()
                hit_player = True
                if not player.alive:
                    killed_player = True
                break
        return hit_player, killed_player

    def reset(self):
        self.health = self.max_health
        self.previous_health = self.health
        self.rect.x = 500
        self.rect.y = SCREEN_HEIGHT - 200
        self.alive = True
        self.action = 0
        self.frame_index = 0
        self.arrow_group.empty()
        self.attacking = False
        self.attack_frame = 0
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.episode_steps = 0
        self.total_reward = 0
        self.previous_state = None
        self.previous_action = None
        self.invulnerable_timer = 0
        self.just_attacked = False
        self.death_penalty_applied = False
        self.knockback_velocity = 0

    def end_episode(self):
        self.sarsa.end_episode()
        self.episode_steps = 0
        self.total_reward = 0
