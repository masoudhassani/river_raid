"""Asset loading (images/sounds) with caching, and an audio facade that can be
switched off completely for headless training."""
from functools import lru_cache
from pathlib import Path

import pygame as pg

ROOT = Path(__file__).resolve().parent.parent


def asset_path(rel):
    """Resolve a path such as 'media/icon/ship.png' against the repository root,
    so the game works no matter what the current working directory is."""
    return str(ROOT / rel)


@lru_cache(maxsize=None)
def image(rel):
    surface = pg.image.load(asset_path(rel))
    # 32 bit surfaces blit ~25x faster than the palette based png files
    if pg.display.get_init() and pg.display.get_surface() is not None:
        return surface.convert_alpha()
    converted = pg.Surface(surface.get_size(), pg.SRCALPHA, 32)
    converted.blit(surface, (0, 0))
    return converted


class Audio:
    """Thin wrapper around pygame's mixer. When disabled every call is a no-op,
    which is what we want for headless / multi-process RL training."""

    def __init__(self, enabled=False, frequency=16000, channels=8):
        self.enabled = False
        self._sounds = {}
        if enabled:
            try:
                pg.mixer.pre_init(frequency, -16, 2, 512)
                pg.mixer.init()
                pg.mixer.set_num_channels(channels)
                self.enabled = True
            except pg.error:
                pass   # no audio device available

    def sound(self, rel):
        if rel not in self._sounds:
            self._sounds[rel] = pg.mixer.Sound(asset_path(rel))
        return self._sounds[rel]

    def play(self, channel, rel, loops=0):
        if self.enabled:
            pg.mixer.Channel(channel).play(self.sound(rel), loops)

    def play_if_idle(self, channel, rel, loops=0):
        if self.enabled and not pg.mixer.Channel(channel).get_busy():
            pg.mixer.Channel(channel).play(self.sound(rel), loops)

    def stop(self, channel):
        if self.enabled:
            pg.mixer.Channel(channel).stop()

    def pause(self, channel):
        if self.enabled:
            pg.mixer.Channel(channel).pause()

    def music(self, rel, loops=-1):
        if self.enabled:
            pg.mixer.music.load(asset_path(rel))
            pg.mixer.music.play(loops)


NO_AUDIO = Audio(enabled=False)
