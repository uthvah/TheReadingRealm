import os
import random
import math
import pygame
from os import listdir
from os.path import isfile, join

# Initialize Pygame and set the display mode early
pygame.init()
WIDTH, HEIGHT = 1000, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Reading Realm")
FPS = 60

# Game parameters
PLAYER_VEL = 5
GRAVITY = 1
JUMP_STRENGTH = -16  # Increased jump power for higher jumps
LEVEL_LENGTH = 8000  # Distance to reach to win
TIME_LIMIT = 300     # seconds

# Camera smoothing factor (0 < alpha <= 1)
CAMERA_ALPHA = 0.1

# Colors
COLORS = {
    "SKY_BLUE": (135, 206, 235),
    "CLOUD_WHITE": (255, 255, 255),
    "DARK_BLUE": (0, 105, 148),
    "GOLD": (255, 215, 0),
    "RED": (255, 0, 0),
    "GREEN": (34, 139, 34),
    "BLACK": (0, 0, 0)
}

# Fonts
def load_font(filename, size):
    return pygame.font.Font(join("assets", filename), size)

FONTS = {
    "title": load_font("gallery.regular.ttf", 100),
    "menu": load_font("VT323-Regular.ttf", 50),
    "level": load_font("VT323-Regular.ttf", 100),
    "score": load_font("VT323-Regular.ttf", 36)
}

# Background: load image and create tiles; also support parallax (with factor < 1)
def get_background(name):
    image = pygame.image.load(join("assets", "Background", name)).convert()
    _, _, img_width, img_height = image.get_rect()
    tiles = [(i * img_width, j * img_height)
             for i in range(WIDTH // img_width + 2)
             for j in range(HEIGHT // img_height + 2)]
    return tiles, image

# Utility for flipping sprites horizontally
def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]

# Load sprite sheets from a folder
def load_sprite_sheets(dir1, dir2, width, height, direction=False, frame_counts=None):
    path = join("assets", dir1, dir2)
    images = [f for f in listdir(path) if isfile(join(path, f))]
    all_sprites = {}
    for image in images:
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()
        total_frames = sprite_sheet.get_width() // width
        base_name = image.replace(".png", "")
        desired_frames = frame_counts.get(base_name, total_frames) if frame_counts else total_frames
        sprites = []
        for i in range(min(total_frames, desired_frames)):
            surface = pygame.Surface((width, height), pygame.SRCALPHA)
            rect = pygame.Rect(i * width, 0, width, height)
            surface.blit(sprite_sheet, (0, 0), rect)
            sprites.append(pygame.transform.scale2x(surface))
        if direction:
            all_sprites[base_name + "_right"] = sprites
            all_sprites[base_name + "_left"] = flip(sprites)
        else:
            all_sprites[base_name] = sprites
    return all_sprites

def get_block(size):
    path = join("assets", "Terrain", "Terrain.png")
    image = pygame.image.load(path).convert_alpha()
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = pygame.Rect(96, 0, size, size)
    surface.blit(image, (0, 0), rect)
    return pygame.transform.scale2x(surface)

# Additional obstacle: Spike
class Spike(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.image.load(r"D:\projects\TheReadingRealm\assets\Traps\Spikes\Idle.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (width, height))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
    
    def draw(self, surface, offset_x):
        surface.blit(self.image, (self.rect.x - offset_x, self.rect.y))

# Additional obstacle: Trophy (end checkpoint)
class Trophy(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height):
        super().__init__()
        self.image = pygame.image.load(r"D:\projects\TheReadingRealm\assets\Items\Checkpoints\End\End (Idle).png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (width, height))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
    
    def draw(self, surface, offset_x):
        surface.blit(self.image, (self.rect.x - offset_x, self.rect.y))

# Cloud for parallax background decoration
class Cloud(pygame.sprite.Sprite):
    def __init__(self, x, y, speed, image_path):
        super().__init__()
        self.image = pygame.image.load(image_path).convert_alpha()
        scale = random.uniform(0.7, 1.3)
        self.image = pygame.transform.scale(self.image, 
                                             (int(self.image.get_width() * scale), int(self.image.get_height() * scale)))
        self.rect = self.image.get_rect(topleft=(x, y))
        self.speed = speed
        self.original_y = y
        self.drift_timer = random.uniform(0, 2 * math.pi)

    def update(self):
        self.rect.x -= self.speed
        self.drift_timer += 0.05
        drift_amplitude = 10
        self.rect.y = self.original_y + math.sin(self.drift_timer) * drift_amplitude
        if self.rect.right < 0:
            self.rect.x = WIDTH

def create_cloud_system(num_clouds):
    cloud_images = [
        join("assets", "cloud1.png"),
        join("assets", "cloud2.png"),
        join("assets", "cloud3.png")
    ]
    clouds = pygame.sprite.Group()
    for _ in range(num_clouds):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HEIGHT // 2)
        speed = random.uniform(0.5, 2)
        clouds.add(Cloud(x, y, speed, random.choice(cloud_images)))
    return clouds

# Player class with sprite animations
class Player(pygame.sprite.Sprite):
    SPRITES = load_sprite_sheets("MainCharacters", "MaskDude", 128, 128, direction=True)
    
    def __init__(self, x, y, width, height):
        super().__init__()
        # Use the sprite size for collision; ensure player spawns above platforms.
        self.rect = pygame.Rect(x, y, width // 2, height // 2)
        self.x_vel = 0
        self.y_vel = 0
        self.direction = "right"
        self.animation_count = 0
        self.jump_count = 0
        self.run_anim_count = 0
        self.jump_anim_count = 0
        self.fall_anim_count = 0
        self.last_x = self.rect.x
        self.movement_threshold = 2
        self.hit = False
        self.hit_count = 0
        self.sprite = None

    def jump(self):
        # Only trigger jump when key is pressed and jump_count allows
        if self.jump_count < 2:
            self.y_vel = JUMP_STRENGTH
            self.jump_count += 1
            self.jump_anim_count = 0
            self.fall_anim_count = 0

    def move_left(self):
        self.x_vel = -PLAYER_VEL
        if self.direction != "left":
            self.direction = "left"
            self.run_anim_count = 0

    def move_right(self):
        self.x_vel = PLAYER_VEL
        if self.direction != "right":
            self.direction = "right"
            self.run_anim_count = 0

    def update_sprite(self):
        is_moving = abs(self.rect.x - self.last_x) > self.movement_threshold
        self.last_x = self.rect.x
        if self.hit:
            anim = "hit"
            count = self.animation_count
        elif self.jump_count > 0:
            if self.y_vel < 0:
                anim = "jump"
                self.jump_anim_count += 1
                count = self.jump_anim_count
            else:
                anim = "fall"
                self.fall_anim_count += 1
                count = self.fall_anim_count
        elif is_moving:
            anim = "run"
            self.run_anim_count += 1
            count = self.run_anim_count
        else:
            anim = "idle"
            count = self.animation_count

        frame_index = (count // 5) % len(self.SPRITES.get(anim + "_" + self.direction,
                                                           self.SPRITES["idle_" + self.direction]))
        self.sprite = self.SPRITES[anim + "_" + self.direction][frame_index]
        self.animation_count += 1
        self.update_rect_and_mask()

    def update_rect_and_mask(self):
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    def apply_gravity(self):
        self.y_vel += GRAVITY
        self.rect.y += self.y_vel

    def update(self):
        self.rect.x += self.x_vel
        self.apply_gravity()
        self.update_sprite()
        self.x_vel = 0

    def landed(self):
        self.y_vel = 0
        self.jump_count = 0
        self.fall_anim_count = 0
        self.jump_anim_count = 0
        self.animation_count = 0

    def hit_head(self):
        self.y_vel = abs(self.y_vel)

    def draw(self, surface, offset_x):
        surface.blit(self.sprite, (self.rect.x - offset_x, self.rect.y))

# Base class for platforms and other objects
class Object(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.name = name

    def draw(self, surface, offset_x):
        surface.blit(self.image, (self.rect.x - offset_x, self.rect.y))

# Platform block
class Block(Object):
    def __init__(self, x, y, size):
        super().__init__(x, y, size, size)
        block_image = get_block(size)
        self.image.blit(block_image, (0, 0))
        self.mask = pygame.mask.from_surface(self.image)

# Procedural level generation with landmarks and varied gaps
def generate_procedural_level(block_size):
    platforms = []
    x = 0
    # Start the platform somewhere in the lower third of the screen.
    y = HEIGHT - block_size * 3  
    landmark_interval = 800  # Every 800 pixels, add a landmark cluster.
    next_landmark = landmark_interval

    while x < LEVEL_LENGTH:
        if x >= next_landmark:
            # Landmark cluster: create a block formation (e.g. a small tower or wider platform)
            cluster_width = random.randint(2, 4) * block_size
            for i in range(3):  # Create a 3-row landmark
                for j in range(cluster_width // block_size):
                    platforms.append(Block(x + j * block_size, y - i * block_size, block_size))
            x += cluster_width + random.randint(block_size // 2, block_size)
            next_landmark += landmark_interval
            # Slight vertical adjustment
            y = max(HEIGHT // 2, min(HEIGHT - block_size, y + random.randint(-block_size, block_size)))
        else:
            platforms.append(Block(x, y, block_size))
            gap = random.randint(block_size // 2, block_size + x // 200)
            x += block_size + gap
            y_change = random.randint(-block_size // 2, block_size // 2)
            y = max(HEIGHT // 2, min(HEIGHT - block_size, y + y_change))
    return platforms

# Draw function: background with parallax, clouds, objects, player, score and timer
def draw(window, background_tiles, bg_image, player, objects, offset_x, score, timer):
    window.fill(COLORS["SKY_BLUE"])
    # Draw background layer with parallax factor (e.g., move slower than foreground)
    parallax_offset = offset_x * 0.5
    for tile in background_tiles:
        window.blit(bg_image, (tile[0] - parallax_offset, tile[1]))
    # Draw all objects and player
    for obj in objects:
        obj.draw(window, offset_x)
    player.draw(window, offset_x)
    score_text = FONTS["score"].render(f"Score: {score}", True, COLORS["BLACK"])
    time_text = FONTS["score"].render(f"Time: {timer}", True, COLORS["BLACK"])
    window.blit(score_text, (10, 10))
    window.blit(time_text, (10, 50))
    pygame.display.update()

# Main Game class
class Game:
    def __init__(self):
        self.window = screen
        self.clock = pygame.time.Clock()
        self.background_tiles, self.bg_image = get_background("Blue.png")
        self.clouds = create_cloud_system(5)
        self.platforms = generate_procedural_level(96)
        self.objects = []
        self.objects.extend(self.platforms)
        self.spikes = []
        # Place spikes on some platforms (after 1/3 of level) for challenge
        for plat in self.platforms:
            if plat.rect.x > LEVEL_LENGTH * 0.33 and random.random() < 0.2:
                spike = Spike(plat.rect.x + random.randint(0, plat.rect.width - 20),
                              plat.rect.y - 20, 20, 20)
                self.spikes.append(spike)
        self.objects.extend(self.spikes)
        # Place trophy on the last platform as the win checkpoint
        if self.platforms:
            last_plat = self.platforms[-1]
            self.trophy = Trophy(last_plat.rect.x + last_plat.rect.width // 2,
                                  last_plat.rect.y - 80, 40, 80)
            self.objects.append(self.trophy)
        else:
            self.trophy = None

    def main_menu(self):
        menu_options = ["Start Game", "Quit"]
        selected = 0
        while True:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(menu_options)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(menu_options)
                    elif event.key == pygame.K_RETURN:
                        if menu_options[selected] == "Start Game":
                            return "start"
                        elif menu_options[selected] == "Quit":
                            return "quit"
            self.window.fill(COLORS["SKY_BLUE"])
            self.clouds.update()
            self.clouds.draw(self.window)
            # Render title with a subtle shadow for depth
            title_lines = ["The", "Reading", "Realm"]
            for i, line in enumerate(title_lines):
                shadow = FONTS["title"].render(line, True, (100, 100, 100))
                text = FONTS["title"].render(line, True, COLORS["DARK_BLUE"])
                shadow_rect = shadow.get_rect(center=(WIDTH//2 + 3, HEIGHT//2 - 150 + i*100 + 3))
                text_rect = text.get_rect(center=(WIDTH//2, HEIGHT//2 - 150 + i*100))
                self.window.blit(shadow, shadow_rect)
                self.window.blit(text, text_rect)
            # Render menu options
            for i, option in enumerate(menu_options):
                color = COLORS["GOLD"] if i == selected else COLORS["CLOUD_WHITE"]
                opt_text = FONTS["menu"].render(option, True, color)
                opt_rect = opt_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 150 + i*60))
                self.window.blit(opt_text, opt_rect)
            pygame.display.update()

    def main_game(self):
        # Spawn player on top of the first platform to avoid falling immediately.
        if self.platforms:
            start_y = self.platforms[0].rect.top - 50
        else:
            start_y = HEIGHT - 150
        player = Player(100, start_y, 50, 50)
        start_time = pygame.time.get_ticks()
        score = 0
        offset_x = 0

        game_over = False
        victory = False
        bonus_awarded = False

        while True:
            self.clock.tick(FPS)
            current_time = (pygame.time.get_ticks() - start_time) // 1000

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        player.jump()

            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player.move_left()
            elif keys[pygame.K_RIGHT]:
                player.move_right()

            player.update()

            # Collision with platforms: allow landing only if falling (no auto jump)
            for plat in self.platforms:
                if pygame.sprite.collide_mask(player, plat) and player.y_vel > 0:
                    player.rect.bottom = plat.rect.top
                    player.landed()

            # Collision with spikes (game over)
            for spike in self.spikes:
                if pygame.sprite.collide_mask(player, spike):
                    game_over = True

            # Collision with trophy (victory)
            if self.trophy and pygame.sprite.collide_mask(player, self.trophy):
                victory = True
                if not bonus_awarded:
                    bonus = max(0, (TIME_LIMIT - current_time)) * 10
                    score += bonus
                    bonus_awarded = True

            # Update score based on player's horizontal progress
            score = max(score, int((player.rect.x / LEVEL_LENGTH) * 1000))
            # Lose condition: player falls or time runs out
            if player.rect.top > HEIGHT or current_time > TIME_LIMIT:
                game_over = True
            # Victory condition: reaching near the trophy or end of level
            if player.rect.x >= LEVEL_LENGTH:
                victory = True
                if not bonus_awarded:
                    bonus = max(0, (TIME_LIMIT - current_time)) * 10
                    score += bonus
                    bonus_awarded = True

            # Smooth camera: target offset centers player horizontally around WIDTH/3.
            target_offset = player.rect.centerx - WIDTH/3
            offset_x += (target_offset - offset_x) * CAMERA_ALPHA

            self.clouds.update()
            draw(self.window, self.background_tiles, self.bg_image, player, self.objects, offset_x, score, current_time)

            # Overlay win/lose screen if game ends
            if game_over or victory:
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 180))
                self.window.blit(overlay, (0, 0))
                if game_over:
                    msg = FONTS["level"].render("GAME OVER", True, COLORS["RED"])
                else:
                    msg = FONTS["level"].render("VICTORY!", True, COLORS["GOLD"])
                msg_rect = msg.get_rect(center=(WIDTH//2, HEIGHT//2 - 50))
                instr = FONTS["menu"].render("R - Restart   ESC - Quit", True, COLORS["BLACK"])
                instr_rect = instr.get_rect(center=(WIDTH//2, HEIGHT//2 + 50))
                self.window.blit(msg, msg_rect)
                self.window.blit(instr, instr_rect)
                pygame.display.update()
                waiting = True
                while waiting:
                    self.clock.tick(FPS)
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            return "quit"
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_r:
                                return self.main_game()
                            if event.key == pygame.K_ESCAPE:
                                return "quit"

    def run(self):
        while True:
            choice = self.main_menu()
            if choice == "start":
                result = self.main_game()
                if result == "quit":
                    break
            else:
                break
        pygame.quit()

if __name__ == "__main__":
    Game().run()
