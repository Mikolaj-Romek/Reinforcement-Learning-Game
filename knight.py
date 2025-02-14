import pygame
import os
import math
import time

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, RED, GREEN, BLUE,
    FPS, GRAVITY, JUMP_STRENGTH
)
from characters import Character
from sarsa import SARSA

class Knight(Character):
    animation_lists = None

    @classmethod
    def load_animations(cls):
        if cls.animation_lists is None:
            cls.animation_lists = []
            animation_types = ["Idle", "Attack", "Walk", "Death", "Block"]
            for animation in animation_types:
                temp_list = []
                # The original code had "img\\knight\\{animation}", but here
                # we unify to forward slashes. Adjust if needed on Windows:
                anim_path = f"img/knight/{animation}"
                num_of_frames = len(os.listdir(anim_path))
                for i in range(num_of_frames):
                    img = pygame.image.load(f"{anim_path}/{i}.png").convert_alpha()
                    img = pygame.transform.scale(img, (int(img.get_width() * 2), int(img.get_height() * 2)))
                    temp_list.append(img)
                cls.animation_lists.append(temp_list)

    def __init__(self, x, y):
        super().__init__(x, y)
        if Knight.animation_lists is None:
            Knight.load_animations()
        self.animation_list = Knight.animation_lists
        self.health = 100
        self.max_health = self.health
        self.previous_health = self.health
        self.speed = 3
        self.direction = 1
        self.action = 0  # 0: Idle, 1: Attack, 2: Walk, 3: Death, 4: Block
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.alive = True
        self.death_timer = time.time()
        self.vertical_offset = 0
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.attacking = False
        self.blocking = False
        self.attack_frame = 0
        self.invulnerable_timer = 0
        self.invulnerable_duration = 60
        self.just_attacked = False
        self.death_penalty_applied = False
        self.shield_used = False
        self.attack_landed = False
        
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.x = max(0, min(x, SCREEN_WIDTH - self.rect.width))
        self.rect.bottom = y + self.vertical_offset
        
        self.sarsa = SARSA(character_type="knight")
        self.previous_state = None
        self.previous_action = None
        self.episode_steps = 0
        self.total_reward = 0
        self.knockback_velocity = 0
        self.knockback_decay = 0.7
        self.shield_cooldown = 0
        self.shield_cooldown_max = 60
        
        self.attack_range = 60
        self.block_duration = 0
        self.max_block_duration = 120
        self.block_release_cooldown = 60
        self.player = None
        
        self.hit_player = False
        self.killed_player = False

    def get_state(self, player):
        dx = player.rect.x - self.rect.x
        dy = player.rect.y - self.rect.y
        
        # Distance
        if abs(dx) <= self.attack_range:
            x_state = "melee_range"
        elif abs(dx) <= 100:
            x_state = "close"
        elif abs(dx) <= 200:
            x_state = "medium"
        else:
            x_state = "far"
        
        x_direction = "right" if dx > 0 else "left"
        
        if abs(dy) <= 50:
            y_state = "same_level"
        elif dy < -50:
            y_state = "above"
        else:
            y_state = "below"
        
        knight_health = "high" if self.health > 66 else ("medium" if self.health > 20 else "low")
        player_health = "high" if player.health > 66 else ("medium" if player.health > 20 else "low")

        current_action = ["idle", "attack", "walk", "death", "block"][self.action]
        
        facing_player = "facing_player" if self.is_facing_player() else "not_facing_player"
        attack_ready = "attack_ready" if self.attack_cooldown == 0 else "attack_cooldown"
        player_attacking = "player_attacking" if player.attacking else "player_not_attacking"

        if self.rect.left <= 50:
            wall_state = "close_to_left_wall"
        elif self.rect.right >= SCREEN_WIDTH - 50:
            wall_state = "close_to_right_wall"
        else:
            wall_state = "no_wall"
            
        shield_ready = "shield_ready" if self.shield_cooldown == 0 else "shield_cooldown"
        
        block_state = f"blocking_{self.block_duration // 30}" if self.blocking else "not_blocking"
        
        return (f"{x_state}_{x_direction}_{y_state}_{knight_health}_{player_health}_"
                f"{current_action}_{facing_player}_{attack_ready}_{player_attacking}_"
                f"{wall_state}_{shield_ready}_{block_state}")

    def is_facing_player(self):
        if self.player:
            return ((self.direction == 1 and self.player.rect.centerx > self.rect.centerx) or
                    (self.direction == -1 and self.player.rect.centerx < self.rect.centerx))
        return False

    def act(self, action, player, tile_map):
        self.player = player
        if self.attacking:
            return
        if action == 'move_left':
            self.direction = -1
            self.move_ai(tile_map)
        elif action == 'move_right':
            self.direction = 1
            self.move_ai(tile_map)
        elif action == 'attack':
            self.attack()
        elif action == 'block':
            if not self.blocking:
                self.block()
            elif self.block_duration >= self.max_block_duration:
                self.release_block()
        elif action == 'maintain_block':
            if self.blocking and self.block_duration < self.max_block_duration and self.is_facing_player():
                self.block_duration += 1
            else:
                self.release_block()
        elif action == 'idle':
            if self.blocking:
                self.release_block()
            else:
                self.update_action(0)

        self.previous_action = action

    def move_ai(self, tile_map):
        if self.alive and not self.attacking and not self.blocking:
            dx = self.direction * self.speed
            self.move(dx, tile_map)
            self.update_action(2)  # Walk

    def attack(self):
        if (self.attack_cooldown == 0 and self.alive and 
            not self.attacking and not self.blocking):
            self.attacking = True
            self.attack_frame = 0
            self.attack_cooldown = 60
            self.update_action(1)
            self.attack_landed = False
            self.just_attacked = True
            return True
        return False

    def block(self):
        if (self.alive and not self.attacking and not self.blocking and 
            self.shield_cooldown == 0 and self.is_facing_player()):
            self.blocking = True
            self.update_action(4)
            self.frame_index = len(self.animation_list[4]) - 1
            self.shield_used = False
            self.block_duration = 0
            return True
        return False

    def release_block(self):
        if self.blocking:
            self.blocking = False
            self.shield_cooldown = self.block_release_cooldown
            self.update_action(0)

    def take_damage(self, amount, knockback_direction):
        if self.alive and self.invulnerable_timer == 0:
            if not (self.blocking and self.is_facing_player()):
                self.health -= amount
                self.flash_timer = 30
                self.update_action(0)
                self.invulnerable_timer = self.invulnerable_duration
                self.knockback_velocity = knockback_direction * 15
            else:
                self.knockback_velocity = knockback_direction * 5
            
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(3)
                if not self.death_penalty_applied:
                    self.total_reward -= 100
                    self.death_penalty_applied = True

    def check_melee_hit(self, player):
        if (self.attacking and not self.attack_landed and self.is_facing_player() and
            abs(self.rect.centerx - player.rect.centerx) < self.attack_range and
            abs(self.rect.centery - player.rect.centery) < 50):
            knockback_direction = 1 if self.direction > 0 else -1
            player.take_damage(10, knockback_direction)
            self.attack_landed = True
            self.hit_player = True
            if not player.alive:
                self.killed_player = True
            return True
        return False

    def get_reward(self):
        reward = 0
        if self.hit_player:
            reward += 30
            if self.killed_player:
                reward += 50
        if self.health < self.previous_health:
            reward -= 20
        if self.blocking and self.shield_used and self.is_facing_player():
            reward += 30
        if self.health == 0 and not self.death_penalty_applied:
            reward -= 50
            self.death_penalty_applied = True

        self.previous_health = self.health
        return reward

    def update(self, player, tile_map):
        super().update(tile_map)
        self.update_animation()
        self.hit_player = False
        self.killed_player = False
        self.update_animation()

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.flash_timer > 0:
            self.flash_timer -= 1
        if self.shield_cooldown > 0:
            self.shield_cooldown -= 1
        
        if self.alive:
            current_state = self.get_state(player)
            action = self.sarsa.get_action(current_state)
            self.act(action, player, tile_map)
            self.check_melee_hit(player)
            self.previous_state = current_state
            self.previous_action = action
            self.episode_steps += 1

        # Attack animation progression
        if self.attacking:
            self.attack_frame += 0.5
            if self.attack_frame >= len(self.animation_list[1]):
                self.attacking = False
                self.attack_frame = 0

        # Block logic
        if self.blocking:
            if self.block_duration < self.max_block_duration and self.is_facing_player():
                self.block_duration += 1
            else:
                self.release_block()

        # Apply knockback
        if self.knockback_velocity != 0:
            self.rect.x += int(self.knockback_velocity)
            self.knockback_velocity *= self.knockback_decay
            if abs(self.knockback_velocity) < 0.1:
                self.knockback_velocity = 0
        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        max_frames = len(self.animation_list[self.action])
        
        if self.blocking:
            # Always stay at the last frame of block
            self.frame_index = max_frames - 1
        else:
            if self.attacking:
                self.frame_index = int(min(self.attack_frame, max_frames - 1))
            elif pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
                self.update_time = pygame.time.get_ticks()
                self.frame_index += 1
                if self.frame_index >= max_frames:
                    if self.action == 3:  # Death
                        self.frame_index = max_frames - 1
                    elif self.action in [1, 4]:  # Attack or Block
                        self.frame_index = 0
                        self.update_action(0)
                    else:
                        self.frame_index = 0

        self.frame_index = int(min(self.frame_index, max_frames - 1))
        self.image = self.animation_list[self.action][self.frame_index]
        if self.direction == -1:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if self.flash_timer > 0 and self.flash_timer % 4 < 2:
            self.image = self.image.copy()
            self.image.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)

    def update_action(self, new_action):
        if new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def reset(self):
        self.health = self.max_health
        self.previous_health = self.health
        self.rect.x = 500
        self.rect.y = SCREEN_HEIGHT - 200
        self.alive = True
        self.action = 0
        self.frame_index = 0
        self.attacking = False
        self.blocking = False
        self.attack_frame = 0
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.episode_steps = 0
        self.total_reward = 0
        self.previous_state = None
        self.previous_action = None
        self.invulnerable_timer = 0
        self.death_penalty_applied = False
        self.shield_used = False
        self.attack_landed = False
        self.shield_cooldown = 0
        self.just_attacked = False
        self.block_duration = 0
        self.player = None
        self.hit_player = False
        self.killed_player = False

    def end_episode(self):
        self.sarsa.end_episode()
        self.episode_steps = 0
        self.total_reward = 0
