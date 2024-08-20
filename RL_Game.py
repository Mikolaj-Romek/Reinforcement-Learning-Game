import pygame
import random
import os
import time
import math

# Initialize Pygame
pygame.init()

# Screen setup
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("RL Game")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Game variables
FPS = 60
GRAVITY = 0.8
JUMP_STRENGTH = -15

class Character(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.rect = pygame.Rect(x, y, 30, 50)
        self.vel_y = 0
        self.jumping = False
        self.falling = False

    def move(self, dx):
        self.rect.x += dx

    def jump(self):
        if not self.jumping and not self.falling:
            self.vel_y = JUMP_STRENGTH
            self.jumping = True
            return True
        return False

    def update(self):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        if self.rect.bottom > SCREEN_HEIGHT - 50:  # Floor collision
            self.rect.bottom = SCREEN_HEIGHT - 50
            self.jumping = False
            self.falling = False
            self.vel_y = 0

class Player(Character):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.health = 100
        self.max_health = self.health
        self.speed = 5
        self.animation_list = []
        self.action = 0  # 0: Idle, 1: Run, 2: Jump, 3: Death, 4: Attack, 5: Fall, 6: Hurt
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.attacking = False
        self.attack_cooldown = 0
        self.facing_right = True
        self.alive = True
        self.hit_timer = 0
        self.knockback_speed = 0
        animation_types = ["Idle", "Run", "Jump", "Death", "Attack", "Fall", "Hurt"]
        for animation in animation_types:
            temp_list = []
            num_of_frames = len(os.listdir(f"img/player/{animation}"))
            for i in range(num_of_frames):
                img = pygame.image.load(f"img/player/{animation}/{i}.png").convert_alpha()
                img = pygame.transform.scale(img, (int(img.get_width() * 2), int(img.get_height() * 2)))
                temp_list.append(img)
            self.animation_list.append(temp_list)
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y)

    def update(self):
        if self.alive:
            super().update()
            self.update_animation()
            if self.attack_cooldown > 0:
                self.attack_cooldown -= 1
            
            if self.hit_timer > 0:
                self.hit_timer -= 1
                self.rect.x += self.knockback_speed
                self.knockback_speed *= 0.9  # Decelerate the knockback
            
            if not self.jumping and not self.falling and self.hit_timer == 0:
                if self.action in [2, 5, 6]:  # If was jumping, falling, or hurt
                    self.update_action(0)  # Set to Idle when landing or recovering
            elif self.vel_y > 0 and not self.falling:
                self.falling = True
                self.update_action(5)  # Set to Fall animation
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
            if self.action == 4:  # Attack animation finished
                self.attacking = False
                self.update_action(0)  # Set to Idle after attack
            elif self.action in [2, 5]:  # For jump and fall animations, stay on last frame
                self.frame_index = len(self.animation_list[self.action]) - 1
            elif self.action == 6:  # Hurt animation finished
                self.update_action(0)  # Set to Idle after hurt
            else:
                self.frame_index = 0

    def update_death_animation(self):
        ANIMATION_COOLDOWN = 150  # Slower animation for death
        self.image = self.animation_list[3][self.frame_index]  # 3 is the index for Death animation
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        
        if pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            if self.frame_index < len(self.animation_list[3]) - 1:
                self.frame_index += 1

    def move(self, dx):
        if self.alive and not self.attacking and self.hit_timer == 0:  # Only move if alive and not attacking or hurt
            super().move(dx)
            if dx != 0:
                self.facing_right = dx > 0
                if not self.jumping and not self.falling:
                    self.update_action(1)  # Set to Run animation only if on the ground
            elif not self.jumping and not self.falling:
                self.update_action(0)  # Set to Idle animation if on the ground and not moving

    def jump(self):
        if self.alive and super().jump():
            self.update_action(2)  # Set to Jump animation
            return True
        return False

    def attack(self):
        if self.alive and self.attack_cooldown == 0 and not self.attacking and not self.jumping and not self.falling and self.hit_timer == 0:
            self.attacking = True
            self.attack_cooldown = 20
            self.update_action(4)  # Set to Attack animation
            return True
        return False

    def update_action(self, new_action):
        if self.alive and new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def take_damage(self, amount, knockback_direction):
        if self.alive:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(3)  # Set to Death animation
                self.frame_index = 0  # Start death animation from the beginning
            else:
                self.hit_timer = 30  # 0.5 seconds at 60 FPS
                self.knockback_speed = knockback_direction * 5  # Adjust for desired knockback strength
                self.update_action(6)  # Set to Hurt animation
                self.attacking = False  # Reset attacking state when hit
                self.attack_cooldown = 0  # Reset attack cooldown when hit

class Arrow(pygame.sprite.Sprite):
    def __init__(self, x, y, direction):
        super().__init__()
        self.image = pygame.image.load("img/archer/arrow/0.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (int(self.image.get_width() * 1.5), int(self.image.get_height() * 1.5)))
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
            
            # Rotate arrow based on trajectory
            self.angle = -math.atan2(self.vel_y, self.speed * self.direction)
            rotated_image = pygame.transform.rotate(pygame.image.load("img/archer/arrow/0.png").convert_alpha(), math.degrees(self.angle))
            self.image = pygame.transform.scale(rotated_image, (int(rotated_image.get_width() * 1.5), int(rotated_image.get_height() * 1.5)))

            # Check if arrow hits the ground
            if self.rect.bottom >= SCREEN_HEIGHT - 60:
                self.rect.bottom = SCREEN_HEIGHT - 60
                self.stopped = True

        # Remove arrow if it goes off-screen horizontally
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()

class Enemy(Character):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.health = 50
        self.max_health = self.health
        self.speed = 2
        self.direction = 1
        self.animation_list = []
        self.action = 0  # 0: Idle, 1: Run, 2: Jump, 3: Death, 4: Attack
        self.frame_index = 0
        self.update_time = pygame.time.get_ticks()
        self.alive = True
        self.jump_timer = time.time()
        self.death_timer = time.time()
        self.jump_height = 10
        self.vertical_offset = 24
        self.hit_timer = 0
        self.knockback_speed = 0
        self.flash_timer = 0
        self.attack_cooldown = 0
        self.arrow_group = pygame.sprite.Group()
        self.attacking = False
        self.attack_frame = 0
        animation_types = ["Idle", "Run", "Jump", "Death", "Attack"]
        for animation in animation_types:
            temp_list = []
            num_of_frames = len(os.listdir(f"img/archer/{animation}"))
            for i in range(num_of_frames):
                img = pygame.image.load(f"img/archer/{animation}/{i}.png").convert_alpha()
                img = pygame.transform.scale(img, (int(img.get_width() * 1.5), int(img.get_height() * 1.5)))
                temp_list.append(img)
            self.animation_list.append(temp_list)
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.midbottom = (x, y + self.vertical_offset)

    def move_ai(self):
        if self.alive and self.hit_timer == 0 and not self.attacking:
            self.rect.x += self.direction * self.speed
            if self.rect.left < 0 or self.rect.right > SCREEN_WIDTH:
                self.direction *= -1
            self.update_action(1)  # Set to Run animation
        self.rect.bottom = SCREEN_HEIGHT - 50 + self.vertical_offset  # Ensure it stays on the ground

    def update(self):
        super().update()
        self.update_animation()
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        if self.hit_timer > 0:
            self.hit_timer -= 1
            self.rect.x += self.knockback_speed
            self.knockback_speed *= 0.9  # Decelerate the knockback
        elif self.alive:
            if self.attack_cooldown == 0:
                self.attack()
            elif not self.attacking:
                self.move_ai()

        if self.flash_timer > 0:
            self.flash_timer -= 1

        if self.attacking:
            self.attack_frame += 1
            if self.attack_frame >= len(self.animation_list[4]):  # If attack animation is finished
                self.attacking = False
                self.attack_frame = 0
                self.shoot_arrow()

        # Ensure the enemy stays on the ground
        self.rect.bottom = SCREEN_HEIGHT - 50 + self.vertical_offset

        # Update arrows
        self.arrow_group.update()

    def update_animation(self):
        ANIMATION_COOLDOWN = 100
        max_frames = len(self.animation_list[self.action])
        self.frame_index = min(self.frame_index, max_frames - 1)
        
        self.image = self.animation_list[self.action][self.frame_index]
        if self.direction == -1:
            self.image = pygame.transform.flip(self.image, True, False)
        
        # Flash effect
        if self.flash_timer > 0 and self.flash_timer % 4 < 2:  # Flash every other frame
            self.image = self.image.copy()
            self.image.fill((255, 255, 255, 128), special_flags=pygame.BLEND_RGBA_MULT)
        
        if self.attacking:
            self.frame_index = self.attack_frame
        elif pygame.time.get_ticks() - self.update_time > ANIMATION_COOLDOWN:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
            if self.frame_index >= max_frames:
                if self.action == 3:  # Death animation
                    self.frame_index = max_frames - 1
                elif self.action == 4:  # Attack animation
                    self.frame_index = 0
                    self.update_action(0)  # Return to Idle after attack
                elif self.action == 2:  # Jump animation
                    self.falling = True
                    self.jumping = False
                    self.frame_index = max_frames - 1  # Stay on last frame of jump
                else:
                    self.frame_index = 0

    def attack(self):
        if self.attack_cooldown == 0 and self.alive and not self.attacking:
            self.attacking = True
            self.attack_frame = 0
            self.attack_cooldown = 180  # 3 seconds cooldown (60 FPS * 3)
            self.update_action(4)  # Set to Attack animation

    def shoot_arrow(self):
        arrow_x = self.rect.centerx + (50 * self.direction)
        arrow_y = self.rect.centery + 10
        new_arrow = Arrow(arrow_x, arrow_y, self.direction)
        self.arrow_group.add(new_arrow)

    def take_damage(self, amount, knockback_direction):
        if self.alive:
            self.health -= amount
            self.hit_timer = 60  # 1 second at 60 FPS
            self.knockback_speed = knockback_direction * 5  # Adjust for desired knockback strength
            self.flash_timer = 30  # Flash for half a second
            self.update_action(0)  # Set to Idle animation
            if self.health <= 0:
                self.health = 0
                self.alive = False
                self.update_action(3)  # Set to Death animation

    def update_action(self, new_action):
        if new_action != self.action:
            self.action = new_action
            self.frame_index = 0
            self.update_time = pygame.time.get_ticks()

    def draw_arrows(self, surface):
        self.arrow_group.draw(surface)

# Create sprites
player = Player(100, SCREEN_HEIGHT - 50)
enemy = Enemy(700, SCREEN_HEIGHT - 50 - 10)

all_sprites = pygame.sprite.Group(player, enemy)

# Game loop
clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if player.attack():
                    # Check if enemy is in range and apply damage
                    if abs(player.rect.centerx - enemy.rect.centerx) < 75:  # Increased attack range
                        knockback_direction = 1 if player.facing_right else -1
                        enemy.take_damage(5, knockback_direction)
            if event.key == pygame.K_UP:
                player.jump()

    # Player movement
    keys = pygame.key.get_pressed()
    dx = 0
    if player.alive:
        if keys[pygame.K_LEFT]:
            dx = -player.speed
        if keys[pygame.K_RIGHT]:
            dx = player.speed
    player.move(dx)

    # Update
    all_sprites.update()
    enemy.arrow_group.update()

    # Check for arrow collisions with player
    for arrow in enemy.arrow_group:
        if player.alive and not arrow.stopped and arrow.rect.colliderect(player.rect):
            knockback_direction = 1 if arrow.direction > 0 else -1
            player.take_damage(5, knockback_direction)
            arrow.kill()

    # Draw
    screen.fill(WHITE)
    pygame.draw.rect(screen, BLACK, (0, SCREEN_HEIGHT - 50, SCREEN_WIDTH, 50))  # Floor
    all_sprites.draw(screen)
    enemy.draw_arrows(screen)
    
    

    # Draw enemy health only if alive
    if enemy.alive:
        pygame.draw.rect(screen, RED, (enemy.rect.x + 20, enemy.rect.y - 20, 50, 5))
        pygame.draw.rect(screen, GREEN, (enemy.rect.x + 20, enemy.rect.y - 20, 50 * (enemy.health / enemy.max_health), 5))

    # Draw player health
    pygame.draw.rect(screen, RED, (player.rect.x + 20, player.rect.y - 20, 50, 5))
    pygame.draw.rect(screen, GREEN, (player.rect.x + 20, player.rect.y - 20, 50 * (player.health / player.max_health), 5))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()