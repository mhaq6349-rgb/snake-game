import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple


class Direction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    @property
    def vector(self) -> Tuple[int, int]:
        return {
            Direction.UP: (0, -1),
            Direction.DOWN: (0, 1),
            Direction.LEFT: (-1, 0),
            Direction.RIGHT: (1, 0),
        }[self]

    @property
    def opposite(self) -> 'Direction':
        return {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }[self]


class PowerUpType(Enum):
    SHIELD = auto()
    MAGNET = auto()
    SLOW = auto()


@dataclass
class Food:
    x: int
    y: int
    kind: str = 'normal'
    value: int = 10
    pulse: float = 0.0
    alive: bool = True
    lifetime: float = 0.0
    max_lifetime: float = 0.0

    @property
    def color_key(self) -> str:
        return {
            'normal': 'food_normal',
            'golden': 'food_golden',
            'bonus': 'food_bonus',
        }.get(self.kind, 'food_normal')


@dataclass
class PowerUp:
    x: int
    y: int
    ptype: PowerUpType
    lifetime: float = 8.0
    alive: bool = True
    pulse: float = 0.0

    @property
    def color_key(self) -> str:
        return {
            PowerUpType.SHIELD: 'powerup_shield',
            PowerUpType.MAGNET: 'powerup_magnet',
            PowerUpType.SLOW: 'powerup_slow',
        }[self.ptype]

    @property
    def label(self) -> str:
        return {
            PowerUpType.SHIELD: 'Shield',
            PowerUpType.MAGNET: 'Magnet',
            PowerUpType.SLOW: 'Slow',
        }[self.ptype]


class Snake:
    def __init__(self, grid_w: int, grid_h: int):
        self.grid_w = grid_w
        self.grid_h = grid_h
        start_x = grid_w // 2
        start_y = grid_h // 2
        self.body: List[Tuple[int, int]] = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y),
        ]
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.growing = False
        self.alive = True
        self.shield_active = False
        self.slow_active = False
        self.magnet_active = False
        self.score_multiplier = 1.0
        self.powerup_timers: dict = {}
        self.move_history: List[Tuple[int, int, Direction]] = []
        self._record_move()

    @property
    def head(self) -> Tuple[int, int]:
        return self.body[0]

    @property
    def length(self) -> int:
        return len(self.body)

    def _record_move(self):
        h = self.head
        self.move_history.append((h[0], h[1], self.direction))

    def set_direction(self, d: Direction):
        if d != self.direction.opposite:
            self.next_direction = d

    def update(self):
        if not self.alive:
            return
        self.direction = self.next_direction
        dx, dy = self.direction.vector
        hx, hy = self.head
        nx = hx + dx
        ny = hy + dy
        self.body.insert(0, (nx, ny))
        self._record_move()
        if not self.growing:
            self.body.pop()
            if len(self.move_history) > len(self.body) + 10:
                self.move_history.pop(0)
        else:
            self.growing = False
        max_hist = len(self.body) * 3
        while len(self.move_history) > max_hist:
            self.move_history.pop(0)

    def grow(self):
        self.growing = True

    def check_self_collision(self) -> bool:
        h = self.head
        return h in self.body[1:]

    def check_wall_collision(self, wrap: bool) -> Optional[str]:
        hx, hy = self.head
        if wrap:
            return None
        if hx < 0 or hx >= self.grid_w or hy < 0 or hy >= self.grid_h:
            return 'wall'
        return None

    def wrap_position(self):
        hx, hy = self.head
        self.body[0] = (hx % self.grid_w, hy % self.grid_h)

    def occupies(self, x: int, y: int) -> bool:
        return (x, y) in self.body

    def get_body_part(self, index: int) -> Optional[Tuple[int, int]]:
        if 0 <= index < len(self.body):
            return self.body[index]
        return None

    def apply_powerup(self, ptype: PowerUpType):
        if ptype == PowerUpType.SHIELD:
            self.shield_active = True
            self.powerup_timers['shield'] = 8.0
        elif ptype == PowerUpType.MAGNET:
            self.magnet_active = True
            self.powerup_timers['magnet'] = 6.0
        elif ptype == PowerUpType.SLOW:
            self.slow_active = True
            self.powerup_timers['slow'] = 5.0

    def update_powerups(self, dt: float, tick_ms: float):
        for key in list(self.powerup_timers.keys()):
            self.powerup_timers[key] -= dt
            if self.powerup_timers[key] <= 0:
                del self.powerup_timers[key]
                if key == 'shield':
                    self.shield_active = False
                elif key == 'magnet':
                    self.magnet_active = False
                elif key == 'slow':
                    self.slow_active = False

    def get_active_powerups(self) -> List[str]:
        return list(self.powerup_timers.keys())
