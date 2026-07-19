import math
import random
import sys
from enum import Enum, auto
from typing import List, Optional, Tuple

import pygame

from .audio import AudioManager
from .entities import Direction, Food, PowerUp, PowerUpType, Snake
from .particles import ParticleSystem
from .renderer import Renderer, FloatingText
from .save import HighScoreManager
from .themes import THEMES
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
        self.menu_selection = 0
        self.settings_selection = 0
        self.last_state = GameState.MENU
        self.name_entered = False
        self.show_name_input = False
        self.name_input = ''
        self.final_rank = -1
        self.game_over_score = 0
        self.magnet_radius = 2

        # Floating score popups
        self.floating_texts: List[FloatingText] = []

        # Ambient particles for menu
        self.ambient_particles: List[dict] = []
        for _ in range(40):
            self.ambient_particles.append({
                'x': random.uniform(0, ws),
                'y': random.uniform(0, hs),
                'vx': random.uniform(-8, 8),
                'vy': random.uniform(-8, 8),
                'size': random.uniform(1, 2.5),
                'alpha': random.uniform(10, 40),
                'phase': random.uniform(0, math.pi * 2),
            })

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
        self.floating_texts.clear()
        self.name_entered = False
        self.show_name_input = False
        self.name_input = ''
        self.final_rank = -1
        self.renderer.shake_x = 0
        self.renderer.shake_y = 0
        self.spawn_food()
        self.spawn_food()

    def spawn_food(self, kind: str = 'normal'):
        for _ in range(100):
            x = random.randint(1, GRID_W - 2)
            y = random.randint(1, GRID_H - 2)
            if not self.snake.occupies(x, y):
                ok = True
                for f in self.foods:
                    if f.x == x and f.y == y and f.alive:
                        ok = False
                        break
                if not ok:
                    continue
                for pu in self.powerups:
                    if pu.x == x and pu.y == y and pu.alive:
                        ok = False
                        break
                if not ok:
                    continue
                for ox, oy in self.obstacles:
                    if ox == x and oy == y:
                        ok = False
                        break
                if ok:
                    break
        else:
            return
        vals = {'normal': 10, 'golden': 50, 'bonus': 25}
        lives = {'normal': 0, 'golden': 5.0, 'bonus': 8.0}
        self.foods.append(Food(
            x=x, y=y, kind=kind,
            value=vals.get(kind, 10),
            max_lifetime=lives.get(kind, 0),
        ))

    def spawn_powerup(self):
        if len([p for p in self.powerups if p.alive]) >= 2:
            return
        for _ in range(50):
            x = random.randint(1, GRID_W - 2)
            y = random.randint(1, GRID_H - 2)
            if not self.snake.occupies(x, y):
                ok = True
                for f in self.foods:
                    if f.x == x and f.y == y and f.alive:
                        ok = False
                        break
                if ok:
                    break
        else:
            return
        ptype = random.choice(list(PowerUpType))
        self.powerups.append(PowerUp(x=x, y=y, ptype=ptype))

    def spawn_obstacles(self):
        self.obstacles.clear()
        count = min(3 + (self.level - 3) * 2, 12)
        for _ in range(count):
            for _ in range(30):
                x = random.randint(2, GRID_W - 3)
                y = random.randint(2, GRID_H - 3)
                if not self.snake.occupies(x, y):
                    ok = True
                    for f in self.foods:
                        if f.x == x and f.y == y and f.alive:
                            ok = False
                            break
                    if ok:
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
            self.spawn_obstacles()
        self.audio.play('levelup')

    def _check_collisions(self):
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

                # Floating score text
                cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
                cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
                ft_color = getattr(self.theme, food.color_key, self.theme.food_normal)
                self.floating_texts.append(FloatingText(cx, cy, f'+{pts}', ft_color))

                # Particles
                color = getattr(self.theme, food.color_key, self.theme.food_normal)
                self.particles.burst(cx, cy, color, 15, 120)

                if food.kind == 'golden':
                    self.audio.play('golden_eat')
                else:
                    self.audio.play('eat')

                if self.food_eaten % 5 == 0:
                    self._advance_level()
                if food.kind == 'bonus':
                    self.spawn_food('bonus')
                    self.spawn_food('bonus')
                should_golden = random.random() < 0.15
                self.spawn_food('golden' if should_golden else 'normal')
                if len(self.foods) < 3:
                    self.spawn_food()
                if random.random() < 0.25:
                    self.spawn_powerup()
                return

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
                self.floating_texts.append(FloatingText(
                    cx, cy, pu.label.upper() + '!', color))
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
                food.x += -1 if dx > 0 else (1 if dx < 0 else 0)
                food.y += -1 if dy > 0 else (1 if dy < 0 else 0)

    def _handle_death(self):
        self.snake.alive = False
        self.state = GameState.GAME_OVER
        self.death_anim_timer = 1.5
        hx, hy = self.snake.head
        cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
        cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
        for _ in range(5):
            self.particles.burst(
                cx + random.randint(-30, 30),
                cy + random.randint(-30, 30),
                self.theme.danger, 25, 180)
        self.particles.burst(cx, cy, self.theme.text_muted, 50, 220)
        self.audio.play('death')
        self.renderer.trigger_shake(8.0)

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
                    if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
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
        items = len(self.ui.menu_items) if self.ui.menu_items else 4
        if key in (pygame.K_UP, pygame.K_w):
            self.menu_selection = (self.menu_selection - 1) % items
            self.audio.play('menu_move')
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.menu_selection = (self.menu_selection + 1) % items
            self.audio.play('menu_move')
        elif key in (pygame.K_RETURN, pygame.K_SPACE):
            item = self.ui.menu_items[self.menu_selection] if self.ui.menu_items else 'Play'
            self._handle_button(item)
            self.audio.play('menu_select')

    def _handle_playing_key(self, key: int):
        d = {pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
             pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
             pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
             pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT}
        if key in d:
            self.snake.set_direction(d[key])
        elif key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = GameState.PAUSED
            self.audio.play('menu_select')

    def _handle_pause_key(self, key: int):
        if key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = GameState.PLAYING
            self.audio.play('menu_select')
        elif key == pygame.K_q:
            self.state = GameState.MENU
            self._reset_game()
            self.audio.play('menu_select')

    def _handle_gameover_key(self, key: int):
        if hasattr(self, 'show_name_input') and self.show_name_input:
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
            elif len(self.name_input) < 8:
                if pygame.K_a <= key <= pygame.K_z:
                    self.name_input += chr(key).upper()
                elif key == pygame.K_SPACE:
                    self.name_input += ' '

    def _handle_settings_key(self, key: int):
        if key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.state = GameState.MENU
            self.audio.play('menu_select')
            self.save_mgr._save_settings()
            return
        if key in (pygame.K_UP, pygame.K_w):
            self.settings_selection = (self.settings_selection - 1) % 4
            self.audio.play('menu_move')
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.settings_selection = (self.settings_selection + 1) % 4
            self.audio.play('menu_move')
        elif key in (pygame.K_LEFT, pygame.K_a):
            self._change_setting(-1)
            self.audio.play('menu_move')
        elif key in (pygame.K_RIGHT, pygame.K_d):
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
            vol = max(0.0, min(1.0, self.save_mgr.settings.volume + direction * 0.1))
            vol = round(vol * 10) / 10
            self.save_mgr.settings.volume = vol
            self.audio.set_volume(vol)

    def _handle_button(self, text: str):
        if text in ('Play', 'Retry'):
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
        elif text in ('Quit to Menu', 'Home'):
            self.state = GameState.MENU
            self._reset_game()
            self.audio.play('menu_select')
        elif text == 'Back':
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
        # Update floating texts
        for ft in list(self.floating_texts):
            ft.update(self.dt)
            if not ft.alive:
                self.floating_texts.remove(ft)

    def _update_playing(self):
        if not self.snake.alive:
            return

        slow = self.snake.slow_active
        tick = self.current_tick_ms * (1.5 if slow else 1.0)
        self.tick_accumulator += self.dt * 1000
        wrap = self.save_mgr.settings.wrap_walls

        while self.tick_accumulator >= tick:
            self.tick_accumulator -= tick
            self.snake.update_powerups(self.dt, tick)

            # Handle slow mode deactivation
            if self.snake.slow_active and 'slow' not in self.snake.powerup_timers:
                self.snake.slow_active = False
                self.current_tick_ms = self.base_tick_ms

            # --- PREDICT NEXT HEAD POSITION BEFORE MOVING ---
            dx, dy = self.snake.direction.vector
            hx, hy = self.snake.head
            nx, ny = hx + dx, hy + dy

            if not wrap and (nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H):
                if self.snake.shield_active:
                    self._shield_block_wall()
                    self.snake.shield_active = False
                    if 'shield' in self.snake.powerup_timers:
                        del self.snake.powerup_timers['shield']
                    continue  # skip this tick, snake didn't move
                else:
                    self.snake.update()
                    self._handle_death()
                    return
            else:
                self.snake.update()
                if wrap:
                    self.snake.wrap_position()

            if self.snake.check_self_collision():
                if self.snake.shield_active:
                    self.snake.shield_active = False
                    if 'shield' in self.snake.powerup_timers:
                        del self.snake.powerup_timers['shield']
                else:
                    self._handle_death()
                    return

            self._update_magnet()
            self._check_collisions()

            # Clean up expired food/powerups
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

            if not self.foods:
                self.spawn_food()
            if len(self.foods) < 2:
                self.spawn_food()

        # Snake trail particles
        if self.snake and self.snake.alive:
            hx, hy = self.snake.head
            cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
            cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
            if random.random() < 0.4:
                self.particles.trail(cx, cy, self.theme.snake_head, 1, 25)

    def _shield_block_wall(self):
        hx, hy = self.snake.head
        cx = hx * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_x
        cy = hy * CELL_SIZE + CELL_SIZE // 2 + self.grid_offset_y
        self.particles.burst(cx, cy, self.theme.powerup_shield, 15, 120)
        self.floating_texts.append(FloatingText(cx, cy - 10, 'BLOCKED!', self.theme.powerup_shield))

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
        sox, soy = self.renderer.get_shake_offset()

        if self.state == GameState.MENU:
            self._draw_ambient_particles()
            self.renderer.draw_grid(self.screen,
                                    self.grid_offset_x + sox, self.grid_offset_y + soy,
                                    self.save_mgr.settings.show_grid)
            self._draw_background_snake()
            self.ui.draw_menu(self.time_s)

        elif self.state in (GameState.PLAYING, GameState.PAUSED):
            self.renderer.draw_grid(self.screen,
                                    self.grid_offset_x + sox, self.grid_offset_y + soy,
                                    self.save_mgr.settings.show_grid)
            if self.save_mgr.settings.particles:
                self.particles.draw(self.screen)
            self.renderer.draw_powerups(self.screen, self.powerups, self.time_s,
                                        sox, soy)
            self.renderer.draw_food(self.screen, self.foods, self.time_s,
                                    sox, soy)
            if self.level >= 3:
                self.renderer.draw_obstacles(self.screen, self.obstacles,
                                             sox, soy)
            self.renderer.draw_floating_texts(self.screen, self.floating_texts)
            self.renderer.draw_snake(self.screen, self.snake.body, self.time_s,
                                     sox, soy)
            self.ui.draw_hud(
                self.score, self.level, self._get_speed(),
                self._get_active_powerup_display() if self.snake else {},
                self.time_s)
            self.ui.draw_fps(self.clock.get_fps())
            if self.state == GameState.PAUSED:
                self.ui.draw_pause(self.time_s)

        elif self.state == GameState.GAME_OVER:
            self.renderer.draw_grid(self.screen,
                                    self.grid_offset_x + sox, self.grid_offset_y + soy,
                                    self.save_mgr.settings.show_grid)
            if self.save_mgr.settings.particles:
                self.particles.draw(self.screen)
            self.renderer.draw_floating_texts(self.screen, self.floating_texts)
            is_high = self.save_mgr.is_high_score(self.score) and not self.name_entered
            self.ui.draw_game_over(
                self.time_s, self.score, self.level,
                self.food_eaten, is_high or self.final_rank >= 0,
                self.final_rank if self.final_rank >= 0 else -1)

        elif self.state == GameState.HIGH_SCORES:
            self._draw_ambient_particles()
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y, False)
            self.ui.draw_high_scores(self.save_mgr.get_top_scores(), self.time_s)

        elif self.state == GameState.SETTINGS:
            self._draw_ambient_particles()
            self.renderer.draw_grid(self.screen, self.grid_offset_x, self.grid_offset_y, False)
            self.ui.draw_settings(self.time_s)

        pygame.display.flip()

    def _draw_ambient_particles(self):
        w, h = self.screen.get_size()
        for p in self.ambient_particles:
            p['x'] += p['vx'] * self.dt
            p['y'] += p['vy'] * self.dt
            if p['x'] < 0 or p['x'] > w:
                p['vx'] *= -1
            if p['y'] < 0 or p['y'] > h:
                p['vy'] *= -1
            alpha = int(p['alpha'] * (math.sin(self.time_s * 0.3 + p['phase']) * 0.5 + 0.5))
            pygame.draw.circle(self.screen, (*self.theme.accent, max(5, alpha)),
                               (int(p['x']), int(p['y'])), int(p['size']))

    def _draw_background_snake(self):
        if self.time_s < 0.1:
            return
        ox, oy = self.grid_offset_x, self.grid_offset_y
        t = self.time_s
        points = []
        for i in range(14):
            phase = t * 0.4 + i * 0.7
            x = int(ox + (math.sin(phase) * 0.45 + 0.5) * PLAY_AREA_W)
            y = int(oy + (math.cos(phase * 0.65) * 0.45 + 0.5) * PLAY_AREA_H)
            points.append((x, y))
        for i in range(len(points) - 1):
            alpha = int(15 + math.sin(t * 2 + i * 0.5) * 8)
            pygame.draw.line(self.screen, (*self.theme.snake_head, alpha),
                             points[i], points[i + 1], 2)

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.render()
        pygame.quit()
        sys.exit()
