"""
GeoView PySide6 -- Sound Feedback
==================================
Subtle sound effects for interaction feedback. Can be disabled.
"""

import logging
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

_logger = logging.getLogger(__name__)
_SOUND_DIR = Path(__file__).parent / "sounds"
_enabled = True
_volume = 0.3
_cache: dict[str, QSoundEffect] = {}


def play(name: str):
    """Play a sound effect. name: 'click', 'success', 'error', 'notify'"""
    if not _enabled:
        return

    if name not in _cache:
        path = _SOUND_DIR / f"{name}.wav"
        if not path.exists():
            _logger.debug("Sound not found: %s", path)
            return
        try:
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(path)))
            effect.setVolume(_volume)
            _cache[name] = effect
        except Exception as e:
            _logger.debug("Sound init failed: %s", e)
            return

    try:
        _cache[name].play()
    except Exception:
        pass


def set_enabled(enabled: bool):
    global _enabled
    _enabled = enabled


def set_volume(vol: float):
    global _volume
    _volume = max(0.0, min(1.0, vol))
    for effect in _cache.values():
        effect.setVolume(_volume)


def is_enabled() -> bool:
    return _enabled
