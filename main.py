import pygame

from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    WHITE, BLACK, RED, GREEN, BLUE,
    FPS
)
from tilemap import TileMap
from characters import Player
from enemies import Enemy
from knight import Knight
from bird import Bird

def main():
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("RL Game")
    clock = pygame.time.Clock()

    tile_map = TileMap()
    player = Player(250, SCREEN_HEIGHT - 100)
    enemy = Enemy(500, SCREEN_HEIGHT - 100)
    knight = Knight(700, SCREEN_HEIGHT - 100)
    bird = Bird(400, SCREEN_HEIGHT - 150)
    
    all_sprites = pygame.sprite.Group(player, enemy, knight, bird)
    bird.sarsa.epsilon = 0
    enemy.sarsa.epsilon = 0
    knight.sarsa.epsilon = 0

    running = True
    while running:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    player.jump()
                if event.key == pygame.K_SPACE:
                    player.attack()

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.move(-player.speed, tile_map)
        if keys[pygame.K_RIGHT]:
            player.move(player.speed, tile_map)

        # Update
        player.update(tile_map)
        enemy.update(player, tile_map)
        knight.update(player, tile_map)
        bird.update(player, enemy, knight)

        # Collisions: player vs. enemy arrows
        for arrow in enemy.arrow_group:
            if pygame.sprite.collide_rect(arrow, player):
                player.take_damage(5, 1 if arrow.direction > 0 else -1)
                arrow.kill()

        # Check if player's attack hits enemy or knight
        if player.attacking and not player.has_hit_enemy:
            if (abs(player.rect.centerx - enemy.rect.centerx) < player.attack_range and
                abs(player.rect.centery - enemy.rect.centery) < 50):
                knockback_direction = 1 if player.facing_right else -1
                enemy.take_damage(10, knockback_direction)
                player.has_hit_enemy = True
            elif (abs(player.rect.centerx - knight.rect.centerx) < player.attack_range and
                  abs(player.rect.centery - knight.rect.centery) < 50):
                knockback_direction = 1 if player.facing_right else -1
                knight.take_damage(10, knockback_direction)
                player.has_hit_enemy = True

        # Check if knight's attack hits player
        if knight.attacking and not knight.attack_landed:
            if (abs(knight.rect.centerx - player.rect.centerx) < knight.attack_range and
                abs(knight.rect.centery - player.rect.centery) < 50):
                knockback_direction = 1 if knight.direction > 0 else -1
                player.take_damage(10, knockback_direction)
                knight.attack_landed = True

        screen.fill(WHITE)
        tile_map.draw(screen)
        all_sprites.draw(screen)
        enemy.draw_arrows(screen)
        bird.draw_shield(screen, player)

        # Health bars
        pygame.draw.rect(screen, RED,   (player.rect.x, player.rect.y - 20, player.rect.width, 5))
        pygame.draw.rect(screen, GREEN, (
            player.rect.x, player.rect.y - 20,
            player.rect.width * player.health / player.max_health,
            5
        ))

        pygame.draw.rect(screen, RED,   (enemy.rect.x, enemy.rect.y - 20, enemy.rect.width, 5))
        pygame.draw.rect(screen, GREEN, (
            enemy.rect.x, enemy.rect.y - 20,
            enemy.rect.width * enemy.health / enemy.max_health,
            5
        ))

        pygame.draw.rect(screen, RED,   (knight.rect.x, knight.rect.y - 20, knight.rect.width, 5))
        pygame.draw.rect(screen, GREEN, (
            knight.rect.x, knight.rect.y - 20,
            knight.rect.width * knight.health / knight.max_health,
            5
        ))

        # Info text
        font = pygame.font.Font(None, 24)
        player_health_text = font.render(f"Player Health: {player.health}", True, BLACK)
        enemy_health_text  = font.render(f"Enemy Health: {enemy.health}",   True, BLACK)
        knight_health_text = font.render(f"Knight Health: {knight.health}", True, BLACK)
        
        screen.blit(player_health_text, (10, 10))
        screen.blit(enemy_health_text,  (10, 40))
        screen.blit(knight_health_text, (10, 70))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
