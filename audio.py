"""Procedural retro-synth sound effect generator with silent fallback when audio hardware is absent."""

from array import array
import math
import random
from typing import Dict, Optional

import pygame


class SoundManager:
    """Synthesizes crisp retro-arcade sound effects in memory (zero external asset files required)."""

    def __init__(self) -> None:
        self.enabled: bool = False
        self.muted: bool = False
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
            self._build_sound_bank()
        except Exception:
            self.enabled = False

    def _synth_wave(
        self,
        freq_start: float,
        freq_end: float,
        duration: float,
        volume: float = 0.30,
        wave_type: str = "square",
        noise_mix: float = 0.0,
    ) -> Optional[pygame.mixer.Sound]:
        if not self.enabled:
            return None
        sample_rate = 22050
        n_samples = max(1, int(sample_rate * duration))
        buf = array("h", [0] * n_samples)
        phase = 0.0
        rng = random.Random(42)

        for i in range(n_samples):
            t = i / n_samples
            env = (1.0 - t) ** 1.35
            freq = freq_start + (freq_end - freq_start) * t
            phase += (2.0 * math.pi * freq) / sample_rate

            if wave_type == "square":
                val = 1.0 if math.sin(phase) >= 0.0 else -1.0
            elif wave_type == "saw":
                val = 2.0 * ((phase / (2.0 * math.pi)) % 1.0) - 1.0
            else:
                val = math.sin(phase)

            if noise_mix > 0.0:
                val = val * (1.0 - noise_mix) + rng.uniform(-1.0, 1.0) * noise_mix

            sample = int(max(-32767, min(32767, val * env * volume * 32767)))
            buf[i] = sample

        try:
            return pygame.mixer.Sound(buffer=buf)
        except Exception:
            return None

    def _build_sound_bank(self) -> None:
        self.sounds["slash"] = self._synth_wave(
            360.0, 110.0, 0.09, volume=0.22, wave_type="saw", noise_mix=0.35
        )
        self.sounds["hit"] = self._synth_wave(
            210.0, 65.0, 0.10, volume=0.28, wave_type="square", noise_mix=0.40
        )
        self.sounds["crit"] = self._synth_wave(
            580.0, 160.0, 0.14, volume=0.32, wave_type="square", noise_mix=0.25
        )
        self.sounds["kill"] = self._synth_wave(
            260.0, 520.0, 0.16, volume=0.26, wave_type="saw", noise_mix=0.15
        )
        self.sounds["dash"] = self._synth_wave(
            180.0, 440.0, 0.11, volume=0.20, wave_type="sine", noise_mix=0.25
        )
        self.sounds["whirlwind"] = self._synth_wave(
            420.0, 140.0, 0.28, volume=0.28, wave_type="saw", noise_mix=0.30
        )
        self.sounds["nova"] = self._synth_wave(
            320.0, 760.0, 0.24, volume=0.26, wave_type="sine", noise_mix=0.15
        )
        self.sounds["lightning"] = self._synth_wave(
            880.0, 220.0, 0.22, volume=0.30, wave_type="square", noise_mix=0.45
        )
        self.sounds["pickup"] = self._synth_wave(
            440.0, 880.0, 0.14, volume=0.24, wave_type="sine"
        )
        self.sounds["levelup"] = self._synth_wave(
            330.0, 990.0, 0.36, volume=0.30, wave_type="square"
        )
        self.sounds["hurt"] = self._synth_wave(
            160.0, 55.0, 0.18, volume=0.34, wave_type="saw", noise_mix=0.45
        )
        self.sounds["stairs"] = self._synth_wave(
            240.0, 620.0, 0.30, volume=0.26, wave_type="sine"
        )

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass
