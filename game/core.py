import math
import random
import sys
from enum import Enum, auto
from typing import List, Optional, Tuple

import pygame

from .audio import AudioManager
from .entities import (
    Direction, Food, PowerUp, PowerUpType, Snake,
)
from .particles import ParticleSystem
from .renderer import Renderer
from .save import HighScoreManager
from .themes import Theme, THEMES
from .ui import UIManager


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    HIGH_SCORES = auto()
    SETTINGS = auto()


GRID_W = 20
GRID_H = 20
CELL_SIZE = 30
PLAY_AREA_W = GRID_W * CELL_SIZE
PLAY_AREA_H = GRID_H * CELL_SIZE
UI_PADDING = 80
MIN_W = PLAY_AREA_W + UI_PADDING * 2
MIN_H = PLAY_AREA_H + UI_PADDING * 2


class Game:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MENU
        self.time_s = 0.0
        self.dt = 0.0

        ws = max(MIN_W, 900)
        hs = max(MIN_H, 720)
        self.screen = pygame.display.set_mode((ws, hs), pygame.RESIZABLE)
        pygame.display.set_caption('Snake — Neon Protocol')
        pygame.display.set_icon(self._create_icon())

        self.grid_offset_x = (ws - PLAY_AREA_W) // 2
        self.grid_offset_y = (hs - PLAY_AREA_H) // 2 + 10

        self.save_mgr = HighScoreManager()
        theme_name = self.save_mgr.get_setting('theme') or 'Dark Nebula'
        self.theme = THEMES.get(theme_name, list(THEMES.values())[0])
        self.renderer = Renderer(self.theme, GRID_W, GRID_H, CELL_SIZE)
        self.ui = UIManager(self.screen, self.theme, self.save_mgr)
        self.audio = AudioManager()
        self.audio.set_volume(self.save_mgr.get_setting('volume') or 0.7)
        self.audio.load()
        self.particles = ParticleSystem()

        self.snake: Optional[Snake] = None
        self.foods: List[Food] = []
        self.powerups: List[PowerUp] = []
        self.obstacles: List[Tuple[int, int]] = []
        self.score = 0
        self.level = 1
        self.food_eaten = 0
        self.base_tick_ms = 180
        self.current_tick_ms = 180
        self.tick_accumulator = 0.0
        self.death_anim_timer = 0.0
        self.should_restart = False
        self.menu_selection = 0
        self.settings_selection = 0
        self.last_state = GameState.MENU
        self.name_entered = False
        self.final_rank = -1
        self.game_over_score = 0
        self.magnet_radius = 2

        self._reset_game()

    def _create_icon(self) -> pygame.Surface:
        s = pygame.Surface((32, 32))
        s.fill((10, 10, 26))
        pygame.draw.rect(s, (0, 255, 136), (10, 10, 12, 12), border_radius=3)
        return s

    def _reset_game(self):
        self.snake = Snake(GRID_W, GRID_H)
        self.foods = []
        self.powerups = []
        self.obstacles = []
        self.score = 0
        self.level = 1
        self.food_eaten = 0
        self.base_tick_ms = 180
        self.current_tick_ms = 180
        self.tick_accumulator = 0.0
        self.death_anim_timer = 0.0
        self.particles.clear()
        self.name_entered = False
        self.final_rank = -1
        self._spawn_food()
        self._spawn_food()

    def _spawn_food(self, kind: str = 'normal'):
        for _ in range(50):
            x = random.randint(1, GRID_W - 2)
            y = random.randint(1, GRID_H - 2)
            if not self.snake.occupies(x, y):
                for f in self.foods:
                    if f.x == x and f.y == y and f.alive:
                        break
                else:
                    for pu in self.powerups:
                        if pu.x == x and pu.y == y and pu.alive:
                            break
                    else:
                        for ox, oy in self.obstacles:
                            if ox == x and oy == y:
                                break
                        else:
                            break
        vals = {'normal': 10, 'golden': 50, 'bonus': 25}
        lives = {'normal': 0, 'golden': 5.0, 'bonus': 8.0}
        self.foods.append(Food(
            x=x, y=y, kind=kind,
            value=vals.get(kind, 10),
            max_lifetime=lives.get(kind, 0),
        ))

    def _spawn_powerup(self):
        if len([p for p in self.powerups if p.alive]) >= 2:
            return
        for _ in range(50):
            x = random.randint(1, GRID_W - 2)
            y = random.randint(1, GRID_H - 2)
            if not self.snake.occupies(x, y):
                for f in self.foods:
                    if f.x == x and f.y == y and f.alive:
                        break
                else:
                    break
        ptype = random.choice(list(PowerUpType))
        self.powerups.append(PowerUp(x=x, y=y, ptype=ptype))

    def _spawn_obstacles(self):
        self.obstacles.clear()
        count = min(3 + (self.level - 3) * 2, 12)
        for _ in range(count):
            for attempt in range(30):
                x = random.randint(2, GRID_W - 3)
                y = random.randint(2, GRID_H - 3)
                if not self.snake.occupies(x, y):
                    for f in self.foods:
                        if f.x == x and f.y == y and f.alive:
                            break
                    else:
                        self.obstacles.append((x, y))
                        break

    def _get_speed(self) -> float:
        return 1000.0 / self.current_tick_ms if self.current_tick_ms > 0 else 0

    def _advance_level(self):
        self.level += 1
        self.base_tick_ms = max(50, self.base_tick_ms - 12)
        self.current_tick_ms = self.base_tick_ms
        if self.snake.slow_active:
            self.current_tick_ms = int(self.current_tick_ms * 1.5)
        if self.level >= 3:
            self._spawn_obstacles()
        self.audio.play('levelup')

    def _check_food_collision(self):
        hx, hy = self.snake.head
        for food in self.foods:
            if not food.alive:
                continue
            if food.x == hx and food.y == hy:
                food.alive = False
                self.snake.grow()
                pts = food.value * self.level
                if self.snake.score_multiplier > 1:
                    pts = int(pts * self.snake.score_multiplier)
                self.score += pts
                self.food_eaten += 1
                cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
                cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
                color_key = food.color_key
                color = getattr(self.theme, color_key, self.theme.food_normal)
                self.particles.burst(cx, cy, color, 15, 120)
                if food.kind == 'golden':
                    self.audio.play('golden_eat')
                else:
                    self.audio.play('eat')
                if self.food_eaten % 5 == 0:
                    self._advance_level()
                if food.kind == 'bonus':
                    self._spawn_food('bonus')
                    self._spawn_food('bonus')
                should_spawn_golden = random.random() < 0.15
                self._spawn_food('golden' if should_spawn_golden else 'normal')
                if len(self.foods) < 3:
                    self._spawn_food()
                if random.random() < 0.25:
                    self._spawn_powerup()
                return

    def _check_powerup_collision(self):
        hx, hy = self.snake.head
        for pu in self.powerups:
            if not pu.alive:
                continue
            if pu.x == hx and pu.y == hy:
                pu.alive = False
                self.snake.apply_powerup(pu.ptype)
                if pu.ptype == PowerUpType.SLOW:
                    self.current_tick_ms = int(self.base_tick_ms * 1.5)
                cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
                cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
                color = getattr(self.theme, pu.color_key, self.theme.accent)
                self.particles.burst(cx, cy, color, 20, 150)
                self.audio.play('powerup')
                return

    def _update_magnet(self):
        if not self.snake.magnet_active:
            return
        hx, hy = self.snake.head
        for food in self.foods:
            if not food.alive:
                continue
            dx = food.x - hx
            dy = food.y - hy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist <= self.magnet_radius and dist > 0:
                speed = 0.2
                food.x += -1 if dx > 0 else (1 if dx < 0 else 0)
                food.y += -1 if dy > 0 else (1 if dy < 0 else 0)

    def _handle_death(self, reason: str = 'collision'):
        self.snake.alive = False
        self.death_anim_timer = 1.2
        hx, hy = self.snake.head
        cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
        cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
        for _ in range(3):
            self.particles.burst(
                cx + random.randint(-20, 20),
                cy + random.randint(-20, 20),
                self.theme.danger, 20, 160)
        self.particles.burst(cx, cy, self.theme.text_muted, 40, 200)
        self.audio.play('death')

    def _get_active_powerup_display(self) -> dict:
        result = {}
        for key, val in self.snake.powerup_timers.items():
            max_time = {'shield': 8.0, 'magnet': 6.0, 'slow': 5.0}.get(key, 5.0)
            result[key] = (val, max_time)
        return result

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.VIDEORESIZE:
                ws = max(MIN_W, event.w)
                hs = max(MIN_H, event.h)
                self.screen = pygame.display.set_mode((ws, hs), pygame.RESIZABLE)
                self.width, self.height = ws, hs
                self.grid_offset_x = (ws - PLAY_AREA_W) // 2
                self.grid_offset_y = (hs - PLAY_AREA_H) // 2 + 10
                self.ui.width, self.ui.height = ws, hs

            if event.type == pygame.KEYDOWN:
                if self.state == GameState.MENU:
                    self._handle_menu_key(event.key)
                elif self.state == GameState.PLAYING:
                    self._handle_playing_key(event.key)
                elif self.state == GameState.PAUSED:
                    self._handle_pause_key(event.key)
                elif self.state == GameState.GAME_OVER:
                    self._handle_gameover_key(event.key)
                elif self.state == GameState.HIGH_SCORES:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                        self.state = GameState.MENU
                        self.audio.play('menu_select')
                elif self.state == GameState.SETTINGS:
                    self._handle_settings_key(event.key)

            if event.type == pygame.MOUSEBUTTONDOWN:
                for b in self.ui.buttons:
                    if b.handle_event(event):
                        self._handle_button(b.text)
                        break

            for b in self.ui.buttons:
                b.handle_event(event)

    def _handle_menu_key(self, key: int):
        items = len(self.ui.menu_items) if hasattr(self.ui, 'menu_items') and self.ui.menu_items else 4
        if key == pygame.K_UP or key == pygame.K_w:
            self.menu_selection = (self.menu_selection - 1) % items
            self.audio.play('menu_move')
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.menu_selection = (self.menu_selection + 1) % items
            self.audio.play('menu_move')
        elif key == pygame.K_RETURN or key == pygame.K_SPACE:
            item = self.ui.menu_items[self.menu_selection] if self.ui.menu_items else 'Play'
            self._handle_button(item)
            self.audio.play('menu_select')

    def _handle_playing_key(self, key: int):
        if key == pygame.K_UP or key == pygame.K_w:
            self.snake.set_direction(Direction.UP)
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.snake.set_direction(Direction.DOWN)
        elif key == pygame.K_LEFT or key == pygame.K_a:
            self.snake.set_direction(Direction.LEFT)
        elif key == pygame.K_RIGHT or key == pygame.K_d:
            self.snake.set_direction(Direction.RIGHT)
        elif key == pygame.K_ESCAPE or key == pygame.K_p:
            self.state = GameState.PAUSED
            self.audio.play('menu_select')

    def _handle_pause_key(self, key: int):
        if key == pygame.K_ESCAPE or key == pygame.K_p:
            self.state = GameState.PLAYING
            self.audio.play('menu_select')
        elif key == pygame.K_q:
            self.state = GameState.MENU
            self._reset_game()
            self.audio.play('menu_select')

    def _handle_gameover_key(self, key: int):
        if self.show_name_input:
            if key == pygame.K_RETURN and self.name_input.strip():
                name = self.name_input.strip()[:8]
                self.final_rank = self.save_mgr.add_score(
                    name, self.game_over_score, self.level, self.food_eaten)
                self.show_name_input = False
                self.name_entered = True
                self.audio.play('menu_select')
            elif key == pygame.K_BACKSPACE:
                self.name_input = self.name_input[:-1]
            elif key == pygame.K_ESCAPE:
                self.show_name_input = False
                self.name_entered = True
            else:
                if len(self.name_input) < 8 and pygame.K_a <= key <= pygame.K_z:
                    self.name_input += chr(key).upper()
                elif key == pygame.K_SPACE and len(self.name_input) < 8:
                    self.name_input += ' '

    def _handle_settings_key(self, key: int):
        if key == pygame.K_ESCAPE or key == pygame.K_RETURN:
            self.state = GameState.MENU
            self.audio.play('menu_select')
            self.save_mgr._save_settings()
            return
        if key == pygame.K_UP or key == pygame.K_w:
            self.settings_selection = (self.settings_selection - 1) % 4
            self.audio.play('menu_move')
        elif key == pygame.K_DOWN or key == pygame.K_s:
            self.settings_selection = (self.settings_selection + 1) % 4
            self.audio.play('menu_move')
        elif key == pygame.K_LEFT or key == pygame.K_a:
            self._change_setting(-1)
            self.audio.play('menu_move')
        elif key == pygame.K_RIGHT or key == pygame.K_d:
            self._change_setting(1)
            self.audio.play('menu_move')

    def _change_setting(self, direction: int):
        if self.settings_selection == 0:
            names = list(THEMES.keys())
            idx = names.index(self.save_mgr.settings.theme)
            idx = (idx + direction) % len(names)
            new_name = names[idx]
            self.save_mgr.settings.theme = new_name
            self.theme = THEMES[new_name]
            self.renderer.set_theme(self.theme)
            self.ui.theme = self.theme
        elif self.settings_selection == 1:
            self.save_mgr.settings.wrap_walls = not self.save_mgr.settings.wrap_walls
        elif self.settings_selection == 2:
            self.save_mgr.settings.particles = not self.save_mgr.settings.particles
        elif self.settings_selection == 3:
            vol = self.save_mgr.settings.volume
            step = 0.1
            vol = max(0.0, min(1.0, vol + direction * step))
            vol = round(vol * 10) / 10
            self.save_mgr.settings.volume = vol
            self.audio.set_volume(vol)

    def _handle_button(self, text: str):
        if text == 'Play' or text == 'Play Again':
            self.state = GameState.PLAYING
            self._reset_game()
            self.audio.play('menu_select')
        elif text == 'High Scores':
            self.state = GameState.HIGH_SCORES
            self.audio.play('menu_select')
        elif text == 'Settings':
            self.state = GameState.SETTINGS
            self.audio.play('menu_select')
        elif text == 'Quit':
            self.running = False
        elif text == 'Resume':
            self.state = GameState.PLAYING
            self.audio.play('menu_select')
        elif text == 'Quit to Menu':
            self.state = GameState.MENU
            self._reset_game()
            self.audio.play('menu_select')
        elif text == 'Main Menu':
            self.state = GameState.MENU
            self._reset_game()
            self.audio.play('menu_select')
        elif text == 'Back':
            if self.last_state and self.last_state != GameState.MENU:
                self.state = self.last_state
            else:
                self.state = GameState.MENU
            self.audio.play('menu_select')

    def update(self):
        self.dt = self.clock.tick(60) / 1000.0
        self.time_s += self.dt

        if self.state == GameState.PLAYING:
            self._update_playing()
        elif self.state == GameState.GAME_OVER:
            self._update_gameover()
        self.particles.update(self.dt)

    def _update_playing(self):
        if not self.snake.alive:
            return

        if self.snake.slow_active:
            tick = self.current_tick_ms * 1.5
        else:
            tick = self.current_tick_ms

        self.tick_accumulator += self.dt * 1000
        wrap = self.save_mgr.settings.wrap_walls

        while self.tick_accumulator >= tick:
            self.tick_accumulator -= tick

            self.snake.update_powerups(self.dt, tick)

            if not self.snake.slow_active and self.snake.powerup_timers.get('slow'):
                pass
            elif self.snake.slow_active and 'slow' not in self.snake.powerup_timers:
                self.snake.slow_active = False
                self.current_tick_ms = self.base_tick_ms

            if wrap:
                self.snake.wrap_position()
            else:
                col = self.snake.check_wall_collision(False)
                if col:
                    if self.snake.shield_active:
                        hx, hy = self.snake.head
                        if hx < 0:
                            self.snake.body[0] = (0, hy)
                        elif hx >= GRID_W:
                            self.snake.body[0] = (GRID_W - 1, hy)
                        if hy < 0:
                            self.snake.body[0] = (hx, 0)
                        elif hy >= GRID_H:
                            self.snake.body[0] = (hx, GRID_H - 1)
                        self.snake.shield_active = False
                        if 'shield' in self.snake.powerup_timers:
                            del self.snake.powerup_timers['shield']
                    else:
                        self._handle_death('wall')
                        return

            self.snake.update()

            if self.snake.check_self_collision():
                if self.snake.shield_active:
                    self.snake.shield_active = False
                    if 'shield' in self.snake.powerup_timers:
                        del self.snake.powerup_timers['shield']
                else:
                    self._handle_death('self')
                    return

            self._update_magnet()
            self._check_food_collision()
            self._check_powerup_collision()

            for food in self.foods:
                if food.max_lifetime > 0:
                    food.lifetime += tick / 1000
                    if food.lifetime >= food.max_lifetime:
                        food.alive = False

            self.foods = [f for f in self.foods if f.alive]

            for pu in self.powerups:
                if pu.alive:
                    pu.lifetime += tick / 1000
                    if pu.lifetime >= 8.0:
                        pu.alive = False
            self.powerups = [p for p in self.powerups if p.alive]

            if len(self.foods) == 0:
                self._spawn_food()
            if len(self.foods) < 2:
                self._spawn_food()

    def _update_gameover(self):
        if self.death_anim_timer > 0:
            self.death_anim_timer -= self.dt
        elif not self.name_entered:
            if self.save_mgr.is_high_score(self.score) and self.score > 0:
                self.show_name_input = True
            else:
                self.name_entered = True

    def render(self):
        self.screen.fill(self.theme.bg)

        if self.state == GameState.MENU:
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y,
                                    self.save_mgr.settings.show_grid)
            self._draw_background_snake()
            self.ui.draw_menu(self.time_s)

        elif self.state == GameState.PLAYING or self.state == GameState.PAUSED:
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y,
                                    self.save_mgr.settings.show_grid)
            if self.save_mgr.settings.particles:
                self.particles.draw(self.screen)
            self.renderer.draw_powerups(self.screen, self.powerups, self.time_s)
            self.renderer.draw_food(self.screen, self.foods, self.time_s)
            if self.level >= 3:
                self.renderer.draw_obstacles(self.screen, self.obstacles)
            self.renderer.draw_snake(self.screen, self.snake.body)
            self.ui.draw_hud(
                self.score, self.level, self._get_speed(),
                self._get_active_powerup_display() if self.snake else {},
                self.time_s)
            self.ui.draw_fps(self.clock.get_fps())
            if self.state == GameState.PAUSED:
                self.ui.draw_pause(self.time_s)

        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y,
                                    self.save_mgr.settings.show_grid)
            if self.save_mgr.settings.particles:
                self.particles.draw(self.screen)
            is_high = self.save_mgr.is_high_score(self.score) and not self.name_entered
            self.ui.draw_game_over(
                self.time_s, self.score, self.level,
                self.food_eaten, is_high or self.final_rank >= 0,
                self.final_rank if self.final_rank >= 0 else -1)

        elif self.state == GameState.HIGH_SCORES:
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y, False)
            self.ui.draw_high_scores(self.save_mgr.get_top_scores(), self.time_s)

        elif self.state == GameState.SETTINGS:
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y, False)
            self.ui.draw_settings(self.time_s)

        pygame.display.flip()

    def _draw_background_snake(self):
        if self.time_s < 0.1:
            return
        ox, oy = self.grid_offset_x, self.grid_offset_y
        cs = CELL_SIZE
        t = self.time_s
        points = []
        for i in range(12):
            phase = t * 0.5 + i * 0.8
            x = int(ox + (math.sin(phase) * 0.4 + 0.5) * PLAY_AREA_W)
            y = int(oy + (math.cos(phase * 0.7) * 0.4 + 0.5) * PLAY_AREA_H)
            points.append((x, y))
        for i in range(len(points) - 1):
            alpha = int(20 + math.sin(t * 2 + i) * 10)
            pygame.draw.line(self.screen, (*self.theme.snake_head, alpha),
                             points[i], points[i + 1], 2)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
        pygame.quit()
        sys.exit()
