#!/bin/sh
# Board has no RTC: fail closed if the clock is unsynchronized (TLS needs it).
i=0
while [ "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)" != "yes" ]; do
    i=$((i + 1))
    if [ "$i" -ge 30 ]; then
        echo "ntp_gate: NTP not synchronized after $((i * 2))s — failing closed" >&2
        exit 1
    fi
    sleep 2
done
