from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Theme:
    name: str
    bg: tuple  # background color
    bg_grid: tuple  # grid line color
    surface: tuple  # card/menu surface
    surface_border: tuple
    snake_head: tuple
    snake_body: tuple
    snake_body_inner: tuple
    food_normal: tuple
    food_golden: tuple
    food_bonus: tuple
    powerup_shield: tuple
    powerup_magnet: tuple
    powerup_slow: tuple
    text_primary: tuple
    text_secondary: tuple
    text_muted: tuple
    accent: tuple
    accent_glow: tuple
    success: tuple
    danger: tuple
    warning: tuple
    glow_strength: int
    cell_radius: int


DARK_NEBULA = Theme(
    name='Dark Nebula',
    bg=(10, 10, 26),
    bg_grid=(18, 18, 42),
    surface=(14, 14, 34),
    surface_border=(30, 30, 60),
    snake_head=(0, 255, 136),
    snake_body=(0, 200, 100),
    snake_body_inner=(0, 255, 150),
    food_normal=(255, 68, 119),
    food_golden=(255, 204, 0),
    food_bonus=(160, 68, 255),
    powerup_shield=(68, 136, 255),
    powerup_magnet=(255, 153, 0),
    powerup_slow=(68, 221, 255),
    text_primary=(230, 230, 240),
    text_secondary=(160, 160, 180),
    text_muted=(100, 100, 120),
    accent=(102, 68, 255),
    accent_glow=(102, 68, 255, 60),
    success=(0, 255, 136),
    danger=(255, 68, 119),
    warning=(255, 204, 0),
    glow_strength=40,
    cell_radius=6,
)

CYBERPULSE = Theme(
    name='Cyberpulse',
    bg=(5, 5, 20),
    bg_grid=(12, 12, 40),
    surface=(10, 10, 30),
    surface_border=(25, 20, 55),
    snake_head=(255, 85, 170),
    snake_body=(200, 50, 130),
    snake_body_inner=(255, 100, 180),
    food_normal=(85, 255, 255),
    food_golden=(255, 220, 50),
    food_bonus=(255, 85, 255),
    powerup_shield=(85, 170, 255),
    powerup_magnet=(255, 170, 50),
    powerup_slow=(85, 255, 200),
    text_primary=(240, 240, 250),
    text_secondary=(170, 170, 190),
    text_muted=(100, 100, 120),
    accent=(255, 85, 170),
    accent_glow=(255, 85, 170, 50),
    success=(85, 255, 170),
    danger=(255, 68, 119),
    warning=(255, 200, 50),
    glow_strength=35,
    cell_radius=5,
)

AURORA = Theme(
    name='Aurora',
    bg=(10, 15, 30),
    bg_grid=(16, 22, 45),
    surface=(14, 20, 38),
    surface_border=(28, 34, 58),
    snake_head=(130, 255, 200),
    snake_body=(80, 200, 150),
    snake_body_inner=(100, 255, 180),
    food_normal=(255, 150, 100),
    food_golden=(255, 220, 80),
    food_bonus=(180, 120, 255),
    powerup_shield=(100, 180, 255),
    powerup_magnet=(255, 180, 80),
    powerup_slow=(100, 255, 220),
    text_primary=(230, 240, 240),
    text_secondary=(160, 180, 180),
    text_muted=(90, 110, 110),
    accent=(130, 255, 200),
    accent_glow=(130, 255, 200, 40),
    success=(130, 255, 200),
    danger=(255, 100, 100),
    warning=(255, 200, 80),
    glow_strength=30,
    cell_radius=6,
)

THEMES: Dict[str, Theme] = {
    'Dark Nebula': DARK_NEBULA,
    'Cyberpulse': CYBERPULSE,
    'Aurora': AURORA,
}
