import struct
import wave
import io
import math
import random
import threading
from pathlib import Path
from typing import Optional

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False


SAMPLE_RATE = 22050
MAX_AMPLITUDE = 32767


def _sine(freq: float, t: float) -> float:
    return math.sin(2 * math.pi * freq * t)


def _square(freq: float, t: float) -> float:
    return 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0


def _noise(t: float) -> float:
    return random.uniform(-1, 1)


def _adsr(t: float, attack: float, decay: float, sustain: float, release: float, dur: float) -> float:
    if t < attack:
        return t / attack
    t -= attack
    if t < decay:
        return 1.0 - (1.0 - sustain) * (t / decay)
    t -= decay
    sustain_end = dur - release
    if t < sustain_end:
        return sustain
    t -= sustain_end
    if t < release:
        return sustain * (1.0 - t / release)
    return 0.0


def _generate_wav(frames: int, samples_per_frame: int) -> io.BytesIO:
    buf = io.BytesIO()
    n_samples = frames * samples_per_frame
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        data = struct.pack('<' + 'h' * n_samples, *samples)
        wf.writeframes(data)
    buf.seek(0)
    return buf


class Sound:
    def __init__(self, duration: float, generator):
        self.duration = duration
        self.generator = generator
        self._buffer: Optional[io.BytesIO] = None
        self._pygame_sound = None

    def _render(self) -> io.BytesIO:
        n_samples = int(SAMPLE_RATE * self.duration)
        samples = []
        for i in range(n_samples):
            t = i / SAMPLE_RATE
            val = self.generator(t, self.duration)
            val = max(-1.0, min(1.0, val))
            samples.append(int(val * MAX_AMPLITUDE))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            data = struct.pack('<' + 'h' * n_samples, *samples)
            wf.writeframes(data)
        buf.seek(0)
        return buf

    def play(self, volume: float = 0.7):
        if not HAS_PYGAME:
            return
        if self._pygame_sound is None:
            buf = self._render()
            self._pygame_sound = pygame.mixer.Sound(buf)
        self._pygame_sound.set_volume(max(0.0, min(1.0, volume)))
        self._pygame_sound.play()


class AudioManager:
    def __init__(self):
        self.volume = 0.7
        self._initialized = False
        self._sounds = {}
        self._init_mixer()

    def _init_mixer(self):
        if not HAS_PYGAME:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1)
            self._initialized = True
        except Exception:
            self._initialized = False

    def _make_eat(self) -> Sound:
        def gen(t, dur):
            freq = 400 + t * 1200
            env = _adsr(t, 0.002, 0.01, 0.5, 0.05, dur)
            return _sine(freq, t) * env * 0.6
        return Sound(0.12, gen)

    def _make_golden_eat(self) -> Sound:
        def gen(t, dur):
            freq = 600 + t * 1800
            env = _adsr(t, 0.002, 0.02, 0.7, 0.08, dur)
            harmonic = _sine(freq * 1.5, t) * 0.3
            return (_sine(freq, t) + harmonic) * env * 0.5
        return Sound(0.2, gen)

    def _make_death(self) -> Sound:
        def gen(t, dur):
            freq = 300 - t * 250
            env = _adsr(t, 0.005, 0.02, 0.8, 0.15, dur)
            noise = _noise(t) * 0.15 * env
            return (_square(max(freq, 40), t) * env * 0.4 + noise) * 0.7
        return Sound(0.5, gen)

    def _make_powerup(self) -> Sound:
        def gen(t, dur):
            notes = [523, 659, 784, 1047]
            i = min(int(t / (dur / len(notes))), len(notes) - 1)
            freq = notes[i]
            env = _adsr(t, 0.005, 0.03, 0.6, 0.1, dur)
            harm1 = _sine(freq * 2, t) * 0.25
            harm2 = _sine(freq * 3, t) * 0.1
            return (_sine(freq, t) + harm1 + harm2) * env * 0.5
        return Sound(0.35, gen)

    def _make_levelup(self) -> Sound:
        def gen(t, dur):
            notes = [440, 554, 659, 880, 1047]
            note_dur = dur / len(notes)
            i = min(int(t / note_dur), len(notes) - 1)
            freq = notes[i]
            local_t = t - i * note_dur
            env = _adsr(local_t, 0.002, 0.02, 0.8, note_dur * 0.3, note_dur)
            return _sine(freq, t) * env * 0.5
        return Sound(0.6, gen)

    def _make_menu_select(self) -> Sound:
        def gen(t, dur):
            env = _adsr(t, 0.001, 0.01, 0.4, 0.03, dur)
            return _sine(800, t) * env * 0.4
        return Sound(0.06, gen)

    def _make_menu_move(self) -> Sound:
        def gen(t, dur):
            env = _adsr(t, 0.001, 0.005, 0.3, 0.02, dur)
            return _sine(500, t) * env * 0.3
        return Sound(0.04, gen)

    def load(self):
        self._sounds = {
            'eat': self._make_eat(),
            'golden_eat': self._make_golden_eat(),
            'death': self._make_death(),
            'powerup': self._make_powerup(),
            'levelup': self._make_levelup(),
            'menu_select': self._make_menu_select(),
            'menu_move': self._make_menu_move(),
        }

    def play(self, name: str, vol_override: Optional[float] = None):
        if not self._initialized or not self._sounds:
            return
        s = self._sounds.get(name)
        if s:
            vol = vol_override if vol_override is not None else self.volume
            s.play(vol)

    def set_volume(self, vol: float):
        self.volume = max(0.0, min(1.0, vol))
