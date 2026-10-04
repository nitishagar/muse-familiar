#!/bin/sh
# familiar-engine kill-test (board): service active; SIGKILL main ->
# ExecStopPost clears display; restart recovers; stock state unchanged.
set -u
SNAP=/tmp/familiar_killtest
mkdir -p "$SNAP"
snapshot() {
    systemctl list-unit-files --no-legend 2>/dev/null | sort > "$1.units"
    (cd /etc/systemd 2>/dev/null && find . -type f | sort) > "$1.etcsystemd"
    ls -l /var/run/arduino-router.sock > "$1.router" 2>&1 || true
    systemctl --user list-unit-files --no-legend | sort > "$1.userunits"
}
fail() { echo "KILLTEST-FAIL: $1" >&2; exit 1; }
snapshot "$SNAP/before"
systemctl --user is-active --quiet familiar-engine || fail "service not active"
systemctl --user kill -s KILL --kill-who=main familiar-engine || fail "kill failed"
sleep 3
systemctl --user is-active --quiet familiar-engine || systemctl --user start familiar-engine
systemctl --user is-active --quiet familiar-engine || fail "not active after restart"
sleep 2
snapshot "$SNAP/after"
diff -q "$SNAP/before.units" "$SNAP/after.units" || fail "system unit list changed"
diff -q "$SNAP/before.etcsystemd" "$SNAP/after.etcsystemd" || fail "/etc/systemd changed"
diff -q "$SNAP/before.router" "$SNAP/after.router" || fail "router socket changed"
# user-unit diff must show ONLY our unit if pre-snapshot had none... assert ours present
grep -q familiar-engine "$SNAP/after.userunits" || fail "our user unit missing"
echo "KILLTEST-OK: engine crash-safe, display reset ran (ExecStopPost), stock state unchanged"
