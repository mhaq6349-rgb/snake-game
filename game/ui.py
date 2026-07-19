import math
from typing import List, Optional, Tuple

import pygame

from .themes import Theme, THEMES
from .save import HighScoreManager, ScoreEntry


class Button:
    def __init__(self, rect: pygame.Rect, text: str, color: Tuple[int, int, int],
                 hover_color: Tuple[int, int, int], font_size: int = 20,
                 radius: int = 8):
        self.rect = rect
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.font_size = font_size
        self.radius = radius
        self.hovered = False
        self.pulse = 0.0

    def draw(self, surface: pygame.Surface, theme: Theme, time_s: float):
        color = self.hover_color if self.hovered else self.color
        pulse = math.sin(time_s * 2) * 3 if self.hovered else 0
        r = self.rect.inflate(pulse, pulse)
        bg = (*color, 180 if not self.hovered else 230)
        bg_surf = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.rect(bg_surf, bg, bg_surf.get_rect(), border_radius=self.radius)
        if self.hovered:
            pygame.draw.rect(bg_surf, (*color, 60), bg_surf.get_rect(),
                             border_radius=self.radius, width=2)
        surface.blit(bg_surf, r.topleft)
        font = pygame.font.Font(None, self.font_size)
        txt = font.render(self.text, True, theme.text_primary)
        txt_rect = txt.get_rect(center=r.center)
        surface.blit(txt, txt_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def handle_key(self, key: int) -> bool:
        return False


class UIManager:
    def __init__(self, screen: pygame.Surface, theme: Theme, save_mgr: HighScoreManager):
        self.screen = screen
        self.theme = theme
        self.save = save_mgr
        self.width, self.height = screen.get_size()
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 18)
        self.font_tiny = pygame.font.Font(None, 14)
        self.buttons: List[Button] = []
        self.name_input = ''
        self.name_cursor = 0
        self.show_name_input = False
        self.name_done = False
        self.menu_selection = 0
        self.menu_items = []

    def _center(self, w: int, h: int) -> Tuple[int, int]:
        return (self.width - w) // 2, (self.height - h) // 2

    def _draw_bg(self, alpha: int = 180):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((*self.theme.bg, alpha))
        self.screen.blit(overlay, (0, 0))

    def _draw_title(self, text: str, y: int, size: int = None):
        font = pygame.font.Font(None, size or 48)
        txt = font.render(text, True, self.theme.snake_head)
        shadow = font.render(text, True, (0, 0, 0))
        trect = txt.get_rect(center=(self.width // 2, y))
        srect = shadow.get_rect(center=(self.width // 2 + 2, y + 2))
        self.screen.blit(shadow, srect)
        self.screen.blit(txt, trect)

    def draw_menu(self, time_s: float):
        w, h = self.width, self.height
        # Animated dots in background
        for i in range(30):
            x = int((math.sin(time_s * 0.3 + i * 1.7) * 0.5 + 0.5) * w)
            y = int((math.cos(time_s * 0.2 + i * 2.3) * 0.5 + 0.5) * h)
            alpha = int(30 + math.sin(time_s + i) * 15)
            pygame.draw.circle(self.screen, (*self.theme.accent, alpha), (x, y), 1.5)

        self._draw_title('S N A K E', h // 4, 56)
        sub = self.font_small.render('neon protocol', True, self.theme.text_muted)
        self.screen.blit(sub, sub.get_rect(center=(w // 2, h // 4 + 44)))
        self.menu_items = ['Play', 'High Scores', 'Settings', 'Quit']
        start_y = h // 2 - 10
        self.buttons.clear()
        for i, item in enumerate(self.menu_items):
            by = start_y + i * 52
            btn = Button(
                pygame.Rect(w // 2 - 90, by, 180, 40),
                item,
                (30, 30, 55),
                self.theme.accent,
                22, 6,
            )
            self.buttons.append(btn)

        for b in self.buttons:
            b.draw(self.screen, self.theme, time_s)

    def draw_pause(self, time_s: float):
        self._draw_bg(140)
        self._draw_title('PAUSED', self.height // 3, 42)
        resume_btn = Button(
            pygame.Rect(self.width // 2 - 90, self.height // 2 - 10, 180, 40),
            'Resume', self.theme.accent, self.theme.snake_head, 20, 6,
        )
        quit_btn = Button(
            pygame.Rect(self.width // 2 - 90, self.height // 2 + 50, 180, 40),
            'Quit to Menu', (40, 40, 55), self.theme.danger, 20, 6,
        )
        self.buttons = [resume_btn, quit_btn]
        for b in self.buttons:
            b.draw(self.screen, self.theme, time_s)

    def draw_game_over(self, time_s: float, score: int, level: int,
                       food_eaten: int, is_high: bool, rank: int = -1):
        self._draw_bg(170)
        self._draw_title('GAME OVER', self.height // 5, 46)

        stats_x = self.width // 2 - 100
        stats_y = self.height // 3
        line_h = 28
        for i, (label, val) in enumerate([
            ('Score', str(score)),
            ('Level', str(level)),
            ('Food', str(food_eaten)),
        ]):
            lbl = self.font_medium.render(label, True, self.theme.text_secondary)
            vl = self.font_medium.render(val, True, self.theme.text_primary)
            self.screen.blit(lbl, (stats_x, stats_y + i * line_h))
            self.screen.blit(vl, (stats_x + 140, stats_y + i * line_h))

        if is_high and rank >= 0:
            hs = self.font_small.render(
                f'New High Score! (#{rank + 1})' if self.save.scores else 'New High Score!',
                True, self.theme.food_golden)
            self.screen.blit(hs, hs.get_rect(center=(self.width // 2, stats_y + 3 * line_h + 10)))

        if self.show_name_input:
            prompt = self.font_small.render('Enter name:', True, self.theme.text_secondary)
            self.screen.blit(prompt, (stats_x, stats_y + 4 * line_h + 15))
            name_surf = self.font_large.render(
                self.name_input + ('_' if time_s % 0.5 < 0.25 else ' '),
                True, self.theme.snake_head)
            self.screen.blit(name_surf, (stats_x, stats_y + 4 * line_h + 38))
            instr = self.font_tiny.render(
                'Enter name then press ENTER',
                True, self.theme.text_muted)
            self.screen.blit(instr, (stats_x, stats_y + 4 * line_h + 72))
        else:
            self.buttons = []
            play_again = Button(
                pygame.Rect(self.width // 2 - 90, stats_y + 4 * line_h + 15, 180, 40),
                'Play Again', self.theme.accent, self.theme.snake_head, 20, 6,
            )
            to_menu = Button(
                pygame.Rect(self.width // 2 - 90, stats_y + 4 * line_h + 65, 180, 40),
                'Main Menu', (40, 40, 55), self.theme.text_secondary, 20, 6,
            )
            self.buttons = [play_again, to_menu]
            for b in self.buttons:
                b.draw(self.screen, self.theme, time_s)

    def draw_high_scores(self, scores: List[ScoreEntry], time_s: float):
        self._draw_bg(160)
        self._draw_title('HIGH SCORES', self.height // 6, 40)

        if not scores:
            empty = self.font_medium.render('No scores yet!', True, self.theme.text_muted)
            self.screen.blit(empty, empty.get_rect(center=(self.width // 2, self.height // 2 - 20)))
        else:
            start_y = self.height // 4
            for i, s in enumerate(scores[:10]):
                color = self.theme.food_golden if i == 0 else (
                    self.theme.text_secondary if i < 3 else self.theme.text_muted)
                rank_str = f'#{i + 1}'
                med_font = pygame.font.Font(None, 22)
                rank_surf = med_font.render(rank_str, True, color)
                name_surf = med_font.render(s.name, True, self.theme.text_primary)
                score_surf = med_font.render(str(s.score), True, self.theme.snake_head)
                lvl_surf = med_font.render(f'Lv {s.level}', True, self.theme.text_muted)
                y = start_y + i * 28
                self.screen.blit(rank_surf, (self.width // 2 - 130, y))
                self.screen.blit(name_surf, (self.width // 2 - 90, y))
                self.screen.blit(score_surf, (self.width // 2 + 40, y))
                self.screen.blit(lvl_surf, (self.width // 2 + 110, y))

        back = Button(
            pygame.Rect(self.width // 2 - 90, self.height - 80, 180, 40),
            'Back', (40, 40, 55), self.theme.accent, 20, 6,
        )
        self.buttons = [back]
        for b in self.buttons:
            b.draw(self.screen, self.theme, time_s)

    def draw_settings(self, time_s: float):
        self._draw_bg(160)
        self._draw_title('SETTINGS', self.height // 6, 40)

        items_y = self.height // 3
        line_h = 44
        settings_data = [
            ('Theme', self.save.settings.theme, list(THEMES.keys())),
            ('Wrap Walls', 'On' if self.save.settings.wrap_walls else 'Off', None),
            ('Particles', 'On' if self.save.settings.particles else 'Off', None),
            ('Volume', f'{int(self.save.settings.volume * 100)}%', None),
        ]
        for i, (label, val, _) in enumerate(settings_data):
            lbl = self.font_medium.render(label, True, self.theme.text_secondary)
            vl = self.font_medium.render(val, True, self.theme.text_primary)
            y = items_y + i * line_h
            self.screen.blit(lbl, (self.width // 2 - 120, y))
            self.screen.blit(vl, (self.width // 2 + 40, y))

        arrow_left = self.font_small.render('<  >', True, self.theme.text_muted)
        self.screen.blit(arrow_left,
                         (self.width // 2 + 40 + 80, items_y))
        info = self.font_tiny.render(
            'Use UP/DOWN to select, LEFT/RIGHT to change',
            True, self.theme.text_muted)
        self.screen.blit(info, info.get_rect(center=(self.width // 2, self.height - 140)))

        back = Button(
            pygame.Rect(self.width // 2 - 90, self.height - 80, 180, 40),
            'Back', (40, 40, 55), self.theme.accent, 20, 6,
        )
        self.buttons = [back]
        for b in self.buttons:
            b.draw(self.screen, self.theme, time_s)

    def draw_hud(self, score: int, level: int, speed: float,
                 active_powerups: dict, time_s: float):
        h = self.font_medium.render(str(score), True, self.theme.text_primary)
        self.screen.blit(h, (16, 16))
        score_label = self.font_tiny.render('SCORE', True, self.theme.text_muted)
        self.screen.blit(score_label, (16, 4))

        lvl = self.font_small.render(f'LV {level}', True, self.theme.text_secondary)
        lvl_rect = lvl.get_rect(topright=(self.width - 16, 16))
        self.screen.blit(lvl, lvl_rect)

        spd_w = 80
        spd_h = 3
        spd_x = self.width - 16 - spd_w
        spd_y = 40
        pygame.draw.rect(self.screen, (30, 30, 50),
                         (spd_x, spd_y, spd_w, spd_h), border_radius=2)
        speed_pct = min(1.0, (speed - 5) / 15)
        color = self.theme.success if speed_pct < 0.5 else (
            self.theme.warning if speed_pct < 0.75 else self.theme.danger)
        pygame.draw.rect(self.screen, color,
                         (spd_x, spd_y, int(spd_w * speed_pct), spd_h),
                         border_radius=2)
        spd_lbl = self.font_tiny.render('SPEED', True, self.theme.text_muted)
        self.screen.blit(spd_lbl, (spd_x, spd_y + 6))

        bar_y = spd_y + 22

        y_offset = bar_y
        for key, (remaining, max_time) in active_powerups.items():
            from .renderer import Renderer
            color_map = {
                'shield': self.theme.powerup_shield,
                'magnet': self.theme.powerup_magnet,
                'slow': self.theme.powerup_slow,
            }
            label_map = {
                'shield': 'SHIELD', 'magnet': 'MAGNET', 'slow': 'SLOW',
            }
            color = color_map.get(key, self.theme.accent)
            label = label_map.get(key, key.upper())
            pct = max(0, remaining / max_time) if max_time > 0 else 0
            tx = 16
            ty = y_offset
            txt = self.font_tiny.render(label, True, color)
            self.screen.blit(txt, (tx, ty))
            bar_y2 = ty + txt.get_height() + 2
            pygame.draw.rect(self.screen, (40, 40, 60),
                             (tx, bar_y2, 60, 3), border_radius=2)
            if pct > 0:
                pygame.draw.rect(self.screen, color,
                                 (tx, bar_y2, int(60 * pct), 3), border_radius=2)
            y_offset += 20

    def draw_fps(self, fps: float):
        f = self.font_tiny.render(f'{int(fps)} FPS', True, (60, 60, 80))
        self.screen.blit(f, (self.width - f.get_width() - 8, self.height - f.get_height() - 4))
