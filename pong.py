import os
import sys
import pygame
import random
from moviepy.editor import VideoFileClip

# Initialize Pygame
pygame.init()

# Set up the game window
WIDTH, HEIGHT = 1280, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pong")

# Determine base path for assets
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

# Load assets
blip_sound = pygame.mixer.Sound(os.path.join(base_path, "retro_blip.mp3"))
startup_sound = pygame.mixer.Sound(os.path.join(base_path, "ele_fade.wav"))
retro_shot_sound = pygame.mixer.Sound(os.path.join(base_path, "retro_shot.mp3"))

# Paddles and ball
paddle_width, paddle_height = 20, 100
ball_width = 15
paddle_speed = 10
ball_speed_x, ball_speed_y = 4, 4

left_paddle = pygame.Rect(30, HEIGHT // 2 - paddle_height // 2, paddle_width, paddle_height)
right_paddle = pygame.Rect(WIDTH - 30 - paddle_width, HEIGHT // 2 - paddle_height // 2, paddle_width, paddle_height)
ball = pygame.Rect(WIDTH // 2 - ball_width // 2, HEIGHT // 2 - ball_width // 2, ball_width, ball_width)

# For blue power-up: store original paddle height and the bonus height.
left_paddle_original_height = paddle_height
right_paddle_original_height = paddle_height
blue_paddle_height = 150  # new height when blue power-up is active

# Volume Settings
volume_level = 100  # Default volume (100%)
pygame.mixer.music.set_volume(volume_level / 100.0)

# Score
left_score = 0
right_score = 0

# Font
pygame.font.init()
font = pygame.font.Font(None, 72)
small_font = pygame.font.Font(None, 50)

def draw_text(text, x, y, font=font):
    """Helper function to render text."""
    text_surface = font.render(text, True, (255, 255, 255))
    screen.blit(text_surface, (x, y))

def draw_volume_slider(volume):
    """Draws a volume slider."""
    slider_x = WIDTH // 2 - 150
    slider_y = HEIGHT // 2 + 50
    slider_width = 300
    slider_height = 10
    pygame.draw.rect(screen, (100, 100, 100), (slider_x, slider_y, slider_width, slider_height))
    fill_width = int((volume / 100) * slider_width)
    pygame.draw.rect(screen, (255, 255, 255), (slider_x, slider_y, fill_width, slider_height))
    draw_text(f"Volume: {volume}%", WIDTH // 2 - 100, slider_y + 20, small_font)

def main_menu():
    """Displays the main menu with a volume slider."""
    global volume_level
    while True:
        screen.fill((0, 0, 0))
        draw_text("PONG", WIDTH // 2 - 100, HEIGHT // 4)
        draw_text("1. Play", WIDTH // 2 - 100, HEIGHT // 2 - 50)
        draw_text("2. Exit", WIDTH // 2 - 100, HEIGHT // 2)
        draw_volume_slider(volume_level)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return
                elif event.key == pygame.K_2:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_LEFT:
                    volume_level = max(0, volume_level - 5)
                elif event.key == pygame.K_RIGHT:
                    volume_level = min(100, volume_level + 5)
                pygame.mixer.music.set_volume(volume_level / 100.0)

def game_mode_menu():
    """Displays a menu to choose between Play vs AI and Player vs Player.
       Returns the chosen mode as a string: 'ai' or 'pvp'."""
    while True:
        screen.fill((0, 0, 0))
        draw_text("Select Game Mode", WIDTH // 2 - 200, HEIGHT // 4)
        draw_text("1. Play vs AI", WIDTH // 2 - 150, HEIGHT // 2 - 50)
        draw_text("2. Player vs Player", WIDTH // 2 - 150, HEIGHT // 2)
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return "ai"
                elif event.key == pygame.K_2:
                    return "pvp"

def game_loop(mode="pvp"):
    """Runs the main game loop with two kinds of blobs and power-up effects.
       Red blob gives a double-speed hit effect (paddle turns red).
       Blue blob gives an extra-length paddle effect (paddle turns blue).
       The ball continuously accelerates the longer it's in play.
       In 'ai' mode, the right paddle is controlled by simple AI."""
    global ball, left_paddle, right_paddle, ball_speed_x, ball_speed_y, left_score, right_score

    clock = pygame.time.Clock()

    # Setup for blobs: maintain a list of blob objects.
    # Each blob is a tuple: (rect, type) where type is "red" or "blue".
    blobs = []
    # Blob dimensions: elliptical shape with width 100 and height 60.
    blob_width, blob_height = 100, 60
    last_blob_spawn_time = 0

    # Variables for tracking which paddle last hit the ball and their power-up timers.
    # Red power-up timers:
    last_hit_by = None
    left_red_power_end_time = 0
    right_red_power_end_time = 0
    # Blue power-up timers:
    left_blue_power_end_time = 0
    right_blue_power_end_time = 0

    # Set an acceleration factor per frame (adjust as desired)
    acceleration_factor = 1.0005

    while True:
        screen.fill((0, 0, 0))
        current_time = pygame.time.get_ticks()

        # Update paddle sizes based on blue power-up status.
        if current_time < left_blue_power_end_time:
            center = left_paddle.centery
            left_paddle.height = blue_paddle_height
            left_paddle.centery = center
        else:
            center = left_paddle.centery
            left_paddle.height = left_paddle_original_height
            left_paddle.centery = center

        if current_time < right_blue_power_end_time:
            center = right_paddle.centery
            right_paddle.height = blue_paddle_height
            right_paddle.centery = center
        else:
            center = right_paddle.centery
            right_paddle.height = right_paddle_original_height
            right_paddle.centery = center

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        # Spawn a new blob every 10 seconds (50% chance to spawn).
        if current_time - last_blob_spawn_time >= 10000:
            last_blob_spawn_time = current_time
            if random.random() < 0.5:
                new_rect = pygame.Rect(
                    random.randint(WIDTH//4, (WIDTH*3)//4 - blob_width),
                    random.randint(HEIGHT//4, (HEIGHT*3)//4 - blob_height),
                    blob_width,
                    blob_height
                )
                blob_type = "red" if random.random() < 0.5 else "blue"
                blobs.append((new_rect, blob_type))

        # Draw each blob and check for collision with the ball.
        for blob in blobs[:]:
            blob_rect, blob_type = blob
            if blob_type == "red":
                color = (255, 0, 0)
            else:
                color = (0, 0, 255)
            pygame.draw.ellipse(screen, color, blob_rect)
            if ball.colliderect(blob_rect):
                blobs.remove(blob)
                if last_hit_by == 'left':
                    if blob_type == "red":
                        left_red_power_end_time = current_time + 5000  # red effect: double speed hit
                    else:
                        left_blue_power_end_time = current_time + 5000  # blue effect: extra paddle length
                elif last_hit_by == 'right':
                    if blob_type == "red":
                        right_red_power_end_time = current_time + 5000
                    else:
                        right_blue_power_end_time = current_time + 5000

        # Move the ball.
        ball.x += ball_speed_x
        ball.y += ball_speed_y

        # Bounce off top and bottom.
        if ball.top <= 0 or ball.bottom >= HEIGHT:
            ball_speed_y = -ball_speed_y

        # Check collision with paddles.
        if ball.colliderect(left_paddle) and ball_speed_x < 0:
            last_hit_by = 'left'
            ball.left = left_paddle.right
            if current_time < left_red_power_end_time:
                ball_speed_x = abs(ball_speed_x) * 2
            else:
                ball_speed_x = abs(ball_speed_x)
            blip_sound.play()
        elif ball.colliderect(right_paddle) and ball_speed_x > 0:
            last_hit_by = 'right'
            ball.right = right_paddle.left
            if current_time < right_red_power_end_time:
                ball_speed_x = -abs(ball_speed_x) * 2
            else:
                ball_speed_x = -abs(ball_speed_x)
            blip_sound.play()

        # Check if ball goes out of bounds, update score and reset ball.
        if ball.left <= 0 or ball.right >= WIDTH:
            retro_shot_sound.play()
            if ball.left <= 0:
                right_score += 1
            else:
                left_score += 1
            ball.x, ball.y = WIDTH // 2 - ball_width // 2, HEIGHT // 2 - ball_width // 2
            ball_speed_x = random.choice([4, -4])
            ball_speed_y = random.choice([4, -4])
            last_hit_by = None

        # Apply continuous acceleration to the ball.
        ball_speed_x *= acceleration_factor
        ball_speed_y *= acceleration_factor

        # Paddle movement.
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w] and left_paddle.top > 0:
            left_paddle.y -= paddle_speed
        if keys[pygame.K_s] and left_paddle.bottom < HEIGHT:
            left_paddle.y += paddle_speed

        # For the right paddle, if mode is player vs player, use keys;
        # otherwise, in AI mode, simply move toward the ball.
        if mode == "pvp":
            if keys[pygame.K_UP] and right_paddle.top > 0:
                right_paddle.y -= paddle_speed
            if keys[pygame.K_DOWN] and right_paddle.bottom < HEIGHT:
                right_paddle.y += paddle_speed
        else:  # AI mode
            if ball.centery < right_paddle.centery and right_paddle.top > 0:
                right_paddle.y -= paddle_speed
            elif ball.centery > right_paddle.centery and right_paddle.bottom < HEIGHT:
                right_paddle.y += paddle_speed

        # Draw paddles, ball, and score.
        if current_time < left_blue_power_end_time:
            left_color = (0, 0, 255)
        elif current_time < left_red_power_end_time:
            left_color = (255, 0, 0)
        else:
            left_color = (255, 255, 255)

        if current_time < right_blue_power_end_time:
            right_color = (0, 0, 255)
        elif current_time < right_red_power_end_time:
            right_color = (255, 0, 0)
        else:
            right_color = (255, 255, 255)

        pygame.draw.rect(screen, left_color, left_paddle)
        pygame.draw.rect(screen, right_color, right_paddle)
        pygame.draw.ellipse(screen, (255, 255, 255), ball)

        draw_text(str(left_score), WIDTH // 4, 50)
        draw_text(str(right_score), WIDTH * 3 // 4, 50)

        pygame.display.flip()
        clock.tick(60)

def start_game():
    """Starts the game with the startup animation and sound."""
    startup_sound.play()
    startup_video_path = os.path.join(base_path, "startup.mp4")
    if os.path.exists(startup_video_path):
        clip = VideoFileClip(startup_video_path)
        clip.preview()
        clip.close()
    main_menu()
    mode = game_mode_menu()  # Choose between AI and PvP
    game_loop(mode)

if __name__ == "__main__":
    start_game()
