#!/bin/sh
# ExecStopPost: dark matrix + dark user LEDs on every stop path. If the bridge
# is unreachable the sketch's 30 s idle timeout is the backstop.
PYTHONPATH="$HOME/muse-familiar" "$HOME/.local/bin/uv" run --with msgpack \
    python3 -c "from familiar.bridge_client import RouterClient; RouterClient().clear()" \
    >/dev/null 2>&1 || true
for l in red green blue; do
    echo 0 > "/sys/class/leds/unoq:user-${l}1/brightness" 2>/dev/null || true
done
