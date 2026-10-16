"""
Shared Audio Player Controller using Pygame Mixer.
Supports play, pause, seek, volume, replay, stop, and position tracking.
"""
import os
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

logger = logging.getLogger("tambola.audio")

# Initialize pygame mixer safely
PYGAME_AVAILABLE = False
try:
    import pygame
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
    PYGAME_AVAILABLE = True
except Exception as e:
    logger.warning(f"Pygame mixer not available (running in headless/fallback mode): {e}")


class AudioPlayer:
    """Audio controller with duration probing and seek tracking."""

    def __init__(self):
        self.current_file: Optional[str] = None
        self.total_duration: float = 0.0
        self.start_offset: float = 0.0
        self.play_start_time: float = 0.0
        self.is_playing: bool = False
        self.is_paused: bool = False
        self.volume: float = 0.8
        self._set_mixer_volume(self.volume)

    def _set_mixer_volume(self, vol: float):
        try:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
        except Exception:
            pass

    def get_file_duration(self, file_path: str) -> float:
        """Probe duration of audio file in seconds."""
        p = Path(file_path)
        if not p.exists():
            return 0.0

        try:
            # Sound can probe .wav, .ogg accurately
            snd = pygame.mixer.Sound(str(p))
            dur = snd.get_length()
            if dur > 0:
                return dur
        except Exception:
            pass

        # Fallback duration estimate based on file size if mp3
        try:
            size = p.stat().st_size
            # Estimate roughly 128 kbps (~16000 bytes/sec)
            estimated = size / 16000.0
            return max(5.0, min(600.0, estimated))
        except Exception:
            return 0.0

    def play_track(self, file_path: str, start_pos: float = 0.0) -> bool:
        """Load and start playing an audio track from start_pos (seconds)."""
        p = Path(file_path)
        if not p.exists():
            logger.warning(f"Audio file does not exist: {file_path}")
            self.stop()
            return False

        try:
            self.current_file = str(p)
            self.total_duration = self.get_file_duration(self.current_file)
            self.start_offset = max(0.0, start_pos)
            
            pygame.mixer.music.load(self.current_file)
            pygame.mixer.music.play(start=self.start_offset)
            self._set_mixer_volume(self.volume)
            
            self.play_start_time = time.time()
            self.is_playing = True
            self.is_paused = False
            return True
        except Exception as e:
            logger.error(f"Error playing track {file_path}: {e}")
            self.stop()
            return False

    def pause(self):
        """Pause playback."""
        if self.is_playing and not self.is_paused:
            try:
                # Update start offset to current position before pausing
                self.start_offset = self.get_current_position()
                pygame.mixer.music.pause()
                self.is_paused = True
            except Exception as e:
                logger.error(f"Pause error: {e}")

    def resume(self):
        """Resume playback."""
        if self.is_playing and self.is_paused:
            try:
                pygame.mixer.music.unpause()
                self.play_start_time = time.time()
                self.is_paused = False
            except Exception as e:
                logger.error(f"Resume error: {e}")

    def toggle_play_pause(self):
        if self.is_paused:
            self.resume()
        elif self.is_playing:
            self.pause()
        elif self.current_file:
            self.play_track(self.current_file, start_pos=0.0)

    def stop(self):
        """Stop playback completely."""
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self.is_playing = False
        self.is_paused = False
        self.start_offset = 0.0

    def replay(self):
        """Restart current track from the beginning."""
        if self.current_file:
            self.play_track(self.current_file, start_pos=0.0)

    def seek(self, target_seconds: float):
        """Seek to a specific time point in seconds."""
        if not self.current_file:
            return
        target_seconds = max(0.0, min(self.total_duration, target_seconds))
        was_paused = self.is_paused
        
        try:
            pygame.mixer.music.play(start=target_seconds)
            self.start_offset = target_seconds
            self.play_start_time = time.time()
            self.is_playing = True
            if was_paused:
                pygame.mixer.music.pause()
                self.is_paused = True
            else:
                self.is_paused = False
        except Exception as e:
            logger.error(f"Seek error: {e}")

    def set_volume(self, vol_percent: int):
        """Set volume from 0 to 100."""
        self.volume = max(0.0, min(1.0, vol_percent / 100.0))
        self._set_mixer_volume(self.volume)

    def get_current_position(self) -> float:
        """Return playback position in seconds."""
        if not self.is_playing:
            return 0.0
        if self.is_paused:
            return self.start_offset

        # Check if pygame music is still busy
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self.is_playing = False
            return self.total_duration

        elapsed = time.time() - self.play_start_time
        curr = self.start_offset + elapsed
        if self.total_duration > 0 and curr > self.total_duration:
            curr = self.total_duration
            self.is_playing = False
        return curr

    def play_sound_effect(self, freq: float = 880.0, duration: float = 0.12, decay: bool = True):
        """Play synthetic chime or tick sound effect for UI feedback without external files."""
        try:
            import numpy as np
            sample_rate = 44100
            total_samples = int(sample_rate * duration)
            if total_samples <= 0:
                return
            t = np.linspace(0, duration, total_samples, False)
            envelope = np.exp(-t * (18.0 if decay else 4.0))
            tone = (np.sin(2 * np.pi * freq * t) * envelope * 14000).astype(np.int16)
            stereo = np.column_stack((tone, tone))
            snd = pygame.sndarray.make_sound(stereo)
            snd.set_volume(max(0.1, min(1.0, self.volume)))
            snd.play()
        except Exception as e:
            logger.debug(f"Sound effect fallback: {e}")

    def play_tick(self):
        """Play a short slot-machine tick / click sound."""
        self.play_sound_effect(freq=980.0, duration=0.04, decay=True)

    def play_draw_chime(self):
        """Play a smooth calling chime when a new track is drawn."""
        self.play_sound_effect(freq=659.25, duration=0.18, decay=True)

    def play_fanfare(self):
        """Play victory fanfare chords for winners."""
        try:
            import numpy as np
            sample_rate = 44100
            duration = 0.45
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            env = np.exp(-t * 5.0)
            # Major triad (C5, E5, G5)
            wave = (np.sin(2 * np.pi * 523.25 * t) + np.sin(2 * np.pi * 659.25 * t) + np.sin(2 * np.pi * 783.99 * t)) / 3.0
            tone = (wave * env * 16000).astype(np.int16)
            stereo = np.column_stack((tone, tone))
            snd = pygame.sndarray.make_sound(stereo)
            snd.set_volume(max(0.2, min(1.0, self.volume)))
            snd.play()
        except Exception:
            self.play_sound_effect(freq=880.0, duration=0.3)
