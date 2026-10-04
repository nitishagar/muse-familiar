# NOTICE

muse-familiar is MIT licensed. It builds on:

- **muse-gadget-sdk** — Copyright (c) Meta Platforms, Inc. and affiliates.
  Apache License 2.0. https://github.com/facebookincubator/muse-gadget-sdk
  Used unmodified on the device (installed per its README); the
  `familiar.*` command specs follow its `COMMAND_SPECS` contract.
- **Arduino_RouterBridge** and **Arduino_RPClite** — Copyright Arduino
  s.r.l. Mozilla Public License 2.0. The FramePlayer sketch links them;
  `firmware/` files that include their headers are subject to the MPL-2.0
  terms (source available in this repository).
- **Arduino_LED_Matrix / ArduinoGraphics** — part of the
  [ArduinoCore-zephyr](https://github.com/arduino/ArduinoCore-zephyr)
  board package; used per its license.
- The Linux-side bridge client (`familiar/bridge_client.py`) is an
  INDEPENDENT implementation of the msgpack-RPC frame protocol as
  implemented by Arduino_RPClite. The code in Arduino's UNO Q tutorial
  (arduino/docs-content, CC BY-SA 4.0) was NOT copied; the protocol facts
  (request/response frame shapes) are used per the MPL-2.0 RPClite
  reference implementation.

"Muse" and related marks belong to their owners; "Arduino" and "UNO Q"
belong to Arduino. This is an independent community project — not endorsed
by Meta or Arduino.
