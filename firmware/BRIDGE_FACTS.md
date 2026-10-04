# Bridge facts (measured 2026-10-04, UNO Q, FramePlayer over arduino-router)

- Router: msgpack-rpc over `/var/run/arduino-router.sock`; anonymous client
  calls; missing methods return clean errors; `$/version` → 0.10.0.
- **Message cap ~256 B**: 2×104-char frames OK, 3 FAIL ("message size
  exceeds the limit") — hence the chunked show protocol (≤2 frames/call).
- Ping RTT: **19 ms** (own client, `familiar.ping` → `pong:<uptime_s>`).
- Chunked show (begin → chunks → play), 4 frames: **66 ms** begin→play.
- Upload: network port + `--upload-field password=<board-pass>`; ~9–16 s;
  **re-upload over a running sketch proven** (Bridge alive after reflash —
  ping answered within 5 s of the second upload).
- Compile on-board: ~43 s warm; 79–95 KB flash (10–12%), ~36 KB RAM (13%).
- Frame period enforcement: sketch clamps period ≥ 250 ms (≤ 4 fps) and
  masks values to 3 bits; idle timeout 30 s → dim idle glyph (demonstrated:
  engine silent after last show; visual confirmation in release video).
- Recovery notes: upload replaces the sketch (stock MCU behavior changes);
  re-flash any time via `firmware/upload.sh`; last-resort board recovery
  per Arduino docs (EDL 05c6:9008 / board reset procedures).
