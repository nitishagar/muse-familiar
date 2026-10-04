"""Mood state machine: events move the Familiar between moods; each mood
holds for a duration then falls back to idle (the creature settles)."""

from __future__ import annotations

import time

from .frames import KIND_TO_MOOD

MOOD_HOLD_S = {
    "idle": 0,        # resting state — holds until an event
    "happy": 6.0,
    "sad": 8.0,
    "alert": 5.0,
    "sleepy": 20.0,
    "curious": 4.0,
}


class MoodMachine:
    def __init__(self, now=time.monotonic):
        self._now = now
        self.mood = "idle"
        self._expires = None

    def event(self, kind: str) -> str | None:
        """Apply a webhook kind; returns the new mood if it changed."""
        target = KIND_TO_MOOD.get(kind)
        if target is None:
            return None
        return self.set(target)

    def set(self, mood: str) -> str | None:
        if mood not in MOOD_HOLD_S:
            raise ValueError(f"unknown mood: {mood}")
        if mood == self.mood:
            self._refresh()
            return None
        self.mood = mood
        self._refresh()
        return mood

    def _refresh(self):
        hold = MOOD_HOLD_S[self.mood]
        self._expires = (self._now() + hold) if hold else None

    def tick(self) -> str | None:
        """Expire a held mood back to idle; returns 'idle' when it does."""
        if self._expires is not None and self._now() >= self._expires:
            self.mood = "idle"
            self._expires = None
            return "idle"
        return None
