import math
from typing import Tuple

import pygame

from .themes import Theme


class Renderer:
    def __init__(self, theme: Theme, grid_w: int, grid_h: int, cell_size: int):
        self.theme = theme
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell_size = cell_size
        self.grid_px_w = grid_w * cell_size
        self.grid_px_h = grid_h * cell_size
        self._glow_cache = {}
        self._surfaces = {}

    def set_theme(self, theme: Theme):
        self.theme = theme
        self._glow_cache.clear()
        self._surfaces.clear()

    def _glow_surface(self, color: Tuple[int, int, int], radius: int,
                      strength: int) -> pygame.Surface:
        key = (color, radius, strength)
        if key in self._glow_cache:
            return self._glow_cache[key]
        size = radius * 2 + 4
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        for i in range(strength // 2, 0, -1):
            alpha = max(1, int(255 * (i / (strength // 2)) * 0.3))
            r = radius + i
            pygame.draw.circle(surf, (*color, alpha), (size // 2, size // 2), r)
        self._glow_cache[key] = surf
        return surf

    def _cell_rect(self, gx: int, gy: int) -> pygame.Rect:
        return pygame.Rect(
            gx * self.cell_size,
            gy * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def draw_grid(self, surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0,
                  show_grid: bool = True):
        if show_grid:
            for gy in range(self.grid_h + 1):
                y = gy * self.cell_size + offset_y
                pygame.draw.line(surface, self.theme.bg_grid,
                                 (offset_x, y), (offset_x + self.grid_px_w, y), 1)
            for gx in range(self.grid_w + 1):
                x = gx * self.cell_size + offset_x
                pygame.draw.line(surface, self.theme.bg_grid,
                                 (x, offset_y), (x, offset_y + self.grid_px_h), 1)
        border_rect = pygame.Rect(offset_x, offset_y,
                                  self.grid_px_w, self.grid_px_h)
        pygame.draw.rect(surface, self.theme.surface_border, border_rect, 2, 8)

    def draw_cell(self, surface: pygame.Surface, gx: int, gy: int,
                  color: Tuple[int, int, int], radius: int = 0,
                  glow: bool = True, alpha: int = 255):
        if radius <= 0:
            radius = self.theme.cell_radius
        cx = gx * self.cell_size + self.cell_size // 2 + 0
        cy = gy * self.cell_size + self.cell_size // 2 + 0
        cs = self.cell_size - 2
        if glow:
            glow_surf = self._glow_surface(color, cs // 2, self.theme.glow_strength)
            gx_pos = cx - glow_surf.get_width() // 2
            gy_pos = cy - glow_surf.get_height() // 2
            surface.blit(glow_surf, (gx_pos, gy_pos), special_flags=pygame.BLEND_ALPHA_SDL2)
        rect = pygame.Rect(
            gx * self.cell_size + 1,
            gy * self.cell_size + 1,
            self.cell_size - 2,
            self.cell_size - 2,
        )
        if alpha < 255:
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (*color, alpha), s.get_rect(),
                             border_radius=radius)
            surface.blit(s, rect.topleft)
        else:
            pygame.draw.rect(surface, color, rect, border_radius=radius)

    def draw_snake(self, surface: pygame.Surface, body: list, interpolation: float = 0):
        if not body:
            return
        t = self.theme
        seg_count = len(body)
        for i, (gx, gy) in enumerate(body):
            progress = i / max(seg_count - 1, 1)
            if i == 0:
                color = t.snake_head
                radius = t.cell_radius + 1
                size_pct = 1.0
            else:
                r, g, b = t.snake_body
                target_r, target_g, target_b = t.snake_body_inner
                blend = (i % 3) / 3.0
                color = (
                    int(r + (target_r - r) * blend),
                    int(g + (target_g - g) * blend),
                    int(b + (target_b - b) * blend),
                )
                radius = t.cell_radius
                size_pct = max(0.7, 1.0 - progress * 0.3)
            skip = 0
            if i > 0:
                prev = body[i - 1]
                if abs(gx - prev[0]) > 1 or abs(gy - prev[1]) > 1:
                    skip = 1
            if skip:
                continue
            self.draw_cell(surface, gx, gy, color, radius,
                           glow=(i < min(5, seg_count)))
            if i == 0:
                self._draw_snake_eyes(surface, gx, gy, body[1] if len(body) > 1 else None)

    def _draw_snake_eyes(self, surface: pygame.Surface, gx: int, gy: int,
                         next_seg: Tuple[int, int]):
        cs = self.cell_size
        cx = gx * cs + cs // 2
        cy = gy * cs + cs // 2
        eye_offset = cs // 6
        eye_radius = max(2, cs // 8)
        pupil_radius = max(1, eye_radius // 2)
        if next_seg:
            dx = next_seg[0] - gx
            dy = next_seg[1] - gy
        else:
            dx, dy = 1, 0
        perp_x, perp_y = -dy, dx
        for side in (-1, 1):
            ex = cx + perp_x * eye_offset
            ey = cy + perp_y * eye_offset
            pygame.draw.circle(surface, (255, 255, 255), (ex, ey), eye_radius)
            px = ex + dx * (eye_radius // 2)
            py = ey + dy * (eye_radius // 2)
            pygame.draw.circle(surface, (5, 5, 20), (px, py), pupil_radius)

    def draw_food(self, surface: pygame.Surface, foods: list, time_s: float):
        for food in foods:
            if not food.alive:
                continue
            pulse = math.sin(time_s * 3 + food.x * 0.5) * 0.15 + 1.0
            color_key = food.color_key
            color = getattr(self.theme, color_key, self.theme.food_normal)
            size = max(1, int(self.cell_size * 0.5 * pulse))
            cx = food.x * self.cell_size + self.cell_size // 2
            cy = food.y * self.cell_size + self.cell_size // 2
            glow_surf = self._glow_surface(
                color, size + 4, int(self.theme.glow_strength * 0.6))
            gx_pos = cx - glow_surf.get_width() // 2
            gy_pos = cy - glow_surf.get_height() // 2
            surface.blit(glow_surf, (gx_pos, gy_pos),
                         special_flags=pygame.BLEND_ALPHA_SDL2)
            rect = pygame.Rect(0, 0, size * 2, size * 2)
            rect.center = (cx, cy)
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            if food.kind == 'golden':
                points = []
                for i in range(5):
                    angle = -math.pi / 2 + i * 2 * math.pi / 5
                    px = size + math.cos(angle) * size
                    py = size + math.sin(angle) * size
                    points.append((px, py))
                pygame.draw.polygon(s, (*color, 255), points)
                pygame.draw.polygon(s, (255, 255, 255, 60), points, 1)
            else:
                pygame.draw.circle(s, (*color, 255), (size, size), size)
                highlight = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(highlight, (255, 255, 255, 40),
                                   (size // 3, size // 3), size // 3)
                s.blit(highlight, (size // 4, size // 3))
            surface.blit(s, rect.topleft)

    def draw_powerups(self, surface: pygame.Surface, powerups: list, time_s: float):
        for pu in powerups:
            if not pu.alive:
                continue
            pulse = math.sin(time_s * 4 + pu.x) * 0.2 + 1.0
            color = getattr(self.theme, pu.color_key, self.theme.accent)
            cx = pu.x * self.cell_size + self.cell_size // 2
            cy = pu.y * self.cell_size + self.cell_size // 2
            s = int(self.cell_size * 0.55 * pulse)
            glow_surf = self._glow_surface(
                color, s + 3, int(self.theme.glow_strength * 0.5))
            surface.blit(glow_surf,
                         (cx - glow_surf.get_width() // 2,
                          cy - glow_surf.get_height() // 2),
                         special_flags=pygame.BLEND_ALPHA_SDL2)
            rect = pygame.Rect(0, 0, s * 2, s * 2)
            rect.center = (cx, cy)
            surf = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(surf, (*color, 255), surf.get_rect(),
                             border_radius=s // 2)
            inner = pygame.Surface((s, s), pygame.SRCALPHA)
            inner_rect = pygame.Rect(s // 4, s // 4, s, s)
            pygame.draw.rect(inner, (255, 255, 255, 30), inner_rect,
                             border_radius=s // 4)
            surf.blit(inner, (s // 4, s // 4))
            surface.blit(surf, rect.topleft)

    def draw_powerup_indicator(self, surface: pygame.Surface, x: int, y: int,
                               key: str, remaining: float, max_time: float):
        color_map = {
            'shield': self.theme.powerup_shield,
            'magnet': self.theme.powerup_magnet,
            'slow': self.theme.powerup_slow,
        }
        label_map = {
            'shield': 'SHIELD',
            'magnet': 'MAGNET',
            'slow': 'SLOW',
        }
        color = color_map.get(key, self.theme.accent)
        label = label_map.get(key, key.upper())
        pct = max(0, remaining / max_time) if max_time > 0 else 0
        bar_w = 60
        bar_h = 4
        font = pygame.font.Font(None, 14)
        txt = font.render(label, True, color)
        tx = x
        ty = y - txt.get_height() - 6
        surface.blit(txt, (tx, ty))
        pygame.draw.rect(surface, (40, 40, 60),
                         (tx, ty + txt.get_height() + 2, bar_w, bar_h),
                         border_radius=2)
        if pct > 0:
            pygame.draw.rect(surface, color,
                             (tx, ty + txt.get_height() + 2,
                              int(bar_w * pct), bar_h),
                             border_radius=2)

    def draw_obstacles(self, surface: pygame.Surface, obstacles: list):
        for ox, oy in obstacles:
            self.draw_cell(surface, ox, oy, self.theme.text_muted,
                           radius=3, glow=False)
            inner = self.cell_size // 3
            cx = ox * self.cell_size + self.cell_size // 2
            cy = oy * self.cell_size + self.cell_size // 2
            s = pygame.Surface((inner, inner), pygame.SRCALPHA)
            pygame.draw.rect(s, (*self.theme.danger, 80), s.get_rect(),
                             border_radius=2)
            surface.blit(s, (cx - inner // 2, cy - inner // 2))
