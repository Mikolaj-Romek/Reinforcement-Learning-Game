import pygame
import os
import time
import math

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, RED, GREEN, BLUE,
    FPS, GRAVITY, JUMP_STRENGTH
)
from sarsa import SARSA

class Bird(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.load_animations()
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.speed = 3
        self.heal_cooldown = 0
        self.heal_cooldown_max = 300
        self.state = "idle"
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.facing_right = True
        
        self.sarsa = SARSA(character_type="bird")
        self.previous_state = None
        self.previous_action = None
        self.total_reward = 0
        self.previous_distance = float('inf')
        
        # Shield
        self.shield_cooldown = 0
        self.shield_cooldown_max = 390  # 6.5s at 60 FPS
        self.shield_duration = 90       # 1.5s
        self.shield_active = False
        self.shield_loading = False
        self.shield_frame = 0
        self.shield_animations = {
            "loading": self.load_animation("shield/loading", scale=1),
            "working": self.load_animation("shield/working", scale=1)
        }
        self.shield_reward_given = False
        self.shield_start_time = 0
        self.unnecessary_shield_use = False

    def load_animations(self):
        self.animations = {
            "idle": self.load_animation("bird", scale=0.05),
        }
        self.image = self.animations["idle"][0]

    def load_animation(self, folder, scale=1):
        animation = []
        folder_path = f"img/{folder}"
        for i in range(len(os.listdir(folder_path))):
            img = pygame.image.load(f"{folder_path}/{i}.png").convert_alpha()
            img = pygame.transform.scale(
                img, 
                (int(img.get_width() * scale), int(img.get_height() * scale))
            )
            animation.append(img)
        return animation

    def update(self, player, enemy, knight):
        self.heal_cooldown = max(0, self.heal_cooldown - 1)
        self.shield_cooldown = max(0, self.shield_cooldown - 1)

        current_state = self.get_state(player, knight=knight, enemy=enemy)
        action = self.sarsa.get_action(current_state)
        self.perform_action(action, player)

        reward = self.get_reward(player, knight=knight, enemy=enemy)
        self.total_reward += reward

        next_state = self.get_state(player, knight=knight, enemy=enemy)
        next_action = self.sarsa.get_action(next_state)

        if self.previous_state is not None and self.previous_action is not None:
            self.sarsa.update_q_table(self.previous_state, self.previous_action, reward, current_state, action)

        self.previous_state = current_state
        self.previous_action = action

        self.update_animation()
        self.update_shield(player)

    def get_state(self, player, knight=None, enemy=None):
        dx = abs(self.rect.centerx - player.rect.centerx)
        dy = player.rect.top - self.rect.bottom  # Positive if bird is above player

        if dx <= 100 and dy <= 100:
            proximity = "close"
        elif dx <= 150 and dy <= 150:
            proximity = "far"
        else:
            proximity = "very_far"

        x_direction = "right" if player.rect.centerx > self.rect.centerx else "left"
        y_direction = "above" if player.rect.centery < self.rect.centery else "below"

        shield_state = "shield_active" if self.shield_active else "shield_inactive"
        shield_cooldown = "shield_ready" if self.shield_cooldown == 0 else "shield_cooldown"

        # Knight distances and action
        if knight:
            player_to_knight_distance = abs(player.rect.centerx - knight.rect.centerx)
            if player_to_knight_distance <= 60:
                pk_distance = "very_close"
            elif player_to_knight_distance <= 100:
                pk_distance = "close"
            elif player_to_knight_distance <= 200:
                pk_distance = "medium"
            else:
                pk_distance = "far"
            knight_action = ["idle", "attack", "walk", "death", "block"][knight.action]
        else:
            pk_distance = "far"
            knight_action = "idle"

        # Enemy distances and action
        if enemy:
            player_to_enemy_distance = abs(player.rect.centerx - enemy.rect.centerx)
            if player_to_enemy_distance <= 50:
                pe_distance = "very_close"
            elif player_to_enemy_distance <= 100:
                pe_distance = "close"
            elif player_to_enemy_distance <= 200:
                pe_distance = "medium"
            else:
                pe_distance = "far"
            enemy_action = ["idle", "run", "death", "attack"][enemy.action]
        else:
            pe_distance = "far"
            enemy_action = "idle"

        return f"{proximity}_{x_direction}_{y_direction}_{shield_state}_{shield_cooldown}_{pk_distance}_{pe_distance}_{knight_action}_{enemy_action}"

    def perform_action(self, action, player):
        dx, dy = 0, 0
        if action == 'move_up':
            dy = -self.speed
        elif action == 'move_down':
            dy = self.speed
        elif action == 'move_left':
            dx = -self.speed
            self.facing_right = False
        elif action == 'move_right':
            dx = self.speed
            self.facing_right = True
        elif action == 'move_up_left':
            dx, dy = -self.speed, -self.speed
            self.facing_right = False
        elif action == 'move_up_right':
            dx, dy = self.speed, -self.speed
            self.facing_right = True
        elif action == 'move_down_left':
            dx, dy = -self.speed, self.speed
            self.facing_right = False
        elif action == 'move_down_right':
            dx, dy = self.speed, self.speed
            self.facing_right = True
        elif action == 'activate_shield':
            self.activate_shield(player)

        self.rect.x += dx
        self.rect.y += dy

        # Keep the bird in the screen
        self.rect.clamp_ip(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT))

    def get_reward(self, player, knight=None, enemy=None):
        reward = 0
        dx = self.rect.x - player.rect.x
        dy = player.rect.y - self.rect.y

        # Horizontal proximity
        if dx <= 150:
            reward += 0.5
        else:
            reward -= 0.1

        # Vertical "sweet spot"
        if 130 <= dy <= 170:
            reward += 1
        else:
            reward -= 1

        # Reward for blocking
        if player.shielded and not self.shield_reward_given:
            if enemy:
                for arrow in enemy.arrow_group:
                    if not arrow.stopped and arrow.rect.colliderect(player.rect):
                        reward += 50
                        self.shield_reward_given = True
                        self.unnecessary_shield_use = False
                        break
            else:
                # Could check knight's attack here
                self.unnecessary_shield_use = True

        # Unnecessary shield penalty
        if (self.unnecessary_shield_use and not player.shielded
           and time.time() - self.shield_start_time >= self.shield_duration / 60):
            reward -= 5
            self.unnecessary_shield_use = False

        return reward

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        self.image = self.animations[self.state][self.frame_index]
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        if self.frame_index >= len(self.animations[self.state]):
            self.frame_index = 0

    def activate_shield(self, player):
        if self.shield_cooldown == 0 and not self.shield_active and not self.shield_loading:
            self.shield_loading = True
            self.shield_frame = 0
            player.shielded = True
            self.shield_reward_given = False
            self.shield_start_time = time.time()
            self.unnecessary_shield_use = False

    def update_shield(self, player):
        if self.shield_loading:
            self.shield_frame += 1
            # Once done "loading", we flip to active
            if self.shield_frame >= len(self.shield_animations["loading"]) * 2:
                self.shield_loading = False
                self.shield_active = True
                self.shield_frame = 0
        elif self.shield_active:
            self.shield_frame += 1
            if self.shield_frame >= self.shield_duration:
                self.shield_active = False
                player.shielded = False
                self.shield_cooldown = self.shield_cooldown_max
                if self.unnecessary_shield_use:
                    self.total_reward -= 5
                self.unnecessary_shield_use = False

    def draw_shield(self, screen, player):
        if self.shield_loading:
            idx = self.shield_frame // 2 % len(self.shield_animations["loading"])
            shield_image = self.shield_animations["loading"][idx]
            screen.blit(shield_image, (self.rect.centerx - shield_image.get_width() // 2,
                                       self.rect.top - shield_image.get_height()))
        elif self.shield_active:
            idx = self.shield_frame // 6 % len(self.shield_animations["working"])
            shield_image = self.shield_animations["working"][idx]
            shield_image.set_alpha(128)
            screen.blit(shield_image,
                        (player.rect.centerx - shield_image.get_width() // 2,
                         player.rect.centery - shield_image.get_height() // 2))

    def reset(self):
        self.rect.center = (400, SCREEN_HEIGHT - 100)
        self.heal_cooldown = 0
        self.state = "idle"
        self.frame_index = 0
        self.previous_state = None
        self.previous_action = None
        self.total_reward = 0
        self.facing_right = True
        self.previous_distance = float('inf')
        self.shield_cooldown = 0
        self.shield_active = False
        self.shield_loading = False
        self.shield_frame = 0
        self.shield_reward_given = False
        self.unnecessary_shield_use = False

    def end_episode(self):
        self.sarsa.end_episode()
        print(f"Epsilon: {self.sarsa.epsilon:.6f}, Alpha: {self.sarsa.alpha:.6f}")
        self.total_reward = 0
