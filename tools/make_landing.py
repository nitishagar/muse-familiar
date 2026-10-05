#!/usr/bin/env python3
"""Generate the GitHub Pages landing page from the real frame data.

Reads the Familiar's mood animations straight out of familiar/frames.py and
emits docs/index.html (self-contained: inline CSS/JS, no CDN) and
docs/og-image.png (1200x630, stdlib-only PNG encoder — no PIL needed).
The site's matrix shows exactly what the board shows.

Usage: python3 tools/make_landing.py [--check]   (check: regenerate + diff)
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import struct
import sys
import zlib

REPO = pathlib.Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

# ---------------------------------------------------------------- frames ----


def load_moods() -> dict:
    spec = importlib.util.spec_from_file_location("frames", REPO / "familiar" / "frames.py")
    frames = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frames)
    out = {}
    for name, (period, frames_list) in frames.MOODS.items():
        out[name] = {"period": period, "frames": frames_list}
    return out


# ------------------------------------------------------------- png writer ---


def write_png(path: pathlib.Path, width: int, height: int, pixels: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + pixels[y * width * 3:(y + 1) * width * 3]
                   for y in range(height))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


# 5x7 bitmap font (rows as 5-bit ints, MSB left) for the strings we need.
FONT = {
    "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "B": [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    "D": [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    "F": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    "G": [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111],
    "H": [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "I": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b11111],
    "J": [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "M": [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    "N": [0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    "Q": [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10010, 0b10001, 0b10001],
    "S": [0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001],
    "X": [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    "Y": [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    "Z": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    "0": [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "2": [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    "3": [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    "4": [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    "5": [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    "6": [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    "7": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    "8": [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    "9": [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    "+": [0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000],
    "-": [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
    " ": [0] * 7,
}

OG_W, OG_H = 1200, 630


def text_extent(text: str, scale: int) -> tuple:
    """(width, height) in pixels of a draw_text line."""
    return len(text) * 6 * scale - scale, 7 * scale


def draw_text(pixels: list, W: int, H: int, x: int, y: int, text: str,
              scale: int, rgb: tuple,
              dim: tuple = (16, 20, 34)) -> None:
    cursor = x
    for ch in text.upper():
        glyph = FONT.get(ch)
        if glyph is None:
            cursor += 6 * scale
            continue
        for row, bits in enumerate(glyph):
            for col in range(5):
                on = (bits >> (4 - col)) & 1
                color = rgb if on else dim
                for dy in range(scale):
                    for dx in range(scale):
                        px = cursor + col * scale + dx
                        py = y + row * scale + dy
                        if not (0 <= px < W and 0 <= py < H):
                            continue  # clip: never wrap onto other rows
                        i = (py * W + px) * 3
                        pixels[i:i + 3] = list(color)
        cursor += 6 * scale


# (x, y, text, scale, rgb) — every line must fit inside OG_W x OG_H.
OG_TEXTS = [
    (800, 140, "MUSE", 7, (96, 190, 255)),
    (800, 205, "FAMILIAR", 7, (240, 246, 255)),
    (800, 315, "A PIXEL CREATURE FOR", 3, (150, 160, 180)),
    (800, 350, "ARDUINO UNO Q + MUSE", 3, (150, 160, 180)),
    (800, 410, "OPEN SOURCE - MIT", 3, (110, 120, 145)),
]

# LED matrix geometry: 13 cols x 8 rows of dots, left of the text block.
OG_MATRIX = {"origin_x": 64, "origin_y": 100, "pitch": 54, "led": 23,
             "glow": 10}


def make_og_image(moods: dict, path: pathlib.Path) -> None:
    W, H = OG_W, OG_H
    BG = (10, 14, 26)
    pixels = [c for _ in range(W * H) for c in BG]

    def dot(cx: int, cy: int, r: int, rgb: tuple, glow: int = 0) -> None:
        for y in range(max(0, cy - r - glow), min(H, cy + r + glow + 1)):
            for x in range(max(0, cx - r - glow), min(W, cx + r + glow + 1)):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                i = (y * W + x) * 3
                if d <= r:
                    pixels[i:i + 3] = list(rgb)
                elif glow and d <= r + glow:
                    f = 1 - (d - r) / glow
                    pixels[i] = min(255, int(pixels[i] + rgb[0] * f * 0.35))
                    pixels[i + 1] = min(255, int(pixels[i + 1] + rgb[1] * f * 0.35))
                    pixels[i + 2] = min(255, int(pixels[i + 2] + rgb[2] * f * 0.35))

    # the creature: idle frame's happy cousin (frame 0 of happy) on the left
    frame = moods["happy"]["frames"][0]
    g = OG_MATRIX
    for idx, ch in enumerate(frame):
        row, col = divmod(idx, 13)
        level = int(ch)
        if level:
            blue = (60, 160, 255)
            dot(g["origin_x"] + col * g["pitch"],
                g["origin_y"] + row * g["pitch"],
                int(g["led"] * (0.45 + 0.55 * level / 7)), blue,
                glow=g["glow"])

    for x, y, text, scale, rgb in OG_TEXTS:
        w, h = text_extent(text, scale)
        assert 0 <= x and x + w <= W, f"og text overflows horizontally: {text!r}"
        assert 0 <= y and y + h <= H, f"og text overflows vertically: {text!r}"
        draw_text(pixels, W, H, x, y, text, scale, rgb)

    write_png(path, W, H, bytes(pixels))


# ------------------------------------------------------------------ html ----

HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>muse-familiar — a pixel creature for Arduino UNO Q + Muse</title>
<meta name="description" content="An open-source pixel creature living on the Arduino UNO Q's LED matrix. Fed by webhooks, seen and heard by Muse. The first Linux Muse gadget that actuates real hardware.">
<meta property="og:title" content="muse-familiar">
<meta property="og:description" content="A pixel creature for Arduino UNO Q + Muse — open source, webhook-fed, AI-paired.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://nitishagar.github.io/muse-familiar/">
<meta property="og:image" content="https://nitishagar.github.io/muse-familiar/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="muse-familiar">
<meta name="twitter:description" content="A pixel creature for Arduino UNO Q + Muse — open source, webhook-fed, AI-paired.">
<meta name="twitter:image" content="https://nitishagar.github.io/muse-familiar/og-image.png">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 13 8'%3E%3Crect width='13' height='8' fill='%230a0e1a'/%3E%3Ccircle cx='4' cy='2' r='0.9' fill='%2350b4ff'/%3E%3Ccircle cx='8' cy='2' r='0.9' fill='%2350b4ff'/%3E%3Crect x='2' y='1' width='9' height='4' fill='none' stroke='%23304a6e' stroke-width='0.3'/%3E%3C/svg%3E">
<style>
:root{--bg:#0a0e1a;--panel:#0f1626;--line:#1c2942;--ink:#eef4ff;--dim:#93a0b8;--blue:#50b4ff;--deep:#2f80d6}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:16px/1.6 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:960px;margin:0 auto;padding:0 24px}
header{padding:72px 0 40px;text-align:center}
h1{font-size:clamp(34px,6vw,56px);letter-spacing:-.02em}
h1 .fam{color:var(--blue)}
.tagline{color:var(--dim);font-size:clamp(17px,2.6vw,22px);margin-top:10px}
.tagline b{color:var(--ink)}
.badges{margin-top:18px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap}
.badge{border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:13px;color:var(--dim)}
.badge b{color:var(--ink);font-weight:600}
.hero{display:grid;grid-template-columns:1fr;gap:32px;align-items:center;margin:24px auto 8px}
@media(min-width:820px){.hero{grid-template-columns:440px 1fr}}
.matrix-panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:28px;text-align:center}
#matrix{display:grid;grid-template-columns:repeat(13,1fr);gap:6px;max-width:416px;margin:0 auto}
#matrix i{display:block;width:100%;aspect-ratio:1;border-radius:50%;background:#141d33;transition:background .18s,box-shadow .18s}
#matrix i.on-1{background:#173049}#matrix i.on-2{background:#1c466e}
#matrix i.on-3{background:#22609c}#matrix i.on-4{background:#2f80d6}
#matrix i.on-5{background:#3d9aef;box-shadow:0 0 8px #2f80d680}
#matrix i.on-6{background:#50b4ff;box-shadow:0 0 12px #50b4ff80}
#matrix i.on-7{background:#8fd3ff;box-shadow:0 0 16px #50b4ffb0}
.mood-label{margin-top:16px;color:var(--dim);font-size:14px}
.mood-label b{color:var(--ink)}
.ctl-label{margin:16px 0 8px;color:var(--dim);font-size:12.5px}
.moods{display:flex;gap:8px;flex-wrap:wrap;justify-content:center}
.moods button{background:#141d33;color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:8px 14px;font-size:14px;cursor:pointer}
.moods button:hover{border-color:var(--deep)}
.moods button.active{background:var(--deep);border-color:var(--blue)}
.kinds-ctl{display:flex;gap:6px;flex-wrap:wrap;justify-content:center}
.kinds-ctl button{background:transparent;color:var(--dim);border:1px solid var(--line);border-radius:8px;padding:5px 10px;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;cursor:pointer}
.kinds-ctl button:hover{color:var(--ink);border-color:var(--deep)}
.kinds-ctl button.flash{color:var(--ink);border-color:var(--blue);background:#1c466e}
@media(prefers-reduced-motion:reduce){#matrix i{transition:none}}
.pitch{color:var(--dim)} .pitch p{margin-bottom:12px} .pitch b{color:var(--ink)}
section{padding:44px 0;border-top:1px solid var(--line)}
h2{font-size:24px;margin-bottom:18px;letter-spacing:-.01em}
.steps{display:grid;gap:16px}
@media(min-width:820px){.steps{grid-template-columns:repeat(3,1fr)}}
.step{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
.step .n{color:var(--blue);font-weight:700;font-size:13px}
.step h3{font-size:16px;margin:6px 0}
.step p{color:var(--dim);font-size:14px}
pre{background:#0b1120;border:1px solid var(--line);border-radius:12px;padding:16px;overflow:auto;font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace;color:#c9e3ff}
.kinds{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.kind{border:1px solid var(--line);border-radius:8px;padding:4px 10px;font-size:13px;color:var(--dim)}
.kind b{color:var(--ink)}
.safety{display:grid;gap:12px;grid-template-columns:1fr}
@media(min-width:560px){.safety{grid-template-columns:repeat(2,1fr)}}
@media(min-width:820px){.safety{grid-template-columns:repeat(4,1fr)}}
@media(max-width:480px){pre{font-size:12px}.matrix-panel{padding:20px 16px}}
.safe{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;font-size:13.5px;color:var(--dim)}
.safe b{display:block;color:var(--ink);margin-bottom:4px}
.links{display:flex;gap:18px;flex-wrap:wrap;color:var(--dim);font-size:14.5px}
footer{padding:36px 0 56px;color:#5b6980;font-size:13px;text-align:center}
</style>
</head>
<body>
<header class="wrap">
  <h1>muse-<span class="fam">familiar</span></h1>
  <p class="tagline">A pixel creature living on your <b>Arduino UNO Q</b>'s LED matrix —<br>fed by webhooks, seen and heard by <b>Muse</b>.</p>
  <div class="badges">
    <span class="badge">🧵 <b>webhook-fed</b></span>
    <span class="badge">🤖 <b>Muse gadget</b></span>
    <span class="badge">⚡ <b>19&nbsp;ms bridge</b></span>
    <span class="badge">🔓 <b>MIT, open source</b></span>
  </div>
</header>

<div class="wrap hero">
  <div class="matrix-panel">
    <div id="matrix" aria-label="LED matrix showing the Familiar"></div>
    <p class="mood-label">current mood: <b id="mood-name">idle</b> — these are the real frames from <code>frames.py</code></p>
    <p class="ctl-label">Moods</p>
    <div class="moods" id="moods"></div>
    <p class="ctl-label">Simulate a webhook event</p>
    <div class="kinds-ctl" id="kinds"></div>
  </div>
  <div class="pitch">
    <p>The UNO Q is two computers in a UNO: a Qualcomm core running Debian, and an STM32 core running Zephyr sketches. <b>The Familiar lives on the LED matrix in between.</b></p>
    <p>It idles and blinks. Green CI → it <b>hops</b>. Failed deploy → it <b>sulks</b>. Incident → <b>wide-eyed</b>. Hot SoC → it <b>dozes off</b>.</p>
    <p>Pair it with <b>Muse</b> and your assistant can ask how it feels, cheer it up, and read its narrations in chat: <i>"The Familiar is now happy (event: ci_green)."</i></p>
    <p style="font-size:14px">Try the moods and events — the grid is the exact 8×13, 3-bit-grayscale art the board renders.</p>
  </div>
</div>

<section class="wrap">
  <h2>How it works</h2>
  <div class="steps">
    <div class="step"><span class="n">01</span><h3>Feed it</h3><p>GitHub, Home Assistant, or <code>curl</code> hit a tiny hardened webhook on the board's Linux side. Key'd, rate-limited, loopback by default.</p></div>
    <div class="step"><span class="n">02</span><h3>Feel it</h3><p>A mood engine turns events into frame art and pushes animations over the board's msgpack-RPC bridge — 19&nbsp;ms round-trip, chunked around the router's 256-byte cap.</p></div>
    <div class="step"><span class="n">03</span><h3>Show it</h3><p>A Zephyr sketch on the STM32U585 renders frames — with fps, brightness and idle-timeout safety enforced in the MCU itself, so a crash can never leave it strobing.</p></div>
  </div>
</section>

<section class="wrap">
  <h2>Make it yours</h2>
  <pre>git clone https://github.com/nitishagar/muse-familiar &amp;&amp; cd muse-familiar
read -rs UNOQ_UPLOAD_PASSWORD &amp;&amp; export UNOQ_UPLOAD_PASSWORD
cd firmware &amp;&amp; ./upload.sh          # flash the frame player
# ... then the engine + a one-line webhook:
curl -X POST localhost:8123/poke -H "X-Familiar-Key: $KEY" -d '{"kind":"ci_green"}'</pre>
  <div class="kinds">
    <span class="kind"><b>ci_green</b> / deploy_ok / merge → happy</span>
    <span class="kind"><b>ci_red</b> / deploy_fail → sad</span>
    <span class="kind"><b>alert</b> / incident → alert</span>
    <span class="kind"><b>mention</b> / poke → curious</span>
    <span class="kind"><b>hot</b> → sleepy</span>
  </div>
</section>

<section class="wrap">
  <h2>It's a real Muse gadget</h2>
  <p style="color:var(--dim);max-width:720px">Meta's <a href="https://github.com/facebookincubator/muse-gadget-sdk" target="_blank" rel="noopener">Muse gadget SDK</a> runs on the Debian side. One command opens pairing (<code>sudo musegadget pair</code>), the Muse app adopts it, and the repo ships contract-tested <code>familiar.status / show / feed</code> commands — the first open-source Muse gadget that actuates real hardware on Linux.</p>
</section>

<section class="wrap">
  <h2>Safety, baked in</h2>
  <div class="safety">
    <div class="safe"><b>≤ 4 fps, 3-bit</b>Photosensitivity and brightness caps enforced in the sketch, not just the host.</div>
    <div class="safe"><b>Idle timeout</b>No heartbeat for 30 s → the Familiar dozes to a dim glyph. Crashes can't strand it.</div>
    <div class="safe"><b>Hardened webhook</b>Shared key (constant-time), 2 KiB cap, 12/min rate limit, bounded queue.</div>
    <div class="safe"><b>User-space only</b>User systemd units, one project dir, stock board services untouched, clean teardown.</div>
  </div>
</section>

<section class="wrap">
  <h2>Links</h2>
  <div class="links">
    <a href="https://github.com/nitishagar/muse-familiar" target="_blank" rel="noopener">GitHub repo</a>
    <a href="https://gadgets.muse.ai/" target="_blank" rel="noopener">Muse Gadgets</a>
    <a href="https://github.com/facebookincubator/muse-gadget-sdk" target="_blank" rel="noopener">muse-gadget-sdk</a>
    <a href="https://docs.arduino.cc/hardware/uno-q/" target="_blank" rel="noopener">Arduino UNO Q</a>
    <a href="https://discord.gg/3bhjCkZdd6" target="_blank" rel="noopener">Muse Discord</a>
  </div>
</section>

<footer class="wrap">
  Built by <a href="https://github.com/nitishagar">@nitishagar</a> · MIT ·
  not affiliated with Meta (Muse) or Arduino ·
  the LED art above is the real frame data from the repo.
</footer>

<script>
// Frames below are generated from familiar/frames.py — regenerate with
// tools/make_landing.py after changing moods.
const MOODS = __MOODS_JSON__;
const KINDS = __KINDS_JSON__;

const grid = document.getElementById('matrix');
const cells = [];
for (let i = 0; i < 104; i++) {
  const d = document.createElement('i');
  grid.appendChild(d); cells.push(d);
}
let timer = null, current = 'idle';
const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

function drawFrame(mood, f) {
  const frame = MOODS[mood].frames[f % MOODS[mood].frames.length];
  for (let i = 0; i < 104; i++)
    cells[i].className = frame[i] === '0' ? '' : 'on-' + frame[i];
}

function show(mood) {
  const m = MOODS[mood]; if (!m) return;
  current = mood;
  document.getElementById('mood-name').textContent = mood;
  [...document.querySelectorAll('#moods button')].forEach(b =>
    b.classList.toggle('active', b.dataset.mood === mood));
  clearInterval(timer);
  timer = null;
  drawFrame(mood, 0);
  if (reduceMotion) return;
  let f = 1;
  timer = setInterval(() => drawFrame(mood, f++), Math.max(m.period, 250));   // same ≤4fps cap
}

const bar = document.getElementById('moods');
['idle','happy','sad','alert','sleepy','curious','off'].forEach(mood => {
  const b = document.createElement('button');
  b.type = 'button';
  b.textContent = mood; b.dataset.mood = mood;
  b.onclick = () => show(mood);
  bar.appendChild(b);
});
// feed simulation: poke kinds act like the webhook
const kindsBar = document.getElementById('kinds');
Object.keys(KINDS).forEach(kind => {
  const b = document.createElement('button');
  b.type = 'button';
  b.textContent = kind;
  b.onclick = () => {
    show(KINDS[kind]);
    b.classList.add('flash');
    setTimeout(() => b.classList.remove('flash'), 600);
  };
  kindsBar.appendChild(b);
});

// ambient loop: settle back to idle like the board does
if (!reduceMotion) setInterval(() => {
  if (current !== 'idle' && current !== 'off' && Math.random() < 0.25)
    show('idle');
}, 6000);
show('idle');
</script>
</body>
</html>
"""


def make_site(moods: dict) -> None:
    import sys
    sys.path.insert(0, str(REPO))
    from familiar.frames import KIND_TO_MOOD

    DOCS.mkdir(exist_ok=True)
    html = (HTML
            .replace("__MOODS_JSON__", json.dumps(moods))
            .replace("__KINDS_JSON__", json.dumps(KIND_TO_MOOD)))
    (DOCS / "index.html").write_text(html)
    make_og_image(moods, DOCS / "og-image.png")
    print(f"wrote {DOCS/'index.html'} ({len(html)//1024} KB) "
          f"+ og-image.png ({(DOCS/'og-image.png').stat().st_size//1024} KB)")


if __name__ == "__main__":
    make_site(load_moods())
