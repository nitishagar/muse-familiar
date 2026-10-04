#!/bin/sh
# FramePlayer build+upload — runs ON THE BOARD.
# Takes the same flock the engine uses (uploads are the sole MCU writer while
# held); compiles then uploads over the network port; never puts the board
# password in argv (read from $UNOQ_UPLOAD_PASSWORD env or prompts).
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$HERE")"
SKETCH="$HERE/FramePlayer"
LOCK="${FAMILIAR_LOCK:-$HOME/.local/state/familiar.lock}"

mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK"
flock 9   # engine pauses while we own the MCU

echo "== compile =="
arduino-cli compile --fqbn arduino:zephyr:unoq "$SKETCH"

echo "== upload =="
PORT="${FAMILIAR_UPLOAD_PORT:-}"
if [ -z "$PORT" ]; then
    PORT="$(arduino-cli board list --format json 2>/dev/null | \
        sed -n 's/.*"address"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi
[ -n "$PORT" ] || { echo "no network port found (arduino-cli board list)" >&2; exit 1; }
echo "uploading via $PORT"
arduino-cli upload -p "$PORT" --fqbn arduino:zephyr:unoq "$SKETCH"
echo "upload done"
