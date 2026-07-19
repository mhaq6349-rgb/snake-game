import math
from typing import List, Tuple

import pygame

from .themes import Theme


class FloatingText:
    __slots__ = ('x', 'y', 'text', 'color', 'life', 'max_life', 'vy')

    def __init__(self, x: float, y: float, text: str,
                 color: Tuple[int, int, int], life: float = 0.8):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = life
        self.max_life = life
        self.vy = -60

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float):
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface: pygame.Surface):
        t = 1.0 - max(0, self.life / self.max_life)
        alpha = max(0, min(255, int((1 - t) * 255)))
        if alpha < 4:
            return
        font = pygame.font.Font(None, 20)
        txt = font.render(self.text, True, (*self.color, alpha))
        txt.set_alpha(alpha)
        r = txt.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(txt, r)


class Renderer:
    def __init__(self, theme: Theme, grid_w: int, grid_h: int, cell_size: int):
        self.theme = theme
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.cell_size = cell_size
        self.grid_px_w = grid_w * cell_size
        self.grid_px_h = grid_h * cell_size
        self._glow_cache = {}
        self._font_cache = {}
        self.shake_x = 0.0
        self.shake_y = 0.0
        self.shake_decay = 0.92

    def set_theme(self, theme: Theme):
        self.theme = theme
        self._glow_cache.clear()

    def _glow_surface(self, color: Tuple[int, int, int], radius: int,
                      strength: int) -> pygame.Surface:
        key = (color, radius, strength)
        if key in self._glow_cache:
            return self._glow_cache[key]
        size = radius * 2 + 4
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        steps = max(1, strength // 2)
        for i in range(steps, 0, -1):
            alpha = max(1, int(255 * (i / steps) * 0.28))
            r = radius + i
            pygame.draw.circle(surf, (*color, alpha), (size // 2, size // 2), r)
        self._glow_cache[key] = surf
        return surf

    def trigger_shake(self, intensity: float = 6.0):
        self.shake_x = intensity
        self.shake_y = intensity

    def get_shake_offset(self) -> Tuple[int, int]:
        if abs(self.shake_x) < 0.3 and abs(self.shake_y) < 0.3:
            return 0, 0
        import random as _r
        ox = int(self.shake_x * _r.choice((-1, 1)))
        oy = int(self.shake_y * _r.choice((-1, 1)))
        self.shake_x *= self.shake_decay
        self.shake_y *= self.shake_decay
        if abs(self.shake_x) < 0.1:
            self.shake_x = 0
        if abs(self.shake_y) < 0.1:
            self.shake_y = 0
        return ox, oy

    def draw_grid(self, surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0,
                  show_grid: bool = True):
        t = self.theme
        # Darker grid lines
        if show_grid:
            grid_color = t.bg_grid
            for gy in range(self.grid_h + 1):
                y = gy * self.cell_size + offset_y
                w = 1 if gy % 5 == 0 else 1
                pygame.draw.line(surface, grid_color,
                                 (offset_x, y), (offset_x + self.grid_px_w, y), w)
            for gx in range(self.grid_w + 1):
                x = gx * self.cell_size + offset_x
                w = 1 if gx % 5 == 0 else 1
                pygame.draw.line(surface, grid_color,
                                 (x, offset_y), (x, offset_y + self.grid_px_h), w)

        # Outer glow border
        border_rect = pygame.Rect(offset_x - 2, offset_y - 2,
                                  self.grid_px_w + 4, self.grid_px_h + 4)
        glow_surf = self._glow_surface(t.accent, 6, 14)
        for dx, dy in [(0, 0), (4, 0), (0, 4), (4, 4)]:
            surface.blit(glow_surf,
                         (offset_x - glow_surf.get_width() // 2 + dx,
                          offset_y - glow_surf.get_height() // 2 + dy),
                         special_flags=pygame.BLEND_ALPHA_SDL2)
            surface.blit(glow_surf,
                         (offset_x + self.grid_px_w - glow_surf.get_width() // 2 + dx,
                          offset_y + self.grid_px_h - glow_surf.get_height() // 2 + dy),
                         special_flags=pygame.BLEND_ALPHA_SDL2)

        # Main border
        pygame.draw.rect(surface, t.surface_border, border_rect, 2, 10)
        # Inner highlight
        inner_rect = pygame.Rect(offset_x - 1, offset_y - 1,
                                 self.grid_px_w + 2, self.grid_px_h + 2)
        pygame.draw.rect(surface, (*t.accent, 20), inner_rect, 1, 9)

        # Corner ornaments
        orn_size = 8
        orn_color = (*t.accent, 60)
        corners = [
            (offset_x - orn_size, offset_y - orn_size, 1, 1),
            (offset_x + self.grid_px_w - 2, offset_y - orn_size, -1, 1),
            (offset_x - orn_size, offset_y + self.grid_px_h - 2, 1, -1),
            (offset_x + self.grid_px_w - 2, offset_y + self.grid_px_h - 2, -1, -1),
        ]
        for cx, cy, sdx, sdy in corners:
            points = [
                (cx, cy + orn_size * sdy * -1),
                (cx, cy),
                (cx + orn_size * sdx, cy),
            ]
            pygame.draw.lines(surface, orn_color, False, points, 2)

    def draw_cell(self, surface: pygame.Surface, gx: int, gy: int,
                  color: Tuple[int, int, int], radius: int = 0,
                  glow: bool = True, alpha: int = 255,
                  offset_x: int = 0, offset_y: int = 0):
        if radius <= 0:
            radius = self.theme.cell_radius
        cx = gx * self.cell_size + self.cell_size // 2 + offset_x
        cy = gy * self.cell_size + self.cell_size // 2 + offset_y
        cs = self.cell_size - 2
        if glow:
            glow_surf = self._glow_surface(color, cs // 2, self.theme.glow_strength)
            gx_pos = cx - glow_surf.get_width() // 2
            gy_pos = cy - glow_surf.get_height() // 2
            surface.blit(glow_surf, (gx_pos, gy_pos), special_flags=pygame.BLEND_ALPHA_SDL2)
        rect = pygame.Rect(
            gx * self.cell_size + 1 + offset_x,
            gy * self.cell_size + 1 + offset_y,
            self.cell_size - 2,
            self.cell_size - 2,
        )
        if alpha < 255:
            s = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
            surface.blit(s, rect.topleft)
        else:
            pygame.draw.rect(surface, color, rect, border_radius=radius)

    def draw_snake(self, surface: pygame.Surface, body: List[Tuple[int, int]],
                   time_s: float = 0, offset_x: int = 0, offset_y: int = 0):
        if not body:
            return
        t = self.theme
        seg_count = len(body)

        # Draw body segments (back to front)
        for i in range(seg_count - 1, 0, -1):
            gx, gy = body[i]
            prev = body[i - 1]
            if abs(gx - prev[0]) > 1 or abs(gy - prev[1]) > 1:
                continue
            progress = i / max(seg_count - 1, 1)
            # Gradient from body color to inner color with honeycomb-like variation
            r, g, b = t.snake_body
            tr, tg, tb = t.snake_body_inner
            wave = math.sin(i * 1.2 + time_s * 2) * 0.1 + 0.9
            blend = (i % 4) / 4.0
            color = (
                max(0, min(255, int((r + (tr - r) * blend) * wave))),
                max(0, min(255, int((g + (tg - g) * blend) * wave))),
                max(0, min(255, int((b + (tb - b) * blend) * wave))),
            )
            rad = max(2, t.cell_radius - int(progress * 2))
            self.draw_cell(surface, gx, gy, color, rad,
                           glow=(i < min(6, seg_count) and i > 0),
                           alpha=255 - int(progress * 60),
                           offset_x=offset_x, offset_y=offset_y)

            # Scale pattern on body
            if i % 2 == 0 and seg_count > 3:
                scale_size = max(2, self.cell_size // 6)
                scx = gx * self.cell_size + self.cell_size // 2 + offset_x
                scy = gy * self.cell_size + self.cell_size // 2 + offset_y
                sc = pygame.Surface((scale_size, scale_size), pygame.SRCALPHA)
                alpha_sc = max(10, 40 - int(progress * 30))
                pygame.draw.circle(sc, (*t.snake_head, alpha_sc),
                                   (scale_size // 2, scale_size // 2), scale_size // 2)
                surface.blit(sc, (scx - scale_size // 2, scy - scale_size // 2))

        # Draw head last (on top)
        gx, gy = body[0]
        head_color = t.snake_head
        pulse = math.sin(time_s * 4) * 10 + self.theme.glow_strength
        self.draw_cell(surface, gx, gy, head_color, t.cell_radius + 2,
                       glow=True, offset_x=offset_x, offset_y=offset_y)
        self._draw_snake_head_details(surface, gx, gy, body, time_s, offset_x, offset_y)

    def _draw_snake_head_details(self, surface: pygame.Surface, gx: int, gy: int,
                                  body: List[Tuple[int, int]], time_s: float,
                                  ox: int, oy: int):
        cs = self.cell_size
        cx = gx * cs + cs // 2 + ox
        cy = gy * cs + cs // 2 + oy
        next_seg = body[1] if len(body) > 1 else None
        if next_seg:
            dx = next_seg[0] - gx
            dy = next_seg[1] - gy
        else:
            dx, dy = 1, 0

        # Eye positions based on direction
        perp_x, perp_y = -dy, dx
        eye_offset = cs // 5
        eye_radius = max(2, cs // 7)
        pupil_radius = max(1, eye_radius // 2)

        # Eyes with glow
        for side in (-1, 1):
            ex = cx + perp_x * eye_offset
            ey = cy + perp_y * eye_offset
            # Eye white
            pygame.draw.circle(surface, (240, 240, 250), (ex, ey), eye_radius)
            # Pupil looking in movement direction
            px = ex + dx * (eye_radius // 2)
            py = ey + dy * (eye_radius // 2)
            pygame.draw.circle(surface, (5, 5, 20), (px, py), pupil_radius)
            # Eye shine
            shine_x = ex - dx * (eye_radius // 3)
            shine_y = ey - dy * (eye_radius // 3)
            pygame.draw.circle(surface, (255, 255, 255, 160),
                               (shine_x, shine_y), max(1, eye_radius // 4))

        # Tongue (flickers)
        tongue_len = cs // 2
        if math.sin(time_s * 8) > 0:
            tip_x = cx + dx * (cs // 2 + tongue_len)
            tip_y = cy + dy * (cs // 2 + tongue_len)
            mid_x = cx + dx * (cs // 2 + tongue_len // 2)
            mid_y = cy + dy * (cs // 2 + tongue_len // 2)
            pygame.draw.line(surface, self.theme.danger,
                             (mid_x, mid_y), (tip_x, tip_y), 2)
            # Fork
            fork_x = tip_x + perp_x * 3
            fork_y = tip_y + perp_y * 3
            pygame.draw.line(surface, self.theme.danger,
                             (tip_x, tip_y), (fork_x, fork_y), 1)
            fork_x2 = tip_x - perp_x * 3
            fork_y2 = tip_y - perp_y * 3
            pygame.draw.line(surface, self.theme.danger,
                             (tip_x, tip_y), (fork_x2, fork_y2), 1)

    def draw_food(self, surface: pygame.Surface, foods: list, time_s: float,
                  offset_x: int = 0, offset_y: int = 0):
        for food in foods:
            if not food.alive:
                continue
            pulse = math.sin(time_s * 3 + food.x * 0.5) * 0.12 + 1.0
            color_key = food.color_key
            color = getattr(self.theme, color_key, self.theme.food_normal)
            size = max(1, int(self.cell_size * 0.45 * pulse))
            cx = food.x * self.cell_size + self.cell_size // 2 + offset_x
            cy = food.y * self.cell_size + self.cell_size // 2 + offset_y

            # Glow
            glow_surf = self._glow_surface(
                color, size + 4, int(self.theme.glow_strength * 0.5))
            surface.blit(glow_surf,
                         (cx - glow_surf.get_width() // 2,
                          cy - glow_surf.get_height() // 2),
                         special_flags=pygame.BLEND_ALPHA_SDL2)

            if food.kind == 'golden':
                self._draw_golden_star(surface, cx, cy, size, color)
            elif food.kind == 'bonus':
                self._draw_bonus_gem(surface, cx, cy, size, color, time_s)
            else:
                self._draw_orange(surface, cx, cy, size, color, time_s)

    def _draw_orange(self, surface: pygame.Surface, cx: int, cy: int,
                     size: int, color: Tuple[int, int, int], time_s: float):
        s = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        # Main orange body
        orange_color = (255, 140, 0) if color == self.theme.food_normal else color
        pygame.draw.circle(s, orange_color, (size + 2, size + 2), size)
        # Lighter segment lines (citrus segments)
        for i in range(6):
            angle = i * math.pi / 3 + math.sin(time_s * 0.5) * 0.1
            px = size + 2 + math.cos(angle) * size * 0.6
            py = size + 2 + math.sin(angle) * size * 0.6
            pygame.draw.line(s, (255, 180, 50, 80), (size + 2, size + 2),
                             (px, py), 1)
        # Inner circle highlight
        pygame.draw.circle(s, (255, 200, 100, 60), (size + 2, size + 2), size * 0.5)
        # Skin texture dots
        for _ in range(8):
            dot_x = random_pos(size * 0.7, size + 2)
            dot_y = random_pos(size * 0.7, size + 2)
            pygame.draw.circle(s, (220, 120, 0, 40),
                               (int(dot_x) + 2, int(dot_y) + 2), 1)
        # Green leaf on top
        leaf_w = size // 3
        leaf_h = size // 2
        leaf_x = size + 2 - leaf_w // 2 + math.sin(time_s * 2) * 2
        leaf_y = size + 2 - size - 2
        leaf_points = [
            (leaf_x, leaf_y + leaf_h),
            (leaf_x + leaf_w // 2, leaf_y),
            (leaf_x + leaf_w, leaf_y + leaf_h),
        ]
        pygame.draw.polygon(s, (50, 180, 50, 220), leaf_points)
        # Stem
        pygame.draw.line(s, (80, 60, 30, 200),
                         (leaf_x + leaf_w // 2, leaf_y),
                         (leaf_x + leaf_w // 2, leaf_y - 3), 2)
        # Highlight/shine
        shine = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(shine, (255, 255, 255, 30),
                           (size // 3, size // 3), size // 3)
        s.blit(shine, (size // 4, size // 4))
        surface.blit(s, (cx - size - 2, cy - size - 2))

    def _draw_golden_star(self, surface: pygame.Surface, cx: int, cy: int,
                          size: int, color: Tuple[int, int, int]):
        s = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        points = []
        for i in range(5):
            angle = -math.pi / 2 + i * 2 * math.pi / 5
            px = size + 2 + math.cos(angle) * size
            py = size + 2 + math.sin(angle) * size
            points.append((px, py))
        pygame.draw.polygon(s, (*color, 255), points)
        glow_points = []
        for i in range(5):
            angle = -math.pi / 2 + i * 2 * math.pi / 5
            px = size + 2 + math.cos(angle) * (size + 3)
            py = size + 2 + math.sin(angle) * (size + 3)
            glow_points.append((px, py))
        pygame.draw.polygon(s, (*color, 60), glow_points, 1)
        pygame.draw.polygon(s, (255, 255, 255, 60), points, 1)
        surface.blit(s, (cx - size - 2, cy - size - 2))

    def _draw_bonus_gem(self, surface: pygame.Surface, cx: int, cy: int,
                        size: int, color: Tuple[int, int, int], time_s: float):
        s = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        rot = math.sin(time_s * 0.5)
        points = []
        for i in range(4):
            angle = math.pi / 4 + i * math.pi / 2 + rot * 0.2
            px = size + 2 + math.cos(angle) * size
            py = size + 2 + math.sin(angle) * size
            points.append((px, py))
        pygame.draw.polygon(s, (*color, 255), points)
        inner = [(x * 0.6 + (size + 2) * 0.4, y * 0.6 + (size + 2) * 0.4)
                 for x, y in points]
        pygame.draw.polygon(s, (255, 255, 255, 40), inner)
        surface.blit(s, (cx - size - 2, cy - size - 2))

    def draw_powerups(self, surface: pygame.Surface, powerups: list, time_s: float,
                      offset_x: int = 0, offset_y: int = 0):
        for pu in powerups:
            if not pu.alive:
                continue
            pulse = math.sin(time_s * 4 + pu.x) * 0.2 + 1.0
            color = getattr(self.theme, pu.color_key, self.theme.accent)
            cx = pu.x * self.cell_size + self.cell_size // 2 + offset_x
            cy = pu.y * self.cell_size + self.cell_size // 2 + offset_y
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
            pygame.draw.rect(surf, (*color, 255), surf.get_rect(), border_radius=s // 2)
            icon = pygame.font.Font(None, max(10, s))
            label = {'shield': 'S', 'magnet': 'M', 'slow': '!'}.get(
                pu.ptype.name.lower() if hasattr(pu.ptype, 'name') else '', '?')
            icon_txt = icon.render(label, True, (255, 255, 255, 200))
            ir = icon_txt.get_rect(center=(s, s))
            surf.blit(icon_txt, ir)
            surface.blit(surf, rect.topleft)

    def draw_obstacles(self, surface: pygame.Surface, obstacles: list,
                       offset_x: int = 0, offset_y: int = 0):
        for ox, oy in obstacles:
            self.draw_cell(surface, ox, oy, self.theme.text_muted,
                           radius=3, glow=False, offset_x=offset_x, offset_y=offset_y)
            inner = self.cell_size // 3
            cx = ox * self.cell_size + self.cell_size // 2 + offset_x
            cy = oy * self.cell_size + self.cell_size // 2 + offset_y
            s = pygame.Surface((inner, inner), pygame.SRCALPHA)
            pygame.draw.rect(s, (*self.theme.danger, 80), s.get_rect(), border_radius=2)
            pygame.draw.line(s, (*self.theme.danger, 120),
                             (0, 0), (inner, inner), 1)
            pygame.draw.line(s, (*self.theme.danger, 120),
                             (inner, 0), (0, inner), 1)
            surface.blit(s, (cx - inner // 2, cy - inner // 2))

    def draw_floating_texts(self, surface: pygame.Surface, texts: List[FloatingText]):
        for ft in texts:
            ft.draw(surface)


def random_pos(span: float, center: float) -> float:
    return center + (hash(str(center)) % 1000 - 500) / 500 * span * 0.5
