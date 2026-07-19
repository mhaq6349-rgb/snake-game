# Snake — Neon Protocol

Premium Snake game with dark neon aesthetics, procedural audio, particle effects, power-ups, progressive difficulty, and high-score persistence.

## Features

- **3 visual themes** — Dark Nebula, Cyberpulse, Aurora
- **Smooth movement** — fixed-timestep game loop with interpolation
- **3 food types** — Normal (10pts), Golden (50pts, timed), Bonus (25pts, spawns 2 more)
- **4 power-ups** — Shield (blocks one collision), Magnet (attracts food), Slow (reduces speed)
- **Particle system** — eat bursts, death explosions, sparkle effects
- **Procedural audio** — eat, death, power-up, level-up, menu sounds (no external files)
- **Progressive difficulty** — speed increases every 5 food, obstacles from level 3
- **High scores** — persistent top 10 with name entry
- **Settings** — theme, wrap walls, particles toggle, volume control
- **Keyboard + mouse** controls

## Install

```bash
pip install -r requirements.txt
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move snake |
| Esc / P | Pause |
| Enter / Space | Menu select |
| Mouse click | Button select |

## Themes

| Theme | Snake | Food | Vibe |
|-------|-------|------|------|
| Dark Nebula | Neon green | Pink | Classic dark |
| Cyberpulse | Neon pink | Cyan | Synthwave |
| Aurora | Mint | Coral | Nature-neon |

## Project Structure

```
snake-game/
├── main.py            # Entry point
├── requirements.txt
├── README.md
└── game/
    ├── __init__.py
    ├── core.py        # Game loop, state machine, input
    ├── entities.py    # Snake, Food, PowerUp
    ├── particles.py   # Particle system
    ├── renderer.py    # Grid, glow, effects rendering
    ├── ui.py          # Menus, HUD, overlays
    ├── audio.py       # Procedural audio synthesis
    ├── themes.py      # Color themes
    └── save.py        # High score persistence
```
