import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import List, Optional
from pathlib import Path


SAVE_DIR = Path.home() / '.snake_game'
SCORES_FILE = SAVE_DIR / 'scores.json'
SETTINGS_FILE = SAVE_DIR / 'settings.json'
MAX_SCORES = 10


@dataclass
class ScoreEntry:
    name: str
    score: int
    level: int = 1
    food_eaten: int = 0
    date: str = ''

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime('%Y-%m-%d %H:%M')


@dataclass
class GameSettings:
    theme: str = 'Dark Nebula'
    volume: float = 0.7
    wrap_walls: bool = False
    show_grid: bool = True
    particles: bool = True


class HighScoreManager:
    def __init__(self):
        self._ensure_dir()
        self.scores: List[ScoreEntry] = self._load_scores()
        self.settings: GameSettings = self._load_settings()

    def _ensure_dir(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_scores(self) -> List[ScoreEntry]:
        if not SCORES_FILE.exists():
            return []
        try:
            with open(SCORES_FILE) as f:
                data = json.load(f)
            return [ScoreEntry(**entry) for entry in data[:MAX_SCORES]]
        except (json.JSONDecodeError, KeyError, TypeError):
            return []

    def _save_scores(self):
        data = [asdict(s) for s in self.scores[:MAX_SCORES]]
        with open(SCORES_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_settings(self) -> GameSettings:
        if not SETTINGS_FILE.exists():
            return GameSettings()
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
            return GameSettings(**data)
        except (json.JSONDecodeError, TypeError):
            return GameSettings()

    def _save_settings(self):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(asdict(self.settings), f, indent=2)

    def add_score(self, name: str, score: int, level: int, food: int) -> int:
        entry = ScoreEntry(name=name, score=score, level=level, food_eaten=food)
        self.scores.append(entry)
        self.scores.sort(key=lambda s: s.score, reverse=True)
        self.scores = self.scores[:MAX_SCORES]
        self._save_scores()
        rank = next(i for i, s in enumerate(self.scores) if s is entry)
        return rank

    def is_high_score(self, score: int) -> bool:
        if not self.scores:
            return score > 0
        return len(self.scores) < MAX_SCORES or score > self.scores[-1].score

    def get_top_scores(self) -> List[ScoreEntry]:
        return self.scores[:MAX_SCORES]

    def update_setting(self, key: str, value):
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            self._save_settings()

    def get_setting(self, key: str):
        return getattr(self.settings, key, None)
