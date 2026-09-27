import pygame
import random
import json
import os
import math
import sys

class GameConfig:
    WINDOW_WIDTH = 800
    WINDOW_HEIGHT = 750
    HUD_HEIGHT = 150
    GRID_SIZE = 20
    GRID_COLS = 30
    GRID_ROWS = 30
    BOARD_X_OFFSET = (WINDOW_WIDTH - (GRID_COLS * GRID_SIZE)) // 2
    BOARD_Y_OFFSET = HUD_HEIGHT
    FPS = 60
    BASE_TICK_RATE = 130
    COLOR_BG = (18, 18, 20)
    COLOR_BOARD_BG = (26, 26, 30)
    COLOR_GRID_LINE = (35, 35, 42)
    COLOR_HUD_BG = (12, 12, 14)
    COLOR_DIVIDER = (93, 63, 211)
    COLOR_SNAKE_HEAD = (0, 210, 255)
    COLOR_SNAKE_BODY = (0, 160, 220)
    COLOR_FOOD = (255, 68, 68)
    COLOR_PARTICLE = (0, 210, 255)
    COLOR_OBSTACLE = (255, 0, 127)
    COLOR_TEXT_LIGHT = (240, 240, 245)
    COLOR_TEXT_MUTED = (140, 140, 150)
    COLOR_TEXT_NEON = (0, 210, 255)

class ScoreManager:
    FILE_NAME = "high_scores.json"

    def __init__(self):
        self.scores = {"map_empty": 0, "map_wall": 0, "map_hard": 0}
        self.load_scores()

    def load_scores(self):
        if os.path.exists(self.FILE_NAME):
            try:
                with open(self.FILE_NAME, 'r') as f:
                    data = json.load(f)
                    self.scores["map_empty"] = data.get("map_empty", 0)
                    self.scores["map_wall"] = data.get("map_wall", 0)
                    self.scores["map_hard"] = data.get("map_hard", 0)
            except Exception as e:
                print(f"Error loading high scores: {e}. Resetting scores.")
                self.save_scores()
        else:
            self.save_scores()

    def save_scores(self):
        try:
            with open(self.FILE_NAME, 'w') as f:
                json.dump(self.scores, f, indent=4)
        except Exception as e:
            print(f"Error saving high scores: {e}")

    def get_high_score(self, mode):
        return self.scores.get(mode, 0)

    def update_high_score(self, mode, current_score):
        if current_score > self.scores.get(mode, 0):
            self.scores[mode] = current_score
            self.save_scores()
            return True
        return False

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 6)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.06)
        self.radius = random.uniform(2, 4)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= self.decay

    def draw(self, surface):
        if self.life > 0:
            alpha = int(self.life * 255)
            glow_surf = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surf, 
                (self.color[0], self.color[1], self.color[2], alpha), 
                (self.radius * 2, self.radius * 2), 
                self.radius
            )
            surface.blit(glow_surf, (self.x - self.radius * 2, self.y - self.radius * 2))

class Snake:
    def __init__(self):
        self.reset()

    def reset(self, obstacles=None):
        if obstacles is None:
            obstacles = []
        spawn_positions = [
            [[15, 15], [14, 15], [13, 15]],
            [[5, 5], [4, 5], [3, 5]],
            [[25, 25], [24, 25], [23, 25]],
            [[15, 5], [14, 5], [13, 5]],
            [[15, 25], [14, 25], [13, 25]],
        ]
        self.body = [[15, 15], [14, 15], [13, 15]]
        for sp in spawn_positions:
            safe = True
            for seg in sp:
                if seg in obstacles:
                    safe = False
                    break
            if safe:
                self.body = [s[:] for s in sp]
                break
        self.prev_body = [pos[:] for pos in self.body]
        self.direction = [1, 0]
        self.next_direction = [1, 0]
        self.grow_pending = False

    def change_direction(self, new_dir):
        if [new_dir[0] + self.direction[0], new_dir[1] + self.direction[1]] != [0, 0]:
            self.next_direction = new_dir

    def update_logic(self):
        self.direction = self.next_direction[:]
        self.prev_body = [pos[:] for pos in self.body]
        dx, dy = self.direction
        head_x, head_y = self.body[0]
        new_head_x = (head_x + dx) % GameConfig.GRID_COLS
        new_head_y = (head_y + dy) % GameConfig.GRID_ROWS
        new_head = [new_head_x, new_head_y]
        self.body.insert(0, new_head)
        if self.grow_pending:
            self.grow_pending = False
        else:
            self.body.pop()

    def grow(self):
        self.grow_pending = True

    def check_self_collision(self):
        head = self.body[0]
        return head in self.body[1:]

    def check_obstacle_collision(self, obstacles):
        head = self.body[0]
        return head in obstacles

class Food:
    def __init__(self):
        self.position = [0, 0]

    def respawn(self, snake_body, obstacles):
        while True:
            x = random.randint(0, GameConfig.GRID_COLS - 1)
            y = random.randint(0, GameConfig.GRID_ROWS - 1)
            if [x, y] not in snake_body and [x, y] not in obstacles:
                self.position = [x, y]
                break

class GameEngine:
    STATE_MENU = 0
    STATE_PLAYING = 1
    STATE_PAUSED = 2
    STATE_GAME_OVER = 3

    MAP_NAMES = ["EMPTY FIELD", "WALL (MEDIUM)", "HARD"]
    MAP_KEYS = ["map_empty", "map_wall", "map_hard"]
    HARD_TICK_RATE = 85
    HARD_FOOD_COUNT = 3

    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.internal_width = GameConfig.WINDOW_WIDTH
        self.internal_height = GameConfig.WINDOW_HEIGHT
        self.internal_surface = pygame.Surface((self.internal_width, self.internal_height))
        self.screen = pygame.display.set_mode((self.internal_width, self.internal_height), pygame.RESIZABLE)
        pygame.display.set_caption("Gravity Snake - Wrap Edition")
        self.clock = pygame.time.Clock()
        self.score_manager = ScoreManager()
        self.snake = Snake()
        self.foods = [Food()]
        self.particles = []
        self.state = self.STATE_MENU
        
        self.map_index = 0
        self.menu_selection = 0
        self.map_dropdown_open = False
        
        self.score = 0
        self.last_tick_time = pygame.time.get_ticks()
        self.tick_interval = GameConfig.BASE_TICK_RATE
        self.pulse_timer = 0.0
        self.setup_fonts()

    def get_map_obstacles(self):
        if self.map_index == 1:
            obstacles = []
            for x in range(0, GameConfig.GRID_COLS):
                obstacles.append([x, 0])
                obstacles.append([x, GameConfig.GRID_ROWS - 1])
            for y in range(1, GameConfig.GRID_ROWS - 1):
                obstacles.append([0, y])
                obstacles.append([GameConfig.GRID_COLS - 1, y])
            return obstacles
        elif self.map_index == 2:
            obstacles = []
            for y in range(0, GameConfig.GRID_ROWS):
                obstacles.append([0, y])
                obstacles.append([GameConfig.GRID_COLS - 1, y])
            for x in range(1, GameConfig.GRID_COLS - 1):
                obstacles.append([x, 0])
                obstacles.append([x, GameConfig.GRID_ROWS - 1])
            for y in range(4, 10):
                obstacles.append([8, y])
                obstacles.append([21, y])
            for y in range(20, 26):
                obstacles.append([8, y])
                obstacles.append([21, y])
            for x in range(10, 20):
                obstacles.append([x, 10])
                obstacles.append([x, 20])
            return obstacles
        return []

    def setup_fonts(self):
        sys_fonts = pygame.font.get_fonts()
        pref_title_fonts = ['orbitron', 'impact', 'consolas', 'segoe ui black']
        pref_ui_fonts = ['arial', 'segoe ui', 'trebuchet ms', 'lucida sans']
        self.font_title = self.get_available_font(pref_title_fonts, 64)
        self.font_subtitle = self.get_available_font(pref_ui_fonts, 24)
        self.font_hud_label = self.get_available_font(pref_ui_fonts, 16)
        self.font_hud_val = self.get_available_font(pref_title_fonts, 32)
        self.font_badge = self.get_available_font(pref_title_fonts, 20)
        self.font_menu_option = self.get_available_font(pref_ui_fonts, 22)
        self.font_overlay = self.get_available_font(pref_title_fonts, 48)

    def get_available_font(self, font_name_list, size):
        for name in font_name_list:
            if name in pygame.font.get_fonts():
                return pygame.font.SysFont(name, size)
        return pygame.font.Font(None, size + 6)

    def handle_events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.quit_game()
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if self.state == self.STATE_MENU:
                    self.handle_menu_input(event.key)
                elif self.state == self.STATE_PLAYING:
                    self.handle_playing_input(event.key)
                elif self.state == self.STATE_PAUSED:
                    self.handle_paused_input(event.key)
                elif self.state == self.STATE_GAME_OVER:
                    self.handle_game_over_input(event.key)

    def handle_menu_input(self, key):
        if self.map_dropdown_open:
            if key in (pygame.K_UP, pygame.K_w):
                if self.menu_selection > 2:
                    self.menu_selection -= 1
                else:
                    self.map_dropdown_open = False
                    self.menu_selection = 1
            elif key in (pygame.K_DOWN, pygame.K_s):
                if self.menu_selection < 2 + len(self.MAP_NAMES) - 1:
                    self.menu_selection += 1
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                self.map_index = self.menu_selection - 2
                self.map_dropdown_open = False
                self.menu_selection = 1
            elif key == pygame.K_ESCAPE:
                self.map_dropdown_open = False
                self.menu_selection = 1
        else:
            if key in (pygame.K_UP, pygame.K_w):
                if self.menu_selection > 0:
                    self.menu_selection -= 1
            elif key in (pygame.K_DOWN, pygame.K_s):
                if self.menu_selection == 0:
                    self.menu_selection = 1
                elif self.menu_selection == 1:
                    self.map_dropdown_open = True
                    self.menu_selection = 2 + self.map_index
            elif key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.menu_selection == 0:
                    self.start_new_game()
                elif self.menu_selection == 1:
                    self.map_dropdown_open = True
                    self.menu_selection = 2 + self.map_index
            elif key == pygame.K_ESCAPE:
                self.quit_game()

    def handle_playing_input(self, key):
        if key in (pygame.K_UP, pygame.K_w):
            self.snake.change_direction([0, -1])
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.snake.change_direction([0, 1])
        elif key in (pygame.K_LEFT, pygame.K_a):
            self.snake.change_direction([-1, 0])
        elif key in (pygame.K_RIGHT, pygame.K_d):
            self.snake.change_direction([1, 0])
        elif key == pygame.K_p or key == pygame.K_ESCAPE:
            self.state = self.STATE_PAUSED

    def handle_paused_input(self, key):
        if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_SPACE):
            self.state = self.STATE_PLAYING

    def handle_game_over_input(self, key):
        if key == pygame.K_SPACE:
            self.start_new_game()
        elif key == pygame.K_ESCAPE or key == pygame.K_m:
            self.state = self.STATE_MENU

    def start_new_game(self):
        obstacles = self.get_map_obstacles()
        self.snake.reset(obstacles)
        if self.map_index == 2:
            self.tick_interval = self.HARD_TICK_RATE
            food_count = self.HARD_FOOD_COUNT
        else:
            self.tick_interval = GameConfig.BASE_TICK_RATE
            food_count = 1
        self.foods = []
        for _ in range(food_count):
            f = Food()
            occupied = self.snake.body + obstacles
            for existing_f in self.foods:
                occupied.append(existing_f.position)
            f.respawn(self.snake.body, obstacles + [ef.position for ef in self.foods])
            self.foods.append(f)
        self.score = 0
        self.particles.clear()
        self.state = self.STATE_PLAYING
        self.last_tick_time = pygame.time.get_ticks()

    def update_physics(self):
        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.last_tick_time
        if elapsed >= self.tick_interval:
            self.last_tick_time = current_time
            self.snake.update_logic()
            self.check_collisions()

    def check_collisions(self):
        if self.snake.check_self_collision():
            self.trigger_game_over()
            return

        obstacles = self.get_map_obstacles()
        if self.snake.check_obstacle_collision(obstacles):
            self.trigger_game_over()
            return

        head = self.snake.body[0]
        for food in self.foods:
            if head == food.position:
                self.snake.grow()
                self.score += 1
                px = GameConfig.BOARD_X_OFFSET + food.position[0] * GameConfig.GRID_SIZE + GameConfig.GRID_SIZE // 2
                py = GameConfig.BOARD_Y_OFFSET + food.position[1] * GameConfig.GRID_SIZE + GameConfig.GRID_SIZE // 2
                for _ in range(15):
                    self.particles.append(Particle(px, py, GameConfig.COLOR_SNAKE_HEAD))
                other_food_positions = [f.position for f in self.foods if f is not food]
                food.respawn(self.snake.body, obstacles + other_food_positions)
                break

    def trigger_game_over(self):
        self.state = self.STATE_GAME_OVER
        mode_key = self.MAP_KEYS[self.map_index]
        self.score_manager.update_high_score(mode_key, self.score)

    def draw_all(self):
        self.internal_surface.fill(GameConfig.COLOR_BG)
        self.screen_backup = self.screen
        self.screen = self.internal_surface
        self.draw_board_grid()
        self.draw_game_elements()
        self.draw_hud()
        if self.state == self.STATE_MENU:
            self.draw_menu_screen()
        elif self.state == self.STATE_PAUSED:
            self.draw_paused_screen()
        elif self.state == self.STATE_GAME_OVER:
            self.draw_game_over_screen()
        self.screen = self.screen_backup
        win_w, win_h = self.screen.get_size()
        scale = min(win_w / self.internal_width, win_h / self.internal_height)
        scaled_w = int(self.internal_width * scale)
        scaled_h = int(self.internal_height * scale)
        scaled_surface = pygame.transform.smoothscale(self.internal_surface, (scaled_w, scaled_h))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled_surface, ((win_w - scaled_w) // 2, (win_h - scaled_h) // 2))
        pygame.display.flip()

    def draw_board_grid(self):
        board_rect = pygame.Rect(
            GameConfig.BOARD_X_OFFSET,
            GameConfig.BOARD_Y_OFFSET,
            GameConfig.GRID_COLS * GameConfig.GRID_SIZE,
            GameConfig.GRID_ROWS * GameConfig.GRID_SIZE
        )
        pygame.draw.rect(self.screen, GameConfig.COLOR_BOARD_BG, board_rect)
        for col in range(GameConfig.GRID_COLS + 1):
            x = GameConfig.BOARD_X_OFFSET + col * GameConfig.GRID_SIZE
            pygame.draw.line(
                self.screen, 
                GameConfig.COLOR_GRID_LINE, 
                (x, GameConfig.BOARD_Y_OFFSET), 
                (x, GameConfig.BOARD_Y_OFFSET + GameConfig.GRID_ROWS * GameConfig.GRID_SIZE),
                1
            )
        for row in range(GameConfig.GRID_ROWS + 1):
            y = GameConfig.BOARD_Y_OFFSET + row * GameConfig.GRID_SIZE
            pygame.draw.line(
                self.screen, 
                GameConfig.COLOR_GRID_LINE, 
                (GameConfig.BOARD_X_OFFSET, y), 
                (GameConfig.BOARD_X_OFFSET + GameConfig.GRID_COLS * GameConfig.GRID_SIZE, y),
                1
            )

    def draw_game_elements(self):
        board_rect = pygame.Rect(
            GameConfig.BOARD_X_OFFSET,
            GameConfig.BOARD_Y_OFFSET,
            GameConfig.GRID_COLS * GameConfig.GRID_SIZE,
            GameConfig.GRID_ROWS * GameConfig.GRID_SIZE
        )
        self.screen.set_clip(board_rect)
        
        obstacles = self.get_map_obstacles()
        for obs in obstacles:
            ox = GameConfig.BOARD_X_OFFSET + obs[0] * GameConfig.GRID_SIZE
            oy = GameConfig.BOARD_Y_OFFSET + obs[1] * GameConfig.GRID_SIZE
            obs_rect = pygame.Rect(ox + 1, oy + 1, GameConfig.GRID_SIZE - 2, GameConfig.GRID_SIZE - 2)
            pygame.draw.rect(self.screen, GameConfig.COLOR_OBSTACLE, obs_rect, border_radius=4)
            glow_rect = obs_rect.inflate(2, 2)
            pygame.draw.rect(self.screen, (GameConfig.COLOR_OBSTACLE[0], 0, GameConfig.COLOR_OBSTACLE[2], 120), glow_rect, width=1, border_radius=5)

        current_time = pygame.time.get_ticks()
        t = (current_time - self.last_tick_time) / self.tick_interval
        t = max(0.0, min(1.0, t))
        if self.state != self.STATE_PLAYING:
            t = 0.0
            
        food_pulse = 2 * math.sin(pygame.time.get_ticks() * 0.01)
        for food in self.foods:
            food_px = GameConfig.BOARD_X_OFFSET + food.position[0] * GameConfig.GRID_SIZE
            food_py = GameConfig.BOARD_Y_OFFSET + food.position[1] * GameConfig.GRID_SIZE
            food_rect = pygame.Rect(
                food_px + 2 - food_pulse/2, 
                food_py + 2 - food_pulse/2, 
                GameConfig.GRID_SIZE - 4 + food_pulse, 
                GameConfig.GRID_SIZE - 4 + food_pulse
            )
            pygame.draw.rect(self.screen, GameConfig.COLOR_FOOD, food_rect, border_radius=6)
        self.draw_snake_interpolated(t)
        
        for particle in self.particles[:]:
            particle.update()
            if particle.life <= 0:
                self.particles.remove(particle)
            else:
                particle.draw(self.screen)
        self.screen.set_clip(None)

    def draw_snake_interpolated(self, t):
        body = self.snake.body
        prev_body = self.snake.prev_body
        if len(body) != len(prev_body):
            t = 0.0
        color_head = GameConfig.COLOR_SNAKE_HEAD
        color_body = GameConfig.COLOR_SNAKE_BODY
        for i in range(len(body)):
            curr = body[i]
            prev = prev_body[i] if i < len(prev_body) else curr
            draw_positions = []
            x_wrap = abs(curr[0] - prev[0]) > 1.5
            y_wrap = abs(curr[1] - prev[1]) > 1.5
            if not x_wrap and not y_wrap:
                x = prev[0] + (curr[0] - prev[0]) * t
                y = prev[1] + (curr[1] - prev[1]) * t
                draw_positions.append((x, y))
            else:
                interp_x_positions = []
                interp_y_positions = []
                if x_wrap:
                    if curr[0] - prev[0] < -1.5:
                        x_exit = prev[0] + (GameConfig.GRID_COLS - prev[0]) * t
                        x_enter = -1.0 + (curr[0] - (-1.0)) * t
                    else:
                        x_exit = prev[0] + (-1.0 - prev[0]) * t
                        x_enter = GameConfig.GRID_COLS + (curr[0] - GameConfig.GRID_COLS) * t
                    interp_x_positions = [x_exit, x_enter]
                else:
                    x = prev[0] + (curr[0] - prev[0]) * t
                    interp_x_positions = [x]
                if y_wrap:
                    if curr[1] - prev[1] < -1.5:
                        y_exit = prev[1] + (GameConfig.GRID_ROWS - prev[1]) * t
                        y_enter = -1.0 + (curr[1] - (-1.0)) * t
                    else:
                        y_exit = prev[1] + (-1.0 - prev[1]) * t
                        y_enter = GameConfig.GRID_ROWS + (curr[1] - GameConfig.GRID_ROWS) * t
                    interp_y_positions = [y_exit, y_enter]
                else:
                    y = prev[1] + (curr[1] - prev[1]) * t
                    interp_y_positions = [y]
                for rx in interp_x_positions:
                    for ry in interp_y_positions:
                        draw_positions.append((rx, ry))
            for rx, ry in draw_positions:
                px = GameConfig.BOARD_X_OFFSET + rx * GameConfig.GRID_SIZE
                py = GameConfig.BOARD_Y_OFFSET + ry * GameConfig.GRID_SIZE
                seg_rect = pygame.Rect(
                    px + 1, 
                    py + 1, 
                    GameConfig.GRID_SIZE - 2, 
                    GameConfig.GRID_SIZE - 2
                )
                seg_color = color_head if i == 0 else color_body
                border_radius = 8 if i == 0 else 4
                pygame.draw.rect(self.screen, seg_color, seg_rect, border_radius=border_radius)
                if i == 0:
                    glow_rect = seg_rect.inflate(4, 4)
                    glow_color = (seg_color[0], seg_color[1], seg_color[2], 100)
                    glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(glow_surf, glow_color, (0, 0, glow_rect.width, glow_rect.height), border_radius=10, width=2)
                    self.screen.blit(glow_surf, (glow_rect.x, glow_rect.y))

    def draw_hud(self):
        hud_rect = pygame.Rect(0, 0, GameConfig.WINDOW_WIDTH, GameConfig.HUD_HEIGHT)
        pygame.draw.rect(self.screen, GameConfig.COLOR_HUD_BG, hud_rect)
        pygame.draw.line(
            self.screen, 
            GameConfig.COLOR_DIVIDER, 
            (0, GameConfig.HUD_HEIGHT - 3), 
            (GameConfig.WINDOW_WIDTH, GameConfig.HUD_HEIGHT - 3), 
            3
        )
        score_lbl = self.font_hud_label.render("SCORE", True, GameConfig.COLOR_TEXT_MUTED)
        score_val = self.font_hud_val.render(f"{self.score:03d}", True, GameConfig.COLOR_TEXT_LIGHT)
        mode_key = self.MAP_KEYS[self.map_index]
        hi_score = self.score_manager.get_high_score(mode_key)
        hi_lbl = self.font_hud_label.render("HIGH SCORE", True, GameConfig.COLOR_TEXT_MUTED)
        hi_val = self.font_hud_val.render(f"{hi_score:03d}", True, GameConfig.COLOR_TEXT_LIGHT)
        self.screen.blit(score_lbl, (40, 35))
        self.screen.blit(score_val, (40, 65))
        self.screen.blit(hi_lbl, (GameConfig.WINDOW_WIDTH - hi_lbl.get_width() - 40, 35))
        self.screen.blit(hi_val, (GameConfig.WINDOW_WIDTH - hi_val.get_width() - 40, 65))
        self.draw_hud_mode_badge()

    def draw_hud_mode_badge(self):
        self.pulse_timer += 0.05
        pulse_alpha = int(170 + 85 * math.cos(self.pulse_timer))
        map_name = self.MAP_NAMES[self.map_index]
        badge_text = self.font_badge.render(f"MAP: {map_name}", True, GameConfig.COLOR_TEXT_NEON)
        badge_text.set_alpha(pulse_alpha)
        badge_width = badge_text.get_width() + 30
        badge_height = badge_text.get_height() + 15
        badge_x = (GameConfig.WINDOW_WIDTH - badge_width) // 2
        badge_y = 50
        badge_bg = pygame.Surface((badge_width, badge_height), pygame.SRCALPHA)
        pygame.draw.rect(badge_bg, (0, 210, 255, 30), (0, 0, badge_width, badge_height), border_radius=8)
        pygame.draw.rect(badge_bg, (0, 210, 255, alpha_clamped(pulse_alpha)), (0, 0, badge_width, badge_height), width=2, border_radius=8)
        self.screen.blit(badge_bg, (badge_x, badge_y))
        self.screen.blit(
            badge_text, 
            (badge_x + (badge_width - badge_text.get_width()) // 2, 
             badge_y + (badge_height - badge_text.get_height()) // 2)
        )

    def draw_menu_screen(self):
        overlay = pygame.Surface((GameConfig.WINDOW_WIDTH, GameConfig.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 12, 240))
        self.screen.blit(overlay, (0, 0))
        pygame.draw.rect(self.screen, (0, 210, 255, 30), (50, 50, GameConfig.WINDOW_WIDTH - 100, GameConfig.WINDOW_HEIGHT - 100), width=1, border_radius=20)
        
        title_text = self.font_title.render("GRAVITY SNAKE", True, GameConfig.COLOR_SNAKE_HEAD)
        subtitle_text = self.font_subtitle.render("Wrap around obstacles. Weave your path.", True, GameConfig.COLOR_TEXT_MUTED)
        title_x = (GameConfig.WINDOW_WIDTH - title_text.get_width()) // 2
        title_y = 100
        shadow_text = self.font_title.render("GRAVITY SNAKE", True, (0, 70, 90))
        self.screen.blit(shadow_text, (title_x + 3, title_y + 3))
        self.screen.blit(title_text, (title_x, title_y))
        self.screen.blit(subtitle_text, ((GameConfig.WINDOW_WIDTH - subtitle_text.get_width()) // 2, title_y + 70))

        cy = 270
        is_start_selected = (self.menu_selection == 0 and not self.map_dropdown_open)
        start_color = GameConfig.COLOR_TEXT_LIGHT if is_start_selected else GameConfig.COLOR_TEXT_MUTED
        start_font = self.font_overlay if is_start_selected else self.font_subtitle
        start_txt = start_font.render("Start Game", True, start_color)
        start_rect = start_txt.get_rect(center=(GameConfig.WINDOW_WIDTH // 2, cy))
        if is_start_selected:
            self.pulse_timer += 0.04
            ga = int(30 + 20 * math.sin(self.pulse_timer * 1.5))
            gr = start_rect.inflate(50, 24)
            gs = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
            pygame.draw.rect(gs, (0, 210, 255, ga), (0, 0, gr.width, gr.height), border_radius=10)
            pygame.draw.rect(gs, (0, 210, 255, 180), (0, 0, gr.width, gr.height), width=2, border_radius=10)
            self.screen.blit(gs, (gr.x, gr.y))
        self.screen.blit(start_txt, start_rect)

        cy += 70
        is_map_row = (self.menu_selection == 1 and not self.map_dropdown_open)
        arrow_symbol = "v" if not self.map_dropdown_open else "^"
        map_label = f"Map: {self.MAP_NAMES[self.map_index]}  {arrow_symbol}"
        map_color = GameConfig.COLOR_TEXT_LIGHT if (is_map_row or self.map_dropdown_open) else GameConfig.COLOR_TEXT_MUTED
        map_font = self.font_subtitle
        map_txt = map_font.render(map_label, True, map_color)
        map_rect = map_txt.get_rect(center=(GameConfig.WINDOW_WIDTH // 2, cy))
        if is_map_row:
            self.pulse_timer += 0.04
            ga = int(30 + 20 * math.sin(self.pulse_timer * 1.5))
            gr = map_rect.inflate(50, 20)
            gs = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
            pygame.draw.rect(gs, (0, 210, 255, ga), (0, 0, gr.width, gr.height), border_radius=10)
            pygame.draw.rect(gs, (0, 210, 255, 180), (0, 0, gr.width, gr.height), width=2, border_radius=10)
            self.screen.blit(gs, (gr.x, gr.y))
        self.screen.blit(map_txt, map_rect)

        if self.map_dropdown_open:
            dropdown_w = 360
            item_h = 50
            dropdown_h = item_h * len(self.MAP_NAMES) + 20
            dx = (GameConfig.WINDOW_WIDTH - dropdown_w) // 2
            dy = cy + 25
            dd_surf = pygame.Surface((dropdown_w, dropdown_h), pygame.SRCALPHA)
            pygame.draw.rect(dd_surf, (20, 20, 28, 240), (0, 0, dropdown_w, dropdown_h), border_radius=12)
            pygame.draw.rect(dd_surf, (0, 210, 255, 100), (0, 0, dropdown_w, dropdown_h), width=1, border_radius=12)
            self.screen.blit(dd_surf, (dx, dy))

            for idx, name in enumerate(self.MAP_NAMES):
                item_y = dy + 10 + idx * item_h
                is_hovered = (self.menu_selection == 2 + idx)
                is_current = (self.map_index == idx)
                if is_hovered:
                    hi_rect = pygame.Rect(dx + 8, item_y, dropdown_w - 16, item_h - 4)
                    hi_surf = pygame.Surface((hi_rect.width, hi_rect.height), pygame.SRCALPHA)
                    pygame.draw.rect(hi_surf, (0, 210, 255, 40), (0, 0, hi_rect.width, hi_rect.height), border_radius=8)
                    pygame.draw.rect(hi_surf, (0, 210, 255, 160), (0, 0, hi_rect.width, hi_rect.height), width=1, border_radius=8)
                    self.screen.blit(hi_surf, (hi_rect.x, hi_rect.y))
                txt_color = GameConfig.COLOR_SNAKE_HEAD if is_hovered else (GameConfig.COLOR_TEXT_NEON if is_current else GameConfig.COLOR_TEXT_MUTED)
                prefix = "● " if is_current else "  "
                item_txt = self.font_menu_option.render(f"{prefix}{name}", True, txt_color)
                self.screen.blit(item_txt, (dx + 30, item_y + (item_h - item_txt.get_height()) // 2))

            preview_y = dy + dropdown_h + 15
        else:
            preview_y = cy + 50

        self.draw_mini_map_preview(preview_y)

        self.pulse_timer += 0.02
        pulse_alpha = int(160 + 95 * math.sin(self.pulse_timer * 1.5))
        prompt_txt = self.font_subtitle.render("PRESS ENTER TO SELECT", True, GameConfig.COLOR_TEXT_LIGHT)
        prompt_txt.set_alpha(pulse_alpha)
        guide_txt = self.font_hud_label.render("UP / DOWN to navigate  •  ENTER to confirm", True, GameConfig.COLOR_TEXT_MUTED)
        self.screen.blit(prompt_txt, ((GameConfig.WINDOW_WIDTH - prompt_txt.get_width()) // 2, 650))
        self.screen.blit(guide_txt, ((GameConfig.WINDOW_WIDTH - guide_txt.get_width()) // 2, 690))

    def draw_mini_map_preview(self, center_y):
        preview_size = 120
        px = (GameConfig.WINDOW_WIDTH - preview_size) // 2
        py = center_y
        
        preview_rect = pygame.Rect(px, py, preview_size, preview_size)
        pygame.draw.rect(self.screen, GameConfig.COLOR_BOARD_BG, preview_rect, border_radius=8)
        pygame.draw.rect(self.screen, GameConfig.COLOR_DIVIDER, preview_rect, width=1, border_radius=8)
        
        mini_cell = preview_size // GameConfig.GRID_COLS
        obstacles = self.get_map_obstacles()
        for obs in obstacles:
            mx = px + obs[0] * mini_cell
            my = py + obs[1] * mini_cell
            pygame.draw.rect(self.screen, GameConfig.COLOR_OBSTACLE, (mx, my, mini_cell, mini_cell), border_radius=1)

    def draw_paused_screen(self):
        overlay = pygame.Surface((GameConfig.WINDOW_WIDTH, GameConfig.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 12, 180))
        self.screen.blit(overlay, (0, 0))
        paused_txt = self.font_overlay.render("PAUSED", True, GameConfig.COLOR_TEXT_LIGHT)
        resume_txt = self.font_subtitle.render("Press P, ESC, or SPACE to resume", True, GameConfig.COLOR_TEXT_MUTED)
        self.screen.blit(paused_txt, ((GameConfig.WINDOW_WIDTH - paused_txt.get_width()) // 2, 330))
        self.screen.blit(resume_txt, ((GameConfig.WINDOW_WIDTH - resume_txt.get_width()) // 2, 400))

    def draw_game_over_screen(self):
        overlay = pygame.Surface((GameConfig.WINDOW_WIDTH, GameConfig.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 10, 10, 235))
        self.screen.blit(overlay, (0, 0))
        
        header_text = self.font_title.render("GAME OVER", True, GameConfig.COLOR_FOOD)
        header_x = (GameConfig.WINDOW_WIDTH - header_text.get_width()) // 2
        header_y = 200
        
        shadow_header = self.font_title.render("GAME OVER", True, (80, 0, 0))
        self.screen.blit(shadow_header, (header_x + 3, header_y + 3))
        self.screen.blit(header_text, (header_x, header_y))
        
        map_name = self.MAP_NAMES[self.map_index]
        mode_text = self.font_subtitle.render(f"MAP: {map_name}", True, GameConfig.COLOR_TEXT_NEON)
        self.screen.blit(mode_text, ((GameConfig.WINDOW_WIDTH - mode_text.get_width()) // 2, header_y + 80))
        
        stat_box_w = 400
        stat_box_h = 160
        stat_box_x = (GameConfig.WINDOW_WIDTH - stat_box_w) // 2
        stat_box_y = 340
        pygame.draw.rect(self.screen, (24, 20, 20), (stat_box_x, stat_box_y, stat_box_w, stat_box_h), border_radius=12)
        pygame.draw.rect(self.screen, (60, 40, 40), (stat_box_x, stat_box_y, stat_box_w, stat_box_h), width=1, border_radius=12)
        
        score_txt = self.font_badge.render(f"Final Score:  {self.score:03d}", True, GameConfig.COLOR_TEXT_LIGHT)
        mode_key = self.MAP_KEYS[self.map_index]
        hi_score = self.score_manager.get_high_score(mode_key)
        hi_txt = self.font_badge.render(f"High Score:   {hi_score:03d}", True, GameConfig.COLOR_TEXT_MUTED)
        new_high = self.score == hi_score and self.score > 0
        
        self.screen.blit(score_txt, (stat_box_x + 40, stat_box_y + 30))
        self.screen.blit(hi_txt, (stat_box_x + 40, stat_box_y + 65))
        
        if new_high:
            self.pulse_timer += 0.05
            high_pulse_color = (
                int(200 + 55 * math.sin(self.pulse_timer * 2)), 
                int(200 + 55 * math.cos(self.pulse_timer * 2)), 
                50
            )
            new_high_txt = self.font_badge.render("★ NEW RECORD ★", True, high_pulse_color)
            self.screen.blit(new_high_txt, (stat_box_x + 40, stat_box_y + 105))
            
        restart_txt = self.font_subtitle.render("PRESS SPACE TO TRY AGAIN", True, GameConfig.COLOR_TEXT_LIGHT)
        menu_txt = self.font_hud_label.render("Press ESC or M to exit to Title Menu", True, GameConfig.COLOR_TEXT_MUTED)
        self.screen.blit(restart_txt, ((GameConfig.WINDOW_WIDTH - restart_txt.get_width()) // 2, 530))
        self.screen.blit(menu_txt, ((GameConfig.WINDOW_WIDTH - menu_txt.get_width()) // 2, 580))

    def main_loop(self):
        running = True
        while running:
            self.clock.tick(GameConfig.FPS)
            self.handle_events()
            if self.state == self.STATE_PLAYING:
                self.update_physics()
            self.draw_all()

    def quit_game(self):
        pygame.quit()
        sys.exit()

def alpha_clamped(alpha):
    return max(0, min(255, alpha))

if __name__ == "__main__":
    game = GameEngine()
    game.main_loop()
