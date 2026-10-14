"""Procedural synthesizer for multi-layered SFX and looping Background Music (BGM) across 5 Biomes + Menu."""

from array import array
import math
import random
from typing import Dict, List, Optional, Tuple

import pygame


def _midi_to_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


class SoundManager:
    """Synthesizes rich multi-harmonic sound effects and looping dark synthwave BGM tracks in memory."""

    SAMPLE_RATE = 22050

    def __init__(self) -> None:
        self.enabled: bool = False
        self.muted: bool = False
        self.music_muted: bool = False
        self.sfx_volume: float = 0.78
        self.music_volume: float = 0.42
        self.current_bgm_name: str = ""
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.bgm_tracks: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.bgm_channel: Optional[pygame.mixer.Channel] = None
        self._init_mixer()

    def _init_mixer(self) -> None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=self.SAMPLE_RATE, size=-16, channels=1, buffer=1024
                )
            pygame.mixer.set_num_channels(16)
            self.bgm_channel = pygame.mixer.Channel(0)
            self.enabled = True
            self._build_sound_bank()
            self._build_bgm_bank()
        except Exception:
            self.enabled = False

    def _synth_layered_sfx(
        self,
        layers: List[Tuple[float, float, float, str, float]],
        duration: float,
        attack: float = 0.01,
        decay_exp: float = 1.6,
    ) -> Optional[pygame.mixer.Sound]:
        """
        Synthesize a multi-oscillator layered sound effect.
        Each layer is (freq_start, freq_end, amp, wave_type, noise_mix).
        """
        if not self.enabled:
            return None
        sr = self.SAMPLE_RATE
        n_samples = max(1, int(sr * duration))
        buf = array("h", [0] * n_samples)
        phases = [0.0] * len(layers)
        rng = random.Random(1337)
        two_pi = 2.0 * math.pi

        for i in range(n_samples):
            t = i / n_samples
            if t < attack and attack > 0.0:
                env = t / attack
            else:
                env = max(0.0, (1.0 - t) ** decay_exp)

            mixed = 0.0
            for idx, (f_start, f_end, amp, wtype, n_mix) in enumerate(layers):
                freq = f_start + (f_end - f_start) * (t ** 0.85)
                phases[idx] += (two_pi * freq) / sr
                ph = phases[idx]

                if wtype == "square":
                    osc = 0.85 if math.sin(ph) >= 0.0 else -0.85
                elif wtype == "saw":
                    osc = 2.0 * ((ph / two_pi) % 1.0) - 1.0
                elif wtype == "tri":
                    osc = 2.0 * abs(2.0 * ((ph / two_pi) % 1.0) - 1.0) - 1.0
                else:
                    osc = math.sin(ph) + 0.3 * math.sin(ph * 2.0)

                if n_mix > 0.0:
                    osc = osc * (1.0 - n_mix) + rng.uniform(-1.0, 1.0) * n_mix

                mixed += osc * amp

            sample = int(max(-32767, min(32767, mixed * env * 32767)))
            buf[i] = sample

        try:
            snd = pygame.mixer.Sound(buffer=buf)
            snd.set_volume(self.sfx_volume)
            return snd
        except Exception:
            return None

    def _synth_chord_arpeggio(
        self,
        midi_notes: List[int],
        note_len: float,
        volume: float = 0.28,
    ) -> Optional[pygame.mixer.Sound]:
        if not self.enabled:
            return None
        sr = self.SAMPLE_RATE
        total_dur = note_len * len(midi_notes) + 0.14
        n_samples = max(1, int(sr * total_dur))
        buf = array("h", [0] * n_samples)
        two_pi = 2.0 * math.pi

        for idx, note in enumerate(midi_notes):
            freq = _midi_to_freq(note)
            start_i = int(idx * note_len * sr)
            end_i = min(n_samples, start_i + int((note_len + 0.14) * sr))
            span = max(1, end_i - start_i)
            phase = 0.0
            for i in range(start_i, end_i):
                lt = (i - start_i) / span
                env = min(1.0, lt * 12.0) * ((1.0 - lt) ** 1.3)
                phase += (two_pi * freq) / sr
                val = (
                    0.6 * math.sin(phase)
                    + 0.25 * math.sin(phase * 2.0)
                    + 0.15 * (1.0 if math.sin(phase) >= 0 else -1.0)
                )
                s = buf[i] + int(val * env * volume * 32767)
                buf[i] = max(-32767, min(32767, s))

        try:
            snd = pygame.mixer.Sound(buffer=buf)
            snd.set_volume(self.sfx_volume)
            return snd
        except Exception:
            return None

    def _synth_bgm_loop(
        self,
        bass_notes: List[int],
        arp_notes: List[int],
        pad_chord: List[int],
        step_dur: float = 0.18,
        lead_bright: float = 0.35,
        perc_intensity: float = 0.25,
    ) -> Optional[pygame.mixer.Sound]:
        """
        Synthesize a seamless 16-step dark-synthwave / dungeon-synth loop in memory.
        """
        if not self.enabled:
            return None
        sr = self.SAMPLE_RATE
        steps = len(arp_notes)
        total_dur = steps * step_dur
        n_samples = max(1, int(sr * total_dur))
        buf = array("h", [0] * n_samples)
        two_pi = 2.0 * math.pi
        rng = random.Random(9001)

        pad_freqs = [_midi_to_freq(m) for m in pad_chord]
        step_samples = max(1, int(step_dur * sr))

        for step in range(steps):
            s_start = step * step_samples
            s_end = min(n_samples, s_start + step_samples)
            bass_freq = _midi_to_freq(bass_notes[step % len(bass_notes)])
            arp_freq = _midi_to_freq(arp_notes[step % len(arp_notes)])

            is_kick = (step % 4 == 0)
            is_snare = (step % 4 == 2)
            is_hat = (step % 2 == 1)

            b_phase = 0.0
            a_phase = 0.0
            k_phase = 0.0

            for i in range(s_start, s_end):
                local_t = (i - s_start) / step_samples
                global_t = i / sr

                # 1. Warm sub-bass + saw pulse
                b_env = max(0.0, (1.0 - local_t * 0.85) ** 1.25)
                b_phase += (two_pi * bass_freq) / sr
                bass_sig = (
                    0.65 * math.sin(b_phase)
                    + 0.35 * (2.0 * ((b_phase / two_pi) % 1.0) - 1.0)
                ) * b_env * 0.30

                # 2. Plucky melodic arpeggio
                a_env = min(1.0, local_t * 16.0) * ((1.0 - local_t) ** 1.9)
                a_phase += (two_pi * arp_freq) / sr
                arp_sig = (
                    math.sin(a_phase)
                    + lead_bright * math.sin(a_phase * 2.0)
                ) * a_env * 0.22

                # 3. Atmospheric dark pad chord
                pad_lfo = 0.78 + 0.22 * math.sin(global_t * two_pi / (total_dur * 0.5))
                pad_sig = 0.0
                for pf in pad_freqs:
                    pad_sig += math.sin(global_t * two_pi * pf)
                pad_sig = (pad_sig / max(1, len(pad_freqs))) * 0.16 * pad_lfo

                # 4. Crisp synth percussion
                perc_sig = 0.0
                if is_kick and local_t < 0.45:
                    kt = local_t / 0.45
                    k_freq = 125.0 * ((1.0 - kt) ** 1.8) + 36.0
                    k_phase += (two_pi * k_freq) / sr
                    perc_sig += math.sin(k_phase) * (1.0 - kt) * 0.34 * perc_intensity
                elif is_snare and local_t < 0.38:
                    st = local_t / 0.38
                    perc_sig += (
                        (rng.uniform(-1.0, 1.0) * 0.7 + math.sin(local_t * 900.0) * 0.3)
                        * ((1.0 - st) ** 1.7)
                        * 0.22
                        * perc_intensity
                    )
                elif is_hat and local_t < 0.18:
                    ht = local_t / 0.18
                    perc_sig += rng.uniform(-1.0, 1.0) * ((1.0 - ht) ** 2.2) * 0.10 * perc_intensity

                total_sig = bass_sig + arp_sig + pad_sig + perc_sig
                buf[i] = max(-32767, min(32767, int(total_sig * 24000)))

        try:
            return pygame.mixer.Sound(buffer=buf)
        except Exception:
            return None

    def _build_sound_bank(self) -> None:
        self.sounds["slash"] = self._synth_layered_sfx(
            [
                (440.0, 130.0, 0.22, "saw", 0.32),
                (880.0, 220.0, 0.12, "sine", 0.15),
            ],
            duration=0.10,
            decay_exp=1.5,
        )
        self.sounds["hit"] = self._synth_layered_sfx(
            [
                (230.0, 62.0, 0.28, "square", 0.35),
                (115.0, 42.0, 0.24, "sine", 0.10),
            ],
            duration=0.11,
            decay_exp=1.7,
        )
        self.sounds["crit"] = self._synth_layered_sfx(
            [
                (680.0, 180.0, 0.28, "square", 0.25),
                (1020.0, 340.0, 0.20, "saw", 0.10),
                (150.0, 48.0, 0.24, "sine", 0.0),
            ],
            duration=0.16,
            decay_exp=1.4,
        )
        self.sounds["kill"] = self._synth_chord_arpeggio(
            [60, 67, 72], note_len=0.045, volume=0.25
        )
        self.sounds["boss_kill"] = self._synth_chord_arpeggio(
            [55, 62, 67, 74, 79], note_len=0.08, volume=0.34
        )
        self.sounds["dash"] = self._synth_layered_sfx(
            [
                (210.0, 560.0, 0.20, "sine", 0.22),
                (420.0, 840.0, 0.12, "tri", 0.15),
            ],
            duration=0.12,
            decay_exp=1.3,
        )
        self.sounds["whirlwind"] = self._synth_layered_sfx(
            [
                (480.0, 150.0, 0.25, "saw", 0.28),
                (240.0, 520.0, 0.20, "sine", 0.10),
            ],
            duration=0.30,
            decay_exp=1.25,
        )
        self.sounds["nova"] = self._synth_layered_sfx(
            [
                (310.0, 860.0, 0.24, "sine", 0.12),
                (620.0, 1280.0, 0.16, "tri", 0.08),
            ],
            duration=0.26,
            decay_exp=1.35,
        )
        self.sounds["lightning"] = self._synth_layered_sfx(
            [
                (1120.0, 190.0, 0.28, "square", 0.48),
                (560.0, 95.0, 0.20, "saw", 0.30),
            ],
            duration=0.24,
            decay_exp=1.5,
        )
        self.sounds["pickup"] = self._synth_chord_arpeggio(
            [69, 76, 81], note_len=0.04, volume=0.24
        )
        self.sounds["shrine"] = self._synth_chord_arpeggio(
            [62, 69, 74, 81], note_len=0.06, volume=0.28
        )
        self.sounds["levelup"] = self._synth_chord_arpeggio(
            [60, 64, 67, 72, 76], note_len=0.06, volume=0.30
        )
        self.sounds["hurt"] = self._synth_layered_sfx(
            [
                (180.0, 52.0, 0.32, "saw", 0.42),
                (90.0, 38.0, 0.24, "square", 0.20),
            ],
            duration=0.19,
            decay_exp=1.4,
        )
        self.sounds["stairs"] = self._synth_chord_arpeggio(
            [57, 64, 69, 76], note_len=0.065, volume=0.27
        )

    def _build_bgm_bank(self) -> None:
        # Menu Theme: brooding D-minor arcane overture
        self.bgm_tracks["menu"] = self._synth_bgm_loop(
            bass_notes=[38, 38, 41, 38, 36, 36, 33, 36] * 2,
            arp_notes=[62, 65, 69, 74, 69, 65, 62, 57, 60, 64, 67, 72, 67, 64, 60, 55],
            pad_chord=[50, 57, 62, 65],
            step_dur=0.21,
            lead_bright=0.30,
            perc_intensity=0.55,
        )
        # Floor 1: Verdant Ossuary (E-minor eerie organic pulse)
        self.bgm_tracks["biome_1"] = self._synth_bgm_loop(
            bass_notes=[40, 40, 43, 40, 38, 38, 35, 38] * 2,
            arp_notes=[64, 67, 71, 76, 71, 67, 64, 59, 62, 66, 69, 74, 69, 66, 62, 57],
            pad_chord=[52, 59, 64, 67],
            step_dur=0.17,
            lead_bright=0.35,
            perc_intensity=0.85,
        )
        # Floor 2: Astral Archives (C-minor mystic arpeggios)
        self.bgm_tracks["biome_2"] = self._synth_bgm_loop(
            bass_notes=[36, 36, 39, 43, 34, 34, 31, 34] * 2,
            arp_notes=[60, 63, 67, 72, 75, 72, 67, 63, 58, 62, 65, 70, 74, 70, 65, 62],
            pad_chord=[48, 55, 60, 63],
            step_dur=0.16,
            lead_bright=0.45,
            perc_intensity=0.90,
        )
        # Floor 3: Frostbound Citadel (F#-minor crystalline synth)
        self.bgm_tracks["biome_3"] = self._synth_bgm_loop(
            bass_notes=[42, 42, 45, 42, 40, 40, 37, 40] * 2,
            arp_notes=[66, 69, 73, 78, 81, 78, 73, 69, 64, 68, 71, 76, 71, 68, 64, 61],
            pad_chord=[54, 61, 66, 69],
            step_dur=0.155,
            lead_bright=0.55,
            perc_intensity=0.95,
        )
        # Floor 4: Hellforge Foundry (G-minor industrial heavy drive)
        self.bgm_tracks["biome_4"] = self._synth_bgm_loop(
            bass_notes=[31, 31, 34, 38, 30, 30, 33, 36] * 2,
            arp_notes=[55, 58, 62, 67, 63, 62, 58, 55, 54, 57, 62, 66, 62, 57, 54, 50],
            pad_chord=[43, 50, 55, 58],
            step_dur=0.145,
            lead_bright=0.60,
            perc_intensity=1.15,
        )
        # Floor 5: Obsidian Sanctum (A-minor harmonic boss symphony)
        self.bgm_tracks["biome_5"] = self._synth_bgm_loop(
            bass_notes=[33, 33, 36, 40, 32, 32, 35, 39] * 2,
            arp_notes=[57, 60, 64, 69, 72, 69, 64, 60, 56, 59, 64, 68, 71, 68, 64, 59],
            pad_chord=[45, 52, 57, 60],
            step_dur=0.135,
            lead_bright=0.70,
            perc_intensity=1.25,
        )

    def play(self, name: str) -> None:
        if not self.enabled or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.set_volume(self.sfx_volume)
                snd.play()
            except Exception:
                pass

    def play_bgm(self, track_name: str) -> None:
        """Start or switch the looping background music track."""
        if not self.enabled:
            self.current_bgm_name = track_name
            return
        if self.current_bgm_name == track_name and self.bgm_channel and self.bgm_channel.get_busy():
            return
        self.current_bgm_name = track_name
        track = self.bgm_tracks.get(track_name)
        if track is None or self.bgm_channel is None:
            return
        try:
            vol = 0.0 if (self.muted or self.music_muted) else self.music_volume
            self.bgm_channel.set_volume(vol)
            self.bgm_channel.play(track, loops=-1)
        except Exception:
            pass

    def toggle_mute_all(self) -> bool:
        self.muted = not self.muted
        self._apply_bgm_volume()
        return self.muted

    def toggle_music(self) -> bool:
        self.music_muted = not self.music_muted
        self._apply_bgm_volume()
        return not self.music_muted

    def adjust_volume(self, delta: float) -> None:
        self.music_volume = max(0.0, min(1.0, self.music_volume + delta))
        self.sfx_volume = max(0.0, min(1.0, self.sfx_volume + delta))
        self._apply_bgm_volume()

    def _apply_bgm_volume(self) -> None:
        if not self.enabled or self.bgm_channel is None:
            return
        try:
            vol = 0.0 if (self.muted or self.music_muted) else self.music_volume
            self.bgm_channel.set_volume(vol)
        except Exception:
            pass
