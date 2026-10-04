/*
    muse-familiar — FramePlayer sketch for the Arduino UNO Q (STM32U585 / Zephyr).

    A GENERIC frame player: all creature logic lives on the Linux side; this
    sketch only renders what it is told, with safety enforced on the MCU:

      familiar.ping()                      -> "pong:<uptime_s>"
      familiar.show.begin(total, period) -> show.chunk(str<=2 frames)* -> show.play(count)
            frames = N * 104 ASCII chars, each '0'..'7' (grayscale level);
            clamps: period_ms >= 250 (<= 4 fps), N <= 64 frames; extra bits
            masked. Each show() doubles as the heartbeat.
      familiar.clear()                     -> dark matrix

    MCU-side safety: if no show()/clear() arrives for IDLE_TIMEOUT_MS the
    matrix falls to a dim idle glyph (an engine crash on the Linux side can
    orphan the display; nothing host-side can reach these pixels).

    Muse-familiar is MIT licensed; built on Arduino_RouterBridge /
    Arduino_RPClite (MPL-2.0, Arduino s.r.l.) and Arduino_LED_Matrix from
    the arduino:zephyr core. See NOTICE.md.
*/

#include <Arduino_RPClite.h>
#include <Arduino_RouterBridge.h>
#include "Arduino_LED_Matrix.h"

Arduino_LED_Matrix matrix;

static const size_t FRAME_BYTES = 104;     // 8 rows x 13 cols
static const size_t MAX_FRAMES  = 64;
static const uint32_t MIN_PERIOD_MS = 250; // <= 4 fps (photosensitivity bound)
static const uint32_t IDLE_TIMEOUT_MS = 30000;

static uint8_t playBuffer[MAX_FRAMES][FRAME_BYTES];
static size_t  playFrames = 0;
static uint32_t playPeriod = 0;
static size_t  playIndex = 0;
static uint32_t lastFrameMs = 0;
static uint32_t lastHeartbeatMs = 0;
static bool     playing = false;

static const uint8_t IDLE_GLYPH[FRAME_BYTES] = {
    // one dim dot, centre-ish; everything else dark
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,1,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0,0,0,0,0,0,
};

static void renderCurrent() {
    if (playing && playFrames > 0) {
        matrix.draw(playBuffer[playIndex]);
    }
}

// --- RPC methods -----------------------------------------------------------
// The router caps messages at ~256 bytes (measured: 2 x 104-char frames OK,
// 3 fail), so animations upload in chunks: show_begin -> show_chunk* ->
// show_play. Every call refreshes the heartbeat.

static size_t  loadFrames = 0;      // frames staged by show_chunk
static uint32_t loadPeriod = MIN_PERIOD_MS;

String familiar_ping() {
    return String("pong:") + String(millis() / 1000);
}

int familiar_show_begin(int total_frames, int period_ms) {
    if (total_frames < 1 || (size_t)total_frames > MAX_FRAMES) return -1;
    int32_t period = (int32_t)period_ms;                    // negative guard
    uint32_t period_u = (period > (int32_t)MIN_PERIOD_MS)
                        ? (uint32_t)period : MIN_PERIOD_MS; // <= 4 fps
    loadFrames = 0;
    loadPeriod = period_u;
    lastHeartbeatMs = millis();
    return 0;
}

int familiar_show_chunk(String frames) {
    size_t len = frames.length();
    if (len == 0 || len % FRAME_BYTES != 0) return -1;      // bad payload
    size_t n = len / FRAME_BYTES;
    if (loadFrames + n > MAX_FRAMES) return -1;
    for (size_t f = 0; f < n; f++) {
        for (size_t i = 0; i < FRAME_BYTES; i++) {
            uint8_t v = (uint8_t)(frames.charAt(f * FRAME_BYTES + i) - '0');
            if (v > 7) v = 7;                               // 3-bit mask
            playBuffer[loadFrames + f][i] = v;
        }
    }
    loadFrames += n;
    lastHeartbeatMs = millis();
    return (int)loadFrames;
}

int familiar_show_play(int count) {
    if (loadFrames == 0) return -1;
    size_t n = loadFrames;
    if (count > 0 && (size_t)count < n) n = (size_t)count;
    playFrames = n;
    playPeriod = loadPeriod;
    playIndex = 0;
    playing = true;
    lastFrameMs = millis();
    lastHeartbeatMs = millis();
    renderCurrent();
    return (int)n;
}

int familiar_clear() {
    playing = false;
    playFrames = 0;
    uint8_t dark[FRAME_BYTES] = {0};
    matrix.draw(dark);
    lastHeartbeatMs = millis();
    return 0;
}

void setup() {
    matrix.begin();
    matrix.setGrayscaleBits(3);   // display depth 3 bits; source values <= 7
    matrix.draw(IDLE_GLYPH);
    lastHeartbeatMs = millis();

    Bridge.begin();
    Bridge.provide("familiar.ping", familiar_ping);
    Bridge.provide_safe("familiar.show.begin", familiar_show_begin);
    Bridge.provide_safe("familiar.show.chunk", familiar_show_chunk);
    Bridge.provide_safe("familiar.show.play", familiar_show_play);
    Bridge.provide_safe("familiar.clear", familiar_clear);
}

void loop() {
    uint32_t now = millis();

    // advance animation (period already clamped >= 250 ms at show() time)
    if (playing && playFrames > 0 && (now - lastFrameMs) >= playPeriod) {
        lastFrameMs = now;
        playIndex = (playIndex + 1) % playFrames;
        renderCurrent();
    }

    // heartbeat/idle safety: no show()/clear() for 30 s -> dim idle glyph
    if ((now - lastHeartbeatMs) >= IDLE_TIMEOUT_MS) {
        playing = false;
        playFrames = 0;
        matrix.draw(IDLE_GLYPH);
        lastHeartbeatMs = now;  // re-arm so we don't redraw every loop pass
    }

    // NOTE: provide_safe methods are dispatched by the framework's own loop
    // hook — Bridge.update_safe() is private by design (RouterBridge README).
}
