"""Frame codec + the Familiar's mood animations.

A frame is 104 chars ('0'..'7'): 8 rows × 13 columns of grayscale, exactly
what the FramePlayer sketch renders. Bounds (IMPLICIT_SPEC inv.5): values
0-7, exactly 104 chars, ≤ 8 frames per mood, period ≥ 250 ms (clamped again
MCU-side — defense in depth).
"""

from __future__ import annotations

FRAME_LEN = 104
MAX_MOOD_FRAMES = 8
MIN_PERIOD_MS = 250


def validate_frame(frame: str) -> str:
    if len(frame) != FRAME_LEN:
        raise ValueError(f"frame must be {FRAME_LEN} chars, got {len(frame)}")
    for ch in frame:
        if ch not in "01234567":
            raise ValueError(f"grayscale char out of range: {ch!r}")
    return frame


def validate_period(period_ms: int) -> int:
    return max(int(period_ms), MIN_PERIOD_MS)


def _rows(*rows: str) -> str:
    frame = "".join(rows)
    if len(frame) != FRAME_LEN:
        raise ValueError(f"art must be 8 rows x 13 cols (got {len(frame)} chars)")
    return frame


# The Familiar: a chunky little blob, two bright eyes, centre of the matrix.
# rows 0-7, cols 0-12. Body = level 2, eyes = level 7, accents 3-5.

_IDLE_BODY = (
    "0000000000000",
    "0022222222200",
    "0222222222220",
    "0222222222220",
    "0222222222220",
    "0022222222200",
    "0000000000000",
    "0000000000000",
)


def _with_eyes(eye_row: int, left: int, right: int, level="7") -> str:
    rows = [list(r) for r in _IDLE_BODY]
    if 0 <= eye_row < 8:
        for col in (left, right):
            if 0 <= col < 13 and rows[eye_row][col] != "0":
                rows[eye_row][col] = level
    return "".join("".join(r) for r in rows)



MOODS: dict[str, tuple[int, list[str]]] = {
    # resting: slow blink
    "idle": (700, [
        _with_eyes(2, 4, 8),
        _with_eyes(2, 4, 8),
        _with_eyes(2, 4, 8, level="2"),
        _with_eyes(2, 4, 8, level="2"),
    ]),
    # webhook joy: a little hop with sparkle corners
    "happy": (300, [
        _rows("0000000000000", "0022222222200", "0227070707220",
              "0222222222220", "0222222222220", "0022222222200",
              "0000000000000", "0000000000000"),
        _rows("3000000000003", "0300000000300", "0022222222200",
              "0227070707220", "0222222222220", "0222222222200",
              "0000000000000", "0000000000000"),
    ]),
    # deploy failed: eyes droop to the bottom, body sags one row
    "sad": (600, [
        _rows("0000000000000", "0000000000000", "0022222222200",
              "0222222222220", "0222770077220", "0022222222200",
              "0000000000000", "0000000000000"),
        _rows("0000000000000", "0000000000000", "0022222222200",
              "0222222222220", "0222770077220", "0022222222200",
              "0222222222220", "0000000000000"),
    ]),
    # something needs you: eyes wide, top corners strobe
    "alert": (350, [
        _rows("7000000000007", "0022222222200", "0227777777220",
              "0227722277220", "0222222222220", "0022222222200",
              "0000000000000", "0000000000000"),
        _rows("0700000000070", "0022222222200", "0227777777220",
              "0227722277220", "0222222222220", "0022222222200",
              "0000000000000", "0000000000000"),
    ]),
    # board is hot / late hour: dim body, drifting z
    "sleepy": (800, [
        _rows("0000000000000", "0011111111100", "0111000011110",
              "0111111111110", "0011111111100", "0000000000000",
              "0000000000000", "0000000000000"),
        _rows("0000000000040", "0011111111100", "0111000011110",
              "0111111111110", "0011111111100", "0000000000000",
              "0000000000000", "0000000000000"),
        _rows("0000000004000", "0011111111100", "0111000011110",
              "0111111111110", "0011111111100", "0000000000000",
              "0000000000000", "0000000000000"),
    ]),
    # looking around
    "curious": (450, [
        _with_eyes(2, 3, 6),
        _with_eyes(2, 3, 6),
        _with_eyes(2, 6, 9),
        _with_eyes(2, 6, 9),
    ]),
    "off": (MIN_PERIOD_MS, ["0" * FRAME_LEN]),
}

# webhook payload kind -> mood
KIND_TO_MOOD = {
    "ci_green": "happy",
    "deploy_ok": "happy",
    "merge": "happy",
    "poke": "curious",
    "mention": "curious",
    "ci_red": "sad",
    "deploy_fail": "sad",
    "alert": "alert",
    "incident": "alert",
    "hot": "sleepy",
    "quiet": "idle",
}

for name, (period, frames) in MOODS.items():
    if not 1 <= len(frames) <= MAX_MOOD_FRAMES:
        raise ValueError(f"mood {name}: frame count out of bounds")
    for f in frames:
        validate_frame(f)


def mood_frames(mood: str) -> tuple[int, list[str]]:
    if mood not in MOODS:
        raise ValueError(f"unknown mood: {mood}")
    period, frames = MOODS[mood]
    return validate_period(period), frames
