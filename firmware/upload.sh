#!/bin/sh
# FramePlayer build+upload — runs ON THE BOARD.
# Takes an EXCLUSIVE flock (engine holds it SHARED while serving, so uploads
# never flash under a live engine). Board upload password comes from
# $UNOQ_UPLOAD_PASSWORD (the board's Linux password) — never committed.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
SKETCH="$HERE/FramePlayer"
LOCK="${FAMILIAR_LOCK:-$HOME/.local/state/familiar.lock}"

[ -n "${UNOQ_UPLOAD_PASSWORD:-}" ] || { echo "set UNOQ_UPLOAD_PASSWORD (board password)" >&2; exit 1; }

mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK"
flock -w 30 -x 9 || { echo "engine holds the lock: systemctl --user stop familiar-engine first" >&2; exit 1; }

echo "== compile =="
arduino-cli compile --fqbn arduino:zephyr:unoq "$SKETCH"

echo "== upload =="
PORT="${FAMILIAR_UPLOAD_PORT:-$(arduino-cli board list --format json 2>/dev/null | grep -o '"address"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)}"
case "$PORT" in
    *[![:alnum:]:.%_-]*|'') echo "no usable network port found (arduino-cli board list)" >&2; exit 1 ;;
esac
echo "uploading via $PORT"
arduino-cli upload -p "$PORT" --fqbn arduino:zephyr:unoq \
    --upload-field "password=$UNOQ_UPLOAD_PASSWORD" "$SKETCH"
echo "upload done"
