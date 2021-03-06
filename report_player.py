"""
This file defines low-level functions for palying sound.
"""

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame.mixer  # noqa: E402
import time  # noqa: E402
from typing import Iterable  # noqa: E402


class FileNotFoundError(Exception):
    pass


def play_report(report: Iterable[str]) -> None:
    # Check existence of all files
    for f in report:
        if not os.path.isfile(f):
            raise FileNotFoundError('{0} not found!'.format(f))

    _play_report(report)


def _play_report(sound_sequence: Iterable[str]) -> None:
    pygame.mixer.init()

    sounds = [pygame.mixer.Sound(f) for f in sound_sequence]
    if len(sounds) > 0:
        channel = sounds[0].play()
    for s in sounds[1:]:
        channel.queue(s)
        while channel.get_queue() is not None:
            time.sleep(0.01)

    if len(sounds) > 0:
        while channel.get_busy():
            time.sleep(0.01)
    time.sleep(0.5)

    pygame.mixer.quit()
