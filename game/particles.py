import math
import random
from typing import List, Optional, Tuple

import pygame


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'color', 'size',
                 'start_size', 'end_size', 'gravity', 'friction', 'alpha_decay')

    def __init__(self, x: float, y: float, vx: float, vy: float,
                 color: Tuple[int, int, int], life: float = 0.6,
                 size: float = 4.0, gravity: float = 0,
                 friction: float = 0.98):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.start_size = size
        self.end_size = size * 0.1
        self.gravity = gravity
        self.friction = friction
        self.alpha_decay = 255.0 / life if life > 0 else 255

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float):
        self.vx *= self.friction
        self.vy *= self.friction
        self.vy += self.gravity * dt
        self.x += self.vx * dt * 60
        self.y += self.vy * dt * 60
        self.life -= dt
        t = 1.0 - max(0, self.life / self.max_life)
        self.size = self.start_size + (self.end_size - self.start_size) * t

    def draw(self, surface: pygame.Surface, offset_x: float, offset_y: float, alpha_scale: float = 1.0):
        t = 1.0 - max(0, self.life / self.max_life)
        alpha = max(0, min(255, int((1 - t) * 255 * alpha_scale)))
        if alpha < 2:
            return
        color = (*self.color[:3], alpha)
        pos = (int(self.x + offset_x), int(self.y + offset_y))
        r = max(1, int(self.size))
        surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (r, r), r)
        surface.blit(surf, (pos[0] - r, pos[1] - r))


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def emit(self, x: float, y: float, count: int = 12,
             color: Tuple[int, int, int] = (255, 255, 255),
             speed: float = 120, life: float = 0.5,
             size: float = 4, gravity: float = 40,
             spread: float = math.pi * 2):
        for _ in range(count):
            angle = random.uniform(0, spread)
            spd = random.uniform(speed * 0.3, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd
            c = (
                max(0, min(255, color[0] + random.randint(-30, 30))),
                max(0, min(255, color[1] + random.randint(-30, 30))),
                max(0, min(255, color[2] + random.randint(-30, 30))),
            )
            sz = random.uniform(size * 0.5, size * 1.5)
            lt = random.uniform(life * 0.6, life * 1.4)
            self.particles.append(
                Particle(x, y, vx, vy, c, lt, sz, gravity))

    def burst(self, x: float, y: float, color: Tuple[int, int, int],
              count: int = 20, speed: float = 150):
        self.emit(x, y, count, color, speed, 0.4, 5, 50)

    def trail(self, x: float, y: float, color: Tuple[int, int, int],
              count: int = 2, speed: float = 30):
        self.emit(x, y, count, color, speed, 0.3, 3, 20, math.pi * 0.5)

    def sparkle(self, x: float, y: float, color: Tuple[int, int, int]):
        self.emit(x, y, 6, color, 80, 0.25, 2, 10)

    def update(self, dt: float):
        dead = []
        for p in self.particles:
            p.update(dt)
            if not p.alive:
                dead.append(p)
        for p in dead:
            self.particles.remove(p)

    def draw(self, surface: pygame.Surface, offset_x: float = 0, offset_y: float = 0):
        for p in self.particles:
            p.draw(surface, offset_x, offset_y)

    def clear(self):
        self.particles.clear()
